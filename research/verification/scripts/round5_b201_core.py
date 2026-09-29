#!/usr/bin/env python3
"""Round5 B201-B230: batch computations.

Jobs (selected via argv[1]):
  maxcov   n          - maximal-config point coverage (B205)
  pairK    n          - two-point deletion K / g combo (B207)
  rect3    m_max      - 3xm g0/W/K for m=4..m_max (B213,B219,B220)
  passwit  n          - pass-variant same-g witness search (B227)
  stage    n          - stage-wise P/N disagreement std vs circles-only (B223)
  subfam   n          - sub-family of quads reproducing W (B224)
  misere   n          - misere empty winner (B226)
  del1ext  n          - square n + one exterior point, winner (B208 weaken)
  tol      n thr      - near-cocircular threshold quads (B229)
  mediate  n          - mediation metric vs degree (B206)
  wchange  n          - W-size change under 1-point deletion (B201 side info)
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import (  # noqa: E402
    Board,
    board_rect,
    board_square,
    board_square_minus,
    det4,
    is_forbidden_quad,
)

OUTDIR = Path(__file__).resolve().parents[1]


def save(name: str, obj) -> None:
    p = OUTDIR / f"round5_b201_{name}.json"
    p.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote {p}", flush=True)


def solve_g(b: Board):
    g = b.solve_grundy()
    return g


def winner_from_g(g0: int) -> str:
    return "First" if g0 != 0 else "Second"


def winning_first_moves(b: Board, g) -> list[int]:
    w = []
    for u in b.legal_moves(0):
        if g.get(1 << u, 0) == 0:
            w.append(u)
    return w


# ---------------------------------------------------------------- jobs


def job_maxcov(n: int) -> None:
    """List every maximal safe set of size K and which points appear in some max set."""
    b = board_square(n)
    K = b.max_safe_size()
    maxes: list[int] = []
    sys.setrecursionlimit(100000)

    def dfs(occ: int, cand: int, size: int) -> None:
        if size == K:
            maxes.append(occ)
            return
        if size + cand.bit_count() < K:
            return
        while cand:
            bit = cand & -cand
            v = bit.bit_length() - 1
            cand ^= bit
            nxt = occ | bit
            if not b.is_safe(nxt):
                continue
            remain = cand
            bad = 0
            for q in b.quads_by_pt[v]:
                if (q & nxt) == q:
                    pass
                elif (q & ~nxt & b.full).bit_count() == 1:
                    bad |= q & ~nxt
            dfs(nxt, remain & ~bad, size + 1)

    dfs(0, b.full, 0)
    covered = set()
    for m in maxes:
        mm = m
        while mm:
            bit = mm & -mm
            covered.add(bit.bit_length() - 1)
            mm ^= bit
    never = [i for i in range(b.V) if i not in covered]
    # also count how many max sets contain each point
    counts = [0] * b.V
    for m in maxes:
        mm = m
        while mm:
            bit = mm & -mm
            counts[bit.bit_length() - 1] += 1
            mm ^= bit
    save(
        f"maxcov_n{n}",
        {
            "n": n,
            "K": K,
            "n_maximal": len(maxes),
            "points_never_in_max": never,
            "never_coords": [(i % n, i // n) for i in never],
            "contain_counts": counts,
            "min_count": min(counts) if counts else 0,
            "max_count": max(counts) if counts else 0,
        },
    )


def job_pairK(n: int) -> None:
    """All two-point deletions on n x n: K and empty g. Look for K-loss / combo g."""
    base = board_square(n)
    g_base = solve_g(base)
    K_base = base.max_safe_size()
    rows = []
    n_kloss = 0
    n_combo = 0
    V = n * n
    t0 = time.time()
    for i, j in combinations(range(V), 2):
        di = (i % n, i // n)
        dj = (j % n, j // n)
        b = board_square_minus(n, [di, dj])
        # rename local ids: Board builds its own indexing
        g = solve_g(b)
        K = max(occ.bit_count() for occ in g.keys())
        g0 = g[0]
        bi = board_square_minus(n, [di])
        bj = board_square_minus(n, [dj])
        gi = solve_g(bi)[0]
        gj = solve_g(bj)[0]
        combo = (g0 != g_base[0]) and (gi == g_base[0]) and (gj == g_base[0])
        kloss = K < K_base
        if kloss:
            n_kloss += 1
        if combo:
            n_combo += 1
        rows.append(
            {
                "pair": [di, dj],
                "ids": [i, j],
                "K": K,
                "g0": g0,
                "g_one": [gi, gj],
                "g_base": g_base[0],
                "K_base": K_base,
                "kloss": kloss,
                "combo": combo,
            }
        )
        if (len(rows) % 50) == 0:
            print(f"  pair {len(rows)} t={time.time()-t0:.1f}s", flush=True)
    save(
        f"pairK_n{n}",
        {
            "n": n,
            "K_base": K_base,
            "g_base": g_base[0],
            "n_pairs": len(rows),
            "n_kloss": n_kloss,
            "n_combo": n_combo,
            "rows": rows,
        },
    )


def job_rect3(m_max: int) -> None:
    """3 x m boards: g0, W, K for m = 3..m_max."""
    out = []
    for m in range(3, m_max + 1):
        t0 = time.time()
        b = board_rect(3, m)
        g = solve_g(b)
        K = max(occ.bit_count() for occ in g.keys())
        W = winning_first_moves(b, g)
        rec = {
            "w": 3,
            "m": m,
            "V": b.V,
            "F": len(b.quads),
            "g0": g[0],
            "winner": winner_from_g(g[0]),
            "K": K,
            "W": W,
            "W_coords": [(u % 3, u // 3) for u in W],
            "n_pos": len(g),
            "seconds": round(time.time() - t0, 2),
        }
        out.append(rec)
        print(
            f"  3x{m}: g0={g[0]} K={K} |W|={len(W)} pos={len(g)} {rec['seconds']}s",
            flush=True,
        )
    save("rect3", {"boards": out})


def job_passwit(n: int) -> None:
    """Search positions with same normal g but different pass-variant outcome.

    Pass rule: each player may pass at most once. State = (occ, mask)
    mask bit0 = current player has pass left, bit1 = opponent has pass left.
    We only need to distinguish: among reachable occ with the same normal g,
    do pass-outcomes (starting with both passes available) differ?
    """
    b = board_square(n)
    g = solve_g(b)

    # memo for pass game: (occ, p0, p1) -> win for player to move
    # p0/p1 are booleans: can this player still pass? We track whose turn by parity of popcount.
    from functools import lru_cache

    def player_of(occ: int) -> int:
        return occ.bit_count() % 2  # 0 = first player (odd stones? careful)
        # empty: 0 stones, first to move. After 1 stone, second to move.
        # so player-to-move = 0 if popcount even, 1 if odd.

    @lru_cache(maxsize=None)
    def pass_win(occ: int, pass_left_0: int, pass_left_1: int) -> int:
        """1 if current player wins under pass-variant. Current is player_of(occ)."""
        me = player_of(occ)
        my_pass = pass_left_0 if me == 0 else pass_left_1
        opp_pass = pass_left_1 if me == 0 else pass_left_0
        # try normal moves
        for u in b.legal_moves(occ):
            child = occ | (1 << u)
            # turn flips; pass rights unchanged
            if me == 0:
                r = pass_win(child, pass_left_0, pass_left_1)
            else:
                r = pass_win(child, pass_left_0, pass_left_1)
            # after move, opponent is to move at child; if opponent loses there, we win
            # pass_win(child) is win for player to move at child = opponent
            if r == 0:
                return 1
        # try pass if available
        if my_pass:
            if me == 0:
                # pass: turn goes to player 1, I lose my pass
                r = pass_win(occ, 0, pass_left_1)
            else:
                r = pass_win(occ, pass_left_0, 0)
            # after pass, opponent to move at same occ; if opponent loses, we win
            if r == 0:
                return 1
        return 0

    # outcome from empty with both passes
    empty_both = pass_win(0, 1, 1)
    # classify each reachable occ by (g[occ], pass outcome with both passes)
    groups: dict[int, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
    for occ in g.keys():
        # only positions reachable under normal play; pass may reach same occ
        pv = pass_win(occ, 1, 1)
        groups[g[occ]][pv].append(occ)

    witnesses = []
    for gv, by in groups.items():
        if 0 in by and 1 in by:
            witnesses.append(
                {
                    "g": gv,
                    "n_P_pass": len(by[0]),
                    "n_N_pass": len(by[1]),
                    "example_P": by[0][:5],
                    "example_N": by[1][:5],
                }
            )

    # also empty with asymmetric pass rights
    empty_1p = pass_win(0, 1, 0)  # first has pass, second does not? me=0 at empty
    save(
        f"passwit_n{n}",
        {
            "n": n,
            "normal_g0": g[0],
            "normal_winner": winner_from_g(g[0]),
            "pass_empty_both": empty_both,
            "pass_winner_both": winner_from_g(empty_both),
            "pass_empty_first_only": empty_1p,
            "same_g_split_witnesses": witnesses,
            "n_positions": len(g),
        },
    )


def job_stage(n: int) -> None:
    """Stage-wise P/N disagreement between standard and circles-only."""
    # build both families
    pts = [(x, y) for y in range(n) for x in range(n)]
    V = n * n
    std_quads = []
    circ_quads = []
    coll_quads = []
    for ids in combinations(range(V), 4):
        p4 = [pts[i] for i in ids]
        if is_forbidden_quad(p4):
            std_quads.append(ids)
            # collinear?
            (x0, y0), (x1, y1), (x2, y2), (x3, y3) = p4
            area = (x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0)
            coll = True
            for a, bb, c in combinations(p4, 3):
                ax, ay = a
                bx, by = bb
                cx, cy = c
                if (bx - ax) * (cy - ay) - (by - ay) * (cx - ax) != 0:
                    coll = False
                    break
            if coll:
                coll_quads.append(ids)
            else:
                circ_quads.append(ids)

    def build(quads):
        b = Board(pts, name=f"n{n}")
        # Board already computes all quads; we need filtered. Rebuild manually.
        return quads

    # use Board but override quads — easier to use batch10 Game
    from batch10_core import Game, grundy_map

    gstd = grundy_map(Game(n, std_quads), 0)
    gcirc = grundy_map(Game(n, circ_quads), 0)

    # stage-wise: among safe sets (under standard) with k stones, fraction where P/N differs
    # We only have grundy maps keyed by occ reachable in each game.
    # Intersect on positions safe under standard.
    std_safe_occ = set(gstd.keys())
    # actually grundy_map may only include reachable; use all subsets? For n<=5, enumerate all safe.
    stages = defaultdict(lambda: {"n": 0, "n_diff": 0, "n_only_std": 0, "n_only_circ": 0})
    all_occ = set(gstd.keys()) | set(gcirc.keys())
    for occ in all_occ:
        k = occ.bit_count()
        a = gstd.get(occ)
        bb = gcirc.get(occ)
        st = stages[k]
        st["n"] += 1
        if a is None:
            st["n_only_circ"] += 1
        elif bb is None:
            st["n_only_std"] += 1
        elif (a == 0) != (bb == 0):
            st["n_diff"] += 1

    save(
        f"stage_n{n}",
        {
            "n": n,
            "n_std_quads": len(std_quads),
            "n_circ_quads": len(circ_quads),
            "n_coll_quads": len(coll_quads),
            "std_g0": gstd.get(0),
            "circ_g0": gcirc.get(0),
            "stages": {str(k): dict(v) for k, v in sorted(stages.items())},
        },
    )


def job_subfam(n: int) -> None:
    """Find a small sub-family of forbidden quads that reproduces standard W_n."""
    from batch10_core import Game, first_move_labels, forbidden_quads, grundy_map

    quads = forbidden_quads(n)
    g = grundy_map(Game(n, quads), 0)
    W_std = sorted(p for p, lab in first_move_labels(Game(n, quads), g).items() if lab == "Win")
    g0 = g[0]

    # greedy: start empty family, add quads that fix mismatches
    selected: list = []
    # try size-1,2,... subsets of most "important" quads = those covering a W-losing point?
    # Practical: rank quads by how much they reduce |W| toward target when added alone.
    # Full search for tiny families:
    best = None
    # first try all single quads
    for i, q in enumerate(quads):
        gq = grundy_map(Game(n, [q]), 0)
        Wq = sorted(p for p, lab in first_move_labels(Game(n, [q]), gq).items() if lab == "Win")
        if Wq == W_std and (gq[0] == g0):
            best = {"size": 1, "quads": [list(q)], "W": Wq, "g0": gq[0]}
            break
    if best is None:
        # pairs
        for i, j in combinations(range(len(quads)), 2):
            fam = [quads[i], quads[j]]
            gq = grundy_map(Game(n, fam), 0)
            Wq = sorted(p for p, lab in first_move_labels(Game(n, fam), gq).items() if lab == "Win")
            if Wq == W_std and gq[0] == g0:
                best = {"size": 2, "quads": [list(quads[i]), list(quads[j])], "W": Wq, "g0": gq[0]}
                break

    save(
        f"subfam_n{n}",
        {
            "n": n,
            "n_quads": len(quads),
            "W_std": W_std,
            "g0_std": g0,
            "best": best,
        },
    )


def job_misere(n: int) -> None:
    """Misere empty-board winner on n x n (and 1-point deletions if n<=5)."""
    b = board_square(n)
    # misere: player who makes last legal move LOSES.
    # terminal (no move) => previous player made last move and lost => current WINS.
    from functools import lru_cache

    @lru_cache(maxsize=None)
    def win(occ: int) -> int:
        moves = b.legal_moves(occ)
        if not moves:
            return 1  # current wins
        for u in moves:
            if win(occ | (1 << u)) == 0:
                return 1
        return 0

    empty = win(0)
    # also normal for comparison
    g = solve_g(b)
    rec = {
        "n": n,
        "normal_g0": g[0],
        "normal_winner": winner_from_g(g[0]),
        "misere_empty": empty,
        "misere_winner": winner_from_g(empty),
        "agree": winner_from_g(empty) == winner_from_g(g[0]),
    }
    # sample some 1-point deletions if n<=5
    if n <= 5:
        dels = []
        for p in range(n * n):
            bb = board_square_minus(n, [(p % n, p // n)])

            @lru_cache(maxsize=None)
            def winb(occ: int) -> int:
                moves = bb.legal_moves(occ)
                if not moves:
                    return 1
                for u in moves:
                    if winb(occ | (1 << u)) == 0:
                        return 1
                return 0

            gb = solve_g(bb)
            mb = winb(0)
            dels.append(
                {
                    "p": (p % n, p // n),
                    "normal_g0": gb[0],
                    "normal": winner_from_g(gb[0]),
                    "misere": winner_from_g(mb),
                    "agree": winner_from_g(mb) == winner_from_g(gb[0]),
                }
            )
        rec["deletions"] = dels
        rec["n_del_agree"] = sum(1 for d in dels if d["agree"])
    save(f"misere_n{n}", rec)


def job_del1ext(n: int) -> None:
    """n x n plus one exterior point at various offsets; does winner change?"""
    base = board_square(n)
    g_base = solve_g(base)
    rows = []
    offsets = []
    # ring of exterior points: just outside the square
    for x in range(-1, n + 1):
        for y in range(-1, n + 1):
            if 0 <= x < n and 0 <= y < n:
                continue
            if abs(x - (n - 1) / 2) <= n and abs(y - (n - 1) / 2) <= n:
                offsets.append((x, y))
    for ox, oy in offsets:
        pts = [(x, y) for y in range(n) for x in range(n)] + [(ox, oy)]
        b = Board(pts, name=f"{n}x{n}+({ox},{oy})")
        g = solve_g(b)
        K = max(occ.bit_count() for occ in g.keys())
        W = winning_first_moves(b, g)
        rows.append(
            {
                "outer": [ox, oy],
                "V": b.V,
                "F": len(b.quads),
                "g0": g[0],
                "winner": winner_from_g(g[0]),
                "K": K,
                "Wsize": len(W),
                "changed": winner_from_g(g[0]) != winner_from_g(g_base[0]),
            }
        )
        print(f"  +({ox},{oy}) g0={g[0]} K={K} changed={rows[-1]['changed']}", flush=True)
    save(
        f"del1ext_n{n}",
        {
            "n": n,
            "base_g0": g_base[0],
            "base_winner": winner_from_g(g_base[0]),
            "rows": rows,
            "n_changed": sum(1 for r in rows if r["changed"]),
            "n_same": sum(1 for r in rows if not r["changed"]),
        },
    )


def job_tol(n: int, thr: int) -> None:
    """Near-cocircular: forbid quads with 0 < |det| <= thr (plus exact 0).
    Measure how K / max-config symmetry changes vs thr.
    """
    pts = [(x, y) for y in range(n) for x in range(n)]
    V = n * n
    # collect |det| for all 4-subsets
    dets = []
    for ids in combinations(range(V), 4):
        p4 = [pts[i] for i in ids]
        d = det4(
            (p4[0][0] ** 2 + p4[0][1] ** 2, p4[0][0], p4[0][1], 1),
            (p4[1][0] ** 2 + p4[1][1] ** 2, p4[1][0], p4[1][1], 1),
            (p4[2][0] ** 2 + p4[2][1] ** 2, p4[2][0], p4[2][1], 1),
            (p4[3][0] ** 2 + p4[3][1] ** 2, p4[3][0], p4[3][1], 1),
        )
        dets.append((abs(d), ids))
    dets.sort()
    levels = {}
    for t in range(1, thr + 1):
        extra = [ids for ad, ids in dets if 0 < ad <= t]
        exact = [ids for ad, ids in dets if ad == 0]
        fam = exact + extra
        b = Board(pts, name=f"tol{t}")
        # override quads: rebuild Board is easier with custom points list identical
        # We construct a Board and then replace quads — instead filter via is_safe later.
        # Compute K and n_maximal with custom quads:
        quads = []
        qbp = [[] for _ in range(V)]
        for ids in fam:
            m = 0
            for i in ids:
                m |= 1 << i
            quads.append(m)
            for i in ids:
                qbp[i].append(m)
        full = (1 << V) - 1

        def is_safe(occ: int) -> bool:
            for q in quads:
                if (occ & q) == q:
                    return False
            return True

        best = 0
        nmax = 0

        def dfs(occ, cand, size):
            nonlocal best, nmax
            if size > best:
                best = size
            if not cand:
                if size == best:
                    pass
                return
            if size + cand.bit_count() < best:
                return
            while cand:
                bit = cand & -cand
                v = bit.bit_length() - 1
                cand ^= bit
                nxt = occ | bit
                ok = True
                for q in qbp[v]:
                    if (q & nxt) == q:
                        ok = False
                        break
                if not ok:
                    continue
                remain = cand
                bad = 0
                for q in qbp[v]:
                    if (q & nxt) != q and (q & ~nxt & full).bit_count() == 1:
                        bad |= q & ~nxt
                dfs(nxt, remain & ~bad, size + 1)

        dfs(0, full, 0)
        levels[t] = {"n_extra_quads": len(extra), "n_quads": len(fam), "K": best}
        print(f"  thr={t} extra={len(extra)} K={best}", flush=True)
    save(f"tol_n{n}_thr{thr}", {"n": n, "levels": levels, "det_min_nonzero": dets[0][0] if dets else None})


def job_mediate(n: int) -> None:
    """B206: degree vs 'winning-move frequency' as mediation proxy on n x n."""
    b = board_square(n)
    g = solve_g(b)
    V = n * n
    # degree in collinearity/cocircularity hypergraph: number of quads containing p
    deg = [len(b.quads_by_pt[i]) for i in range(V)]
    # winning-move frequency: over all N-positions, how often is p a move to a P-position
    win_freq = [0] * V
    gate = [0] * V  # how many legal moves from occ where p blocks others (|legal after add| < |legal|-1)
    for occ, gv in g.items():
        if gv == 0:
            continue  # P-position: no winning move for player to move... actually from P all moves go to N
        moves = b.legal_moves(occ)
        for u in moves:
            if g.get(occ | (1 << u), 0) == 0:
                win_freq[u] += 1
        for u in moves:
            nxt = occ | (1 << u)
            after = b.legal_moves(nxt)
            if len(after) < max(0, len(moves) - 1):
                gate[u] += 1
    # correlation of deg vs win_freq
    def pearson(a, c):
        ma = sum(a) / len(a)
        mc = sum(c) / len(c)
        num = sum((x - ma) * (y - mc) for x, y in zip(a, c))
        da = sum((x - ma) ** 2 for x in a) ** 0.5
        dc = sum((y - mc) ** 2 for y in c) ** 0.5
        return num / (da * dc) if da and dc else 0.0

    save(
        f"mediate_n{n}",
        {
            "n": n,
            "deg": deg,
            "win_freq": win_freq,
            "gate": gate,
            "corr_deg_win": pearson(deg, win_freq),
            "corr_deg_gate": pearson(deg, gate),
            "corr_win_gate": pearson(win_freq, gate),
            "g0": g[0],
        },
    )


def job_wchange(n: int) -> None:
    """B201 side: W set / |W| change under every 1-point deletion."""
    base = board_square(n)
    g = solve_g(base)
    W0 = winning_first_moves(base, g)
    rows = []
    for p in range(n * n):
        b = board_square_minus(n, [(p % n, p // n)])
        gb = solve_g(b)
        W = winning_first_moves(b, gb)
        K = max(occ.bit_count() for occ in gb.keys())
        rows.append(
            {
                "p": (p % n, p // n),
                "g0": gb[0],
                "K": K,
                "Wsize": len(W),
                "W": W,
                "W_delta_vs_base": sorted(set(W) ^ set(W0)),
                "winner_changed": winner_from_g(gb[0]) != winner_from_g(g[0]),
            }
        )
    save(
        f"wchange_n{n}",
        {
            "n": n,
            "base_g0": g[0],
            "base_W": W0,
            "base_Wsize": len(W0),
            "rows": rows,
        },
    )


def main() -> None:
    job = sys.argv[1]
    if job == "maxcov":
        job_maxcov(int(sys.argv[2]))
    elif job == "pairK":
        job_pairK(int(sys.argv[2]))
    elif job == "rect3":
        job_rect3(int(sys.argv[2]))
    elif job == "passwit":
        job_passwit(int(sys.argv[2]))
    elif job == "stage":
        job_stage(int(sys.argv[2]))
    elif job == "subfam":
        job_subfam(int(sys.argv[2]))
    elif job == "misere":
        job_misere(int(sys.argv[2]))
    elif job == "del1ext":
        job_del1ext(int(sys.argv[2]))
    elif job == "tol":
        job_tol(int(sys.argv[2]), int(sys.argv[3]))
    elif job == "mediate":
        job_mediate(int(sys.argv[2]))
    elif job == "wchange":
        job_wchange(int(sys.argv[2]))
    else:
        print("unknown job", job)
        sys.exit(1)


if __name__ == "__main__":
    main()
