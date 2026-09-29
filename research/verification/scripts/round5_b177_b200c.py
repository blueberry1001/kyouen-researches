#!/usr/bin/env python3
"""B181/B182/B184/B188 terminal-size distributions + first-move influence.
B189 last-point bias + B190 |L| drop predictors on random games.
B185 random-greedy reach probability of maximal sets (n=4 full).
Does NOT compute p_rand win probability.
"""
from __future__ import annotations

import json
import random
import sys
from collections import Counter, defaultdict
from fractions import Fraction

sys.path.insert(0, "research/verification/scripts")
from kyouen_core import board_square, board_square_minus  # noqa: E402

OUT = "research/verification/round5_b177_b200c.json"


def exact_dist_with_first(board, first_move: int | None = None):
    """Exact distribution of terminal |S| under random greedy, optional first move."""
    import sys as _sys

    _sys.setrecursionlimit(100000)
    memo = {}

    def dist(occ: int) -> dict:
        hit = memo.get(occ)
        if hit is not None:
            return hit
        mv = board.legal_moves(occ)
        if not mv:
            d = {occ.bit_count(): 1.0}
            memo[occ] = d
            return d
        acc = defaultdict(float)
        w = 1.0 / len(mv)
        for u in mv:
            for t, p in dist(occ | (1 << u)).items():
                acc[t] += p * w
        d = dict(acc)
        memo[occ] = d
        return d

    if first_move is None:
        return dist(0), 0
    return dist(1 << first_move), 1


def moments(d: dict) -> dict:
    n = sum(d.values())
    mean = sum(t * p for t, p in d.items()) / n
    var = sum((t - mean) ** 2 * p for t, p in d.items()) / n
    sd = var ** 0.5
    if sd == 0:
        skew = kurt = 0.0
    else:
        skew = sum(((t - mean) / sd) ** 3 * p for t, p in d.items()) / n
        kurt = sum(((t - mean) / sd) ** 4 * p for t, p in d.items()) / n - 3.0
    # median
    acc = 0.0
    med = None
    for t in sorted(d):
        acc += d[t] / n
        if acc >= 0.5:
            med = t
            break
    return {
        "mean": mean,
        "sd": sd,
        "median": med,
        "skew": skew,
        "excess_kurtosis": kurt,
        "dist": {str(k): v / n for k, v in sorted(d.items())},
        "E_over_K": mean / board_k_placeholder,
    }


board_k_placeholder = 1.0


def residual_counts(board, occ: int) -> dict:
    need2 = need3 = need4 = 0
    for q in board.quads:
        t = 4 - (q & occ).bit_count()
        if t == 2:
            need2 += 1
        elif t == 3:
            need3 += 1
        elif t == 4:
            need4 += 1
    return need2, need3, need4


def main() -> None:
    global board_k_placeholder
    out: dict = {}

    # ---- B181/B182/B184/B188: exact terminal dist n=3,4,5 ----
    print("=== terminal distributions ===", flush=True)
    for n in (3, 4, 5):
        b = board_square(n)
        K = b.max_safe_size()
        board_k_placeholder = float(K)
        d, _ = exact_dist_with_first(b, None)
        m = moments(d)
        m.pop("E_over_K")
        m["E_over_K"] = m["mean"] / K
        m["K"] = K
        m["scale_n23"] = (n ** (2.0 / 3.0)) * ((n.bit_length()) ** 0)  # placeholder
        import math

        m["n23_log13"] = (n ** (2.0 / 3.0)) * ((math.log(n)) ** (1.0 / 3.0))
        m["mean_over_n23log13"] = m["mean"] / m["n23_log13"]
        m["median_over_n23log13"] = (m["median"] / m["n23_log13"]) if m["median"] else None
        out[f"b181_b182_b184_n{n}"] = m
        print(
            f"n={n} K={K} mean={m['mean']:.4f} med={m['median']} sd={m['sd']:.4f} "
            f"skew={m['skew']:.4f} kurt={m['excess_kurtosis']:.4f} E/K={m['E_over_K']:.4f} "
            f"mean/n23log13={m['mean_over_n23log13']:.4f}",
            flush=True,
        )

    # B188: first-move influence on E[X]
    print("=== B188 first-move ===", flush=True)
    for n in (3, 4):
        b = board_square(n)
        K = b.max_safe_size()
        board_k_placeholder = float(K)
        Es = []
        for p in range(b.V):
            d, _ = exact_dist_with_first(b, p)
            m = moments(d)
            Es.append(m["mean"])
        emean = sum(Es) / len(Es)
        mx, mn = max(Es), min(Es)
        rel = (mx - mn) / emean if emean else None
        out[f"b188_n{n}"] = {
            "E_by_first": Es,
            "E_mean": emean,
            "E_max": mx,
            "E_min": mn,
            "max_diff_over_E": rel,
            "K": K,
        }
        print(f"n={n} E range {mn:.4f}..{mx:.4f} rel={rel:.4f}", flush=True)
    # n=5 first-move is 25 separate DPs — do 5 representative points
    b = board_square(5)
    K = b.max_safe_size()
    board_k_placeholder = float(K)
    reps = [0, 12]  # corner + center; full 25 DPs too heavy
    Es = []
    for p in reps:
        d, _ = exact_dist_with_first(b, p)
        m = moments(d)
        Es.append((p, m["mean"]))
    emean = sum(e for _, e in Es) / len(Es)
    mx, mn = max(e for _, e in Es), min(e for _, e in Es)
    out["b188_n5_sample"] = {
        "E_by_first": Es,
        "E_mean": emean,
        "max_diff_over_E_sample": (mx - mn) / emean if emean else None,
        "note": "2 representative first moves only (corner id=0, center id=12)",
        "K": K,
    }
    print(f"n=5 sample E {mn:.4f}..{mx:.4f}", flush=True)

    # ---- B189/B190: random games ----
    print("=== random games ===", flush=True)
    rng = random.Random(20260929)
    games_out = {}
    for n, ngames in ((4, 5000), (5, 3000), (6, 400)):
        b = board_square(n)
        deg0 = [len(b.quads_by_pt[i]) for i in range(b.V)]
        last_deg = []
        drop_rec = []  # (need2, need3, net_drop, |L_parent|)
        drop_rec2 = []  # (need2_ratio, net_drop)
        for _ in range(ngames):
            occ = 0
            last_u = None
            while True:
                mv = b.legal_moves(occ)
                if not mv:
                    if last_u is not None:
                        last_deg.append(deg0[last_u])
                    break
                need2, need3, need4 = residual_counts(b, occ)
                u = mv[rng.randrange(len(mv))]
                child_L = len(b.legal_moves(occ | (1 << u)))
                net = len(mv) - child_L - 1  # subtract expected consumption of u
                res = need2 + need3 + need4
                drop_rec.append((need2, need3, net, len(mv)))
                drop_rec2.append(((need2 / res) if res else 0.0, net))
                occ = occ | (1 << u)
                last_u = u
        mean_deg_uniform = sum(deg0) / len(deg0)
        med_deg = sorted(deg0)[len(deg0) // 2]
        frac_low_last = (
            sum(1 for d in last_deg if d <= med_deg) / len(last_deg) if last_deg else None
        )
        frac_low_uniform = sum(1 for d in deg0 if d <= med_deg) / len(deg0)

        def corr(xs, ys):
            nn = len(xs)
            if nn < 5:
                return None
            mx = sum(xs) / nn
            my = sum(ys) / nn
            num = sum((xs[i] - mx) * (ys[i] - my) for i in range(nn))
            dx = sum((xs[i] - mx) ** 2 for i in range(nn)) ** 0.5
            dy = sum((ys[i] - my) ** 2 for i in range(nn)) ** 0.5
            return (num / (dx * dy)) if dx and dy else None

        c2 = corr([r[0] for r in drop_rec], [r[2] for r in drop_rec])
        c3 = corr([r[1] for r in drop_rec], [r[2] for r in drop_rec])
        cL = corr([r[3] for r in drop_rec], [r[2] for r in drop_rec])
        cR = corr([r[0] for r in drop_rec2], [r[1] for r in drop_rec2])

        games_out[str(n)] = {
            "ngames": ngames,
            "b189": {
                "mean_last_deg": (sum(last_deg) / len(last_deg)) if last_deg else None,
                "mean_uniform_deg": mean_deg_uniform,
                "frac_low_deg_last": frac_low_last,
                "frac_low_deg_uniform": frac_low_uniform,
                "bias_ratio": (frac_low_last / frac_low_uniform) if frac_low_uniform else None,
                "last_deg_hist": dict(Counter(last_deg)),
            },
            "b190": {
                "corr_need2_vs_net_drop": c2,
                "corr_need3_vs_net_drop": c3,
                "corr_L_vs_net_drop": cL,
                "corr_need2_ratio_vs_net_drop": cR,
                "mean_net_drop": (sum(r[2] for r in drop_rec) / len(drop_rec)) if drop_rec else None,
            },
        }
        print(
            f"n={n} B189 lastdeg {games_out[str(n)]['b189']['mean_last_deg']} "
            f"uniform {mean_deg_uniform} lowfrac {frac_low_last} vs {frac_low_uniform} "
            f"B190 corr need2/net {c2} need3 {c3} ratio {cR}",
            flush=True,
        )

    out["games"] = games_out

    # ---- B185: n=4 maximal sets reach probability ----
    print("=== B185 n=4 reach ===", flush=True)
    b = board_square(4)
    # enumerate all maximal safe sets
    maximal = []
    V = b.V

    def dfs(occ, cand):
        expanded = False
        c = cand
        while c:
            bit = c & -c
            v = bit.bit_length() - 1
            c ^= bit
            nxt = occ | bit
            ok = True
            for q in b.quads_by_pt[v]:
                if (q & nxt) == q:
                    ok = False
                    break
            if not ok:
                continue
            expanded = True
            remain = cand ^ bit
            bad = 0
            cc = remain
            while cc:
                bb = cc & -cc
                vv = bb.bit_length() - 1
                cc ^= bb
                for q in b.quads_by_pt[vv]:
                    if (q & nxt) == q:
                        bad |= bb
                        break
            dfs(nxt, remain & ~bad)
        if not expanded and occ:
            maximal.append(occ)

    dfs(0, (1 << V) - 1)
    print("n=4 maximal count", len(maximal), flush=True)

    # exact reach prob via DP: P(reach terminal T | occ) under random greedy
    # We want for each maximal T: P(random greedy ends at T)
    # DP: E[occ] = distribution over terminals
    # Too many maximal (928?) to store full dist; instead compute
    # reach probability per maximal by working backwards:
    # For random greedy, P(end at T) = sum over paths prod 1/|L|
    # Use memo: f(occ) = dict T->prob, but T can be compressed as we only need
    # specific T's. Instead compute for each maximal independently:
    # p_T(occ) = 0 if occ not subset of T or occ illegal
    # p_T(occ) = 1 if occ == T
    # p_T(occ) = sum_{u in L(occ), u in T} p_T(occ|u) / |L(occ)|   if L(occ) != empty
    #            0 if terminal but != T
    # This is still O(states * maximal). n=4 has 5811 safe states and ~928 maximal —
    # 5811*928 is large. Instead compute distribution of terminals from empty via
    # one DP storing dict of terminal -> prob. Number of terminals reached is <=928.
    # Memory: each state stores dict of up to 928 keys — too much.
    # Alternative: Monte Carlo with many runs for reach probs (not p_rand win).
    # Or: only compare size-5 (minimal) vs size-7 (maximum) reach rates by
    # first hitting a size class. Simpler MC:
    N = 20000
    reach = Counter()
    rng2 = random.Random(1)
    for _ in range(N):
        occ = 0
        while True:
            mv = b.legal_moves(occ)
            if not mv:
                reach[occ] += 1
                break
            occ |= 1 << mv[rng2.randrange(len(mv))]
    # map terminals to size and count
    by_size = Counter()
    for occ, cnt in reach.items():
        by_size[occ.bit_count()] += cnt
    # minimal maximal size=5, max=7
    # exact fractions among the 20000
    total = sum(reach.values())
    # identify how many distinct maximal of each size were hit
    hit_by_size = Counter()
    for occ, cnt in reach.items():
        hit_by_size[occ.bit_count()] += 1
    # also: distribution of reach prob within size-5 vs size-7
    size5_probs = [cnt / total for occ, cnt in reach.items() if occ.bit_count() == 5]
    size7_probs = [cnt / total for occ, cnt in reach.items() if occ.bit_count() == 7]
    size6_probs = [cnt / total for occ, cnt in reach.items() if occ.bit_count() == 6]
    out["b185_n4_mc"] = {
        "N": N,
        "n_distinct_terminals_hit": len(reach),
        "n_maximal_total": len(maximal),
        "hit_by_size": dict(hit_by_size),
        "mass_by_size": {str(k): v / total for k, v in sorted(by_size.items())},
        "size5_reach_min_max": (min(size5_probs), max(size5_probs)) if size5_probs else None,
        "size6_reach_min_max": (min(size6_probs), max(size6_probs)) if size6_probs else None,
        "size7_reach_min_max": (min(size7_probs), max(size7_probs)) if size7_probs else None,
        "size5_reach_mean": (sum(size5_probs) / len(size5_probs)) if size5_probs else None,
        "size7_reach_mean": (sum(size7_probs) / len(size7_probs)) if size7_probs else None,
        "ratio_mean_size5_over_size7": (
            (sum(size5_probs) / len(size5_probs)) / (sum(size7_probs) / len(size7_probs))
            if size5_probs and size7_probs and sum(size7_probs) > 0
            else None
        ),
    }
    print("B185", out["b185_n4_mc"], flush=True)

    # exact for n=4 using recursive expected count of each terminal via
    # "occupancy of paths": actually we can do exact DP on subsets of terminals
    # by grouping terminals — skip, MC is enough for this pass.

    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()
