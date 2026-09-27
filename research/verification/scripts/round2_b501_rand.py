#!/usr/bin/env python3
"""Round2 B501-B510: exact random-play win rate p_rand.

p_rand(occ) = P(player-to-move wins when both pick uniformly among legal moves)
  p_rand(terminal) = 0
  p_rand(occ) = (1/|L|) * sum_{u in L} (1 - p_rand(occ|u))

Population default: all safe sets reachable from empty on n×n, or
explicitly the set of positions with given (n, k, |L|, status).

Outputs research/verification/round2_b501.json (rand section).
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, board_square  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "round2_b501.json"


def prand_table(board: Board) -> dict[int, float]:
    """Memoized exact p_rand over all safe reachable occ."""
    import sys as _sys
    _sys.setrecursionlimit(200000)
    memo: dict[int, float] = {}

    def ev(occ: int) -> float:
        hit = memo.get(occ)
        if hit is not None:
            return hit
        mv = board.legal_moves(occ)
        if not mv:
            memo[occ] = 0.0
            return 0.0
        s = 0.0
        for u in mv:
            s += 1.0 - ev(occ | (1 << u))
        p = s / len(mv)
        memo[occ] = p
        return p

    ev(0)
    return memo


def analyze_n(n: int) -> dict:
    b = board_square(n)
    print(f"[rand] n={n} V={b.V} F={len(b.quads)}", flush=True)
    g = b.solve_grundy()
    pr = prand_table(b)
    # empty board
    empty_g = g.get(0, -1)
    empty_pr = pr.get(0, 0.0)
    # classify reachable safe sets by (k, |L|, status)
    rows = []
    for occ, gv in g.items():
        k = occ.bit_count()
        L = len(b.legal_moves(occ))
        rows.append((occ, k, L, gv, pr[occ]))
    # P positions (g=0), N positions (g>0)
    P = [r for r in rows if r[3] == 0]
    N = [r for r in rows if r[3] > 0]
    P_pr = [r[4] for r in P]
    N_pr = [r[4] for r in N]

    def stats(xs):
        if not xs:
            return {}
        xs2 = sorted(xs)
        return {
            "count": len(xs2),
            "min": xs2[0],
            "max": xs2[-1],
            "mean": sum(xs2) / len(xs2),
        }

    # B501: max p_rand among P positions
    maxP = max(P_pr) if P_pr else None
    # B502: any P with p_rand > 3/4?
    over34 = [r for r in P if r[4] > 0.75]
    over23 = [r for r in P if r[4] > 2.0 / 3.0]

    # B503: N positions with exactly 1 winning move (child g=0) and
    # remaining children all "same random value" — approximate: |W|=1
    # and children p_rand cluster. Count N with |W|=1.
    W_count = {}
    for occ, k, L, gv, pr_v in rows:
        if gv == 0:
            continue
        mv = b.legal_moves(occ)
        w = 0
        child_prs = []
        child_gs = []
        for u in mv:
            ch = occ | (1 << u)
            child_gs.append(g[ch])
            child_prs.append(pr[ch])
            if g[ch] == 0:
                w += 1
        W_count[occ] = (w, L, child_gs, child_prs)
    n_N = len(N)
    n_W1 = sum(1 for occ, (w, L, cg, cp) in W_count.items() if w == 1)
    # "one rescue + temptations": W=1 and among losing children the
    # p_rand values are close to each other (range <= 0.05) and to the
    # winning child's p_rand
    rescue = 0
    rescue_ex = []
    for occ, (w, L, cg, cp) in W_count.items():
        if w != 1:
            continue
        # find winning child p and losing children p
        win_cp = None
        lose_cp = []
        for u_idx, u in enumerate(b.legal_moves(occ)):
            if cg[u_idx] == 0:
                win_cp = cp[u_idx]
            else:
                lose_cp.append(cp[u_idx])
        if win_cp is None or not lose_cp:
            continue
        rng = max(lose_cp) - min(lose_cp)
        if rng <= 0.05:
            rescue += 1
            if len(rescue_ex) < 5:
                rescue_ex.append(
                    {"occ": occ, "k": occ.bit_count(), "L": L,
                     "win_pr": win_cp, "lose_pr_min": min(lose_cp),
                     "lose_pr_max": max(lose_cp)}
                )

    # B505: N with |W|/|L| >= 1/2 but small p_rand
    b505_hits = []
    for occ, (w, L, cg, cp) in W_count.items():
        if L == 0:
            continue
        if w / L >= 0.5 and pr[occ] < 0.35:
            b505_hits.append(
                {"occ": occ, "k": occ.bit_count(), "L": L, "W": w,
                 "ratio": w / L, "p_rand": pr[occ], "g": g[occ]}
            )

    # B506: P positions with remaining-max-moves <= 3 and p_rand > 1/2
    # remaining max moves = longest remaining play under optimal? use
    # remaining empty points that are still playable at most, or simpler:
    # max remaining moves = size of largest safe extension from occ.
    # Cheap proxy: V - k (upper bound) is too loose. Use exact depth of
    # game tree under optimal: max remaining moves = max path length.
    # For small n compute max remaining via DP on reachable states.
    maxrem_memo: dict[int, int] = {}

    def max_rem(occ: int) -> int:
        hit = maxrem_memo.get(occ)
        if hit is not None:
            return hit
        mv = b.legal_moves(occ)
        if not mv:
            maxrem_memo[occ] = 0
            return 0
        best = 0
        for u in mv:
            best = max(best, 1 + max_rem(occ | (1 << u)))
        maxrem_memo[occ] = best
        return best

    max_rem(0)
    b506_hits = []
    b506_checked = 0
    for occ, gv in g.items():
        if gv != 0:
            continue
        mr = maxrem_memo[occ]
        if mr <= 3:
            b506_checked += 1
            if pr[occ] > 0.5:
                b506_hits.append(
                    {"occ": occ, "k": occ.bit_count(),
                     "max_rem": mr, "p_rand": pr[occ]}
                )

    # B508: pairs of positions with same p_rand (to 1e-4) but very
    # different winning-move ratios
    # bucket by rounded p_rand
    buckets = defaultdict(list)
    for occ, (w, L, cg, cp) in W_count.items():
        if L == 0:
            continue
        key = round(pr[occ], 4)
        buckets[key].append((occ, w / L, w, L, g[occ]))
    b508_pairs = []
    for key, lst in buckets.items():
        if len(lst) < 2:
            continue
        ratios = [x[1] for x in lst]
        if max(ratios) - min(ratios) >= 0.4:
            lo = min(lst, key=lambda x: x[1])
            hi = max(lst, key=lambda x: x[1])
            b508_pairs.append(
                {"p_rand": key, "occ_lo": lo[0], "ratio_lo": lo[1],
                 "occ_hi": hi[0], "ratio_hi": hi[1]}
            )
            if len(b508_pairs) >= 5:
                break

    # B509: among N positions with same (n,k,|L|,|W|), corr of p_rand
    # vs variance of losing-child p_rand. Population: those groups.
    groups = defaultdict(list)
    for occ, (w, L, cg, cp) in W_count.items():
        lose_cp = [cp[i] for i in range(L) if cg[i] != 0]
        if len(lose_cp) < 2:
            continue
        mu = sum(lose_cp) / len(lose_cp)
        var = sum((x - mu) ** 2 for x in lose_cp) / len(lose_cp)
        key = (occ.bit_count(), L, w)
        groups[key].append((pr[occ], var))
    # pooled Spearman-like: compare rank correlation across all groups
    all_pairs = []  # (pr, var) for N with >=2 losing children
    for key, lst in groups.items():
        all_pairs.extend(lst)
    # Pearson on all pooled
    b509_n = len(all_pairs)
    b509_r = None
    if b509_n >= 3:
        xs = [p for p, v in all_pairs]
        ys = [v for p, v in all_pairs]
        mx = sum(xs) / len(xs)
        my = sum(ys) / len(ys)
        cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        vx = sum((x - mx) ** 2 for x in xs)
        vy = sum((y - my) ** 2 for y in ys)
        if vx > 0 and vy > 0:
            b509_r = cov / (vx ** 0.5 * vy ** 0.5)
    # also within-group: fraction of groups where lower p_rand has lower var
    agree = 0
    tot = 0
    for key, lst in groups.items():
        if len(lst) < 2:
            continue
        lst_s = sorted(lst, key=lambda t: t[0])
        # check monotone: p increasing => var not systematically decreasing
        # compute pairwise
        for i in range(len(lst_s)):
            for j in range(i + 1, len(lst_s)):
                tot += 1
                if (lst_s[j][0] - lst_s[i][0]) * (lst_s[j][1] - lst_s[i][1]) >= 0:
                    agree += 1

    # B510: true winning move ranked strictly last by child p_rand
    b510_hits = []
    for occ, (w, L, cg, cp) in W_count.items():
        if w == 0:
            continue
        mv = b.legal_moves(occ)
        # winning moves: child g == 0
        win_idxs = [i for i in range(L) if cg[i] == 0]
        lose_idxs = [i for i in range(L) if cg[i] != 0]
        if not lose_idxs:
            continue
        # is every winning move's child p_rand strictly greater than all
        # losing children? (evaluating by child p_rand prefers high p_rand
        # for the player who just moved... careful)
        # "子からのランダム勝率を使った評価" = prefer moves whose child
        # p_rand is LOWEST (because child p_rand is opponent's win rate).
        # So a true winning move ranks last if its child p_rand is the
        # HIGHEST among all moves (looks worst).
        win_prs = [cp[i] for i in win_idxs]
        lose_prs = [cp[i] for i in lose_idxs]
        if min(win_prs) > max(lose_prs):
            b510_hits.append(
                {"occ": occ, "k": occ.bit_count(), "L": L, "W": w,
                 "win_child_pr": min(win_prs),
                 "best_lose_child_pr": max(lose_prs), "g": g[occ]}
            )

    # B507: max p_rand among P by h = max_rem
    by_h = defaultdict(list)
    for occ, gv in g.items():
        if gv != 0:
            continue
        by_h[maxrem_memo[occ]].append(pr[occ])
    h_table = {str(h): {"count": len(v), "max_pr": max(v), "min_pr": min(v)}
               for h, v in sorted(by_h.items())}

    # B504 not computable from this table alone (needs construction).

    out = {
        "n": n,
        "V": b.V,
        "F": len(b.quads),
        "empty_g": empty_g,
        "empty_p_rand": empty_pr,
        "empty_winner_optimal": "N" if empty_g > 0 else "P",
        "empty_winner_random": "first" if empty_pr > 0.5 else ("second" if empty_pr < 0.5 else "tie"),
        "n_reachable": len(g),
        "n_P": len(P),
        "n_N": len(N),
        "P_p_rand": stats(P_pr),
        "N_p_rand": stats(N_pr),
        "B501_max_P_p_rand": maxP,
        "B501_gt_2_3": len(over23),
        "B502_P_gt_3_4": len(over34),
        "B502_examples": [
            {"occ": r[0], "k": r[1], "L": r[2], "p_rand": r[4]} for r in over34[:5]
        ],
        "B503_N_with_W1": n_W1,
        "B503_fraction_W1": (n_W1 / n_N) if n_N else None,
        "B503_rescue_tight": rescue,
        "B503_examples": rescue_ex,
        "B505_hits": b505_hits[:10],
        "B505_n_hits": len(b505_hits),
        "B506_P_maxrem_le3": b506_checked,
        "B506_violations": b506_hits,
        "B507_max_pr_by_h": h_table,
        "B508_pairs": b508_pairs,
        "B509_pooled_n": b509_n,
        "B509_pooled_r": b509_r,
        "B509_pair_agree": agree,
        "B509_pair_total": tot,
        "B510_hits": b510_hits[:10],
        "B510_n_hits": len(b510_hits),
    }
    return out


def main():
    data = {}
    for n in (2, 3, 4):
        data[f"rand_n{n}"] = analyze_n(n)
        # incremental write so timeouts do not lose work
        if OUT.exists():
            old = json.loads(OUT.read_text(encoding="utf-8"))
        else:
            old = {}
        old.update(data)
        OUT.write_text(json.dumps(old, indent=2, ensure_ascii=False), encoding="utf-8")
    # n=5 full reachable p_rand + max-rem DP is too heavy here (timed out
    # at 180s on V=25). Mark NOT-CHECKED at this size.
    data["rand_n5"] = {"error": "timeout V=25; see batch notes", "status": "NOT-CHECKED"}
    data["meta"] = {
        "definition": "p_rand(occ)=E[1-p_rand(child)] under uniform legal moves",
        "population": "all safe reachable occ on n×n (exact, not sampled)",
    }
    # merge
    if OUT.exists():
        old = json.loads(OUT.read_text(encoding="utf-8"))
    else:
        old = {}
    old.update(data)
    OUT.write_text(json.dumps(old, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
