#!/usr/bin/env python3
"""Batch 04 follow-ups: exact B062 coloring, fixed B067 K(S), B078 s_n on n=6.

Outputs research/verification/batch04_followup.json
"""
from __future__ import annotations

import json
import struct
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))

from kyouen_core import Board, board_square  # noqa: E402

OUT = ROOT / "research" / "verification" / "batch04_followup.json"
sys.setrecursionlimit(200000)


def all_safe_masks(board: Board) -> list[int]:
    out: list[int] = []

    def dfs(next_id: int, occ: int) -> None:
        out.append(occ)
        for v in range(next_id, board.V):
            bit = 1 << v
            ok = True
            for q in board.quads_by_pt[v]:
                if (q & occ) == (q & ~bit):
                    ok = False
                    break
            if ok:
                dfs(v + 1, occ | bit)

    dfs(0, 0)
    return out


def residual_info(board: Board, S: int):
    legal = board.legal_moves(S)
    lmask = 0
    for p in legal:
        lmask |= 1 << p
    resid2: set[int] = set()
    for q in board.quads:
        r = q & ~S
        if r.bit_count() == 2 and (r & lmask) == r:
            resid2.add(r)
    return lmask, resid2


def build_adj(board: Board, edges: set[int], lmask: int):
    legal_pts = [p for p in range(board.V) if (lmask >> p) & 1]
    idx = {p: i for i, p in enumerate(legal_pts)}
    adj = [0] * len(legal_pts)  # bitmask adjacency
    for e in edges:
        pts = [p for p in legal_pts if (e >> p) & 1]
        if len(pts) != 2:
            continue
        a, b = idx[pts[0]], idx[pts[1]]
        adj[a] |= 1 << b
        adj[b] |= 1 << a
    return legal_pts, adj


def chromatic_exact(adj_bm: list[int], cap: int) -> int | None:
    """Exact chromatic number if chi<=cap else None (meaning chi>cap).
    Bitmask DSATUR."""
    n = len(adj_bm)
    if n == 0:
        return 0

    def color_ok(colors: list[int], v: int, c: int) -> bool:
        u = adj_bm[v]
        while u:
            b = u & -u
            w = b.bit_length() - 1
            u ^= b
            if colors[w] == c:
                return False
        return True

    colors = [-1] * n

    def dfs(used: int) -> int | None:
        # pick uncolored vertex with max uncolored-degree (DSATUR approx)
        best = -1
        best_key = (-1, -1)
        for v in range(n):
            if colors[v] >= 0:
                continue
            # saturation = number of distinct colors among neighbors
            sat = 0
            seen = 0
            u = adj_bm[v]
            while u:
                b = u & -u
                w = b.bit_length() - 1
                u ^= b
                if colors[w] >= 0 and not (seen & (1 << colors[w])):
                    seen |= 1 << colors[w]
                    sat += 1
            deg = adj_bm[v].bit_count()
            key = (sat, deg)
            if key > best_key:
                best_key = key
                best = v
        if best < 0:
            return used
        v = best
        for c in range(min(used + 1, cap)):
            if color_ok(colors, v, c):
                colors[v] = c
                r = dfs(max(used, c + 1))
                if r is not None:
                    return r
                colors[v] = -1
        return None

    return dfs(0)


def is_tree_bm(adj_bm: list[int]) -> bool:
    n = len(adj_bm)
    e = sum(a.bit_count() for a in adj_bm) // 2
    if n == 0:
        return True
    if e != n - 1:
        return False
    seen = set()

    def dfs(u, p):
        seen.add(u)
        u_mask = adj_bm[u]
        while u_mask:
            b = u_mask & -u_mask
            v = b.bit_length() - 1
            u_mask ^= b
            if v == p:
                continue
            if v in seen:
                return False
            if not dfs(v, u):
                return False
        return True

    return dfs(0, -1) and len(seen) == n


def longest_induced_odd_cycle(adj_bm: list[int]) -> int | None:
    n = len(adj_bm)
    if n > 11:
        return None
    best = 0
    for k in range(3, n + 1, 2):
        for vs in combinations(range(n), k):
            vs_set = set(vs)
            good = True
            for v in vs:
                deg = sum(1 for u in vs_set if adj_bm[v] >> u & 1)
                if deg != 2:
                    good = False
                    break
            if not good:
                continue
            vis = set()
            stack = [vs[0]]
            while stack:
                u = stack.pop()
                if u in vis:
                    continue
                vis.add(u)
                u_mask = adj_bm[u]
                while u_mask:
                    b = u_mask & -u_mask
                    w = b.bit_length() - 1
                    u_mask ^= b
                    if w in vs_set and w not in vis:
                        stack.append(w)
            if len(vis) == k:
                best = max(best, k)
    return best if best else 0


def K_of_fixed(board: Board, S: int) -> int:
    """Max safe extension size. Adds ANY empty point (not just id > max(S))."""
    best = S.bit_count()

    def dfs(occ: int, start: int, sz: int) -> None:
        nonlocal best
        if sz > best:
            best = sz
        for v in range(start, board.V):
            if (occ >> v) & 1:
                continue
            bit = 1 << v
            ok = True
            for q in board.quads_by_pt[v]:
                if (q & occ) == (q & ~bit):
                    ok = False
                    break
            if ok:
                dfs(occ | bit, v + 1, sz + 1)

    # start at 0: added points in increasing id order, any empty point allowed
    dfs(S, 0, S.bit_count())
    return best


def main():
    result = {"b062": {}, "b067": {}, "b078_n6": {}, "b073_note": {}, "b074_orchard": {}}

    # ---------- B062 exact chromatic on all 3-stone positions n=2..5 ----------
    for n in range(2, 6):
        board = board_square(n)
        safe = all_safe_masks(board)
        chi_dist = Counter()
        violations = []
        checked = 0
        for S in safe:
            if S.bit_count() != 3:
                continue
            checked += 1
            lmask, resid2 = residual_info(board, S)
            legal_pts, adj = build_adj(board, resid2, lmask)
            if not adj:
                chi_dist[0] += 1
                continue
            chi = chromatic_exact(adj, cap=6)
            if chi is None:
                chi_dist[">5"] += 1
                violations.append({"n": n, "S": [p for p in range(board.V) if S >> p & 1], "chi": ">5"})
            else:
                chi_dist[chi] += 1
                if chi > 3 and len(violations) < 6:
                    violations.append({"n": n, "S": [p for p in range(board.V) if S >> p & 1], "chi": chi})
        result["b062"][f"{n}x{n}"] = {
            "checked": checked,
            "chi_dist": {str(k): v for k, v in sorted(chi_dist.items(), key=str)},
            "n_chi_gt3": sum(v for k, v in chi_dist.items() if k == ">5" or (isinstance(k, int) and k > 3)),
            "examples": violations[:6],
        }
        print(f"B062 {n}x{n} checked={checked} dist={dict(chi_dist)}", flush=True)

    # ---------- B067 with fixed K(S) ----------
    b067 = {"checked": 0, "violations": [], "near_terminal": 0}
    for n in range(2, 6):
        board = board_square(n)
        safe = all_safe_masks(board)
        # subsample for n=5
        step = 1 if n <= 4 else 2
        for S in safe[::step]:
            lmask, resid2 = residual_info(board, S)
            legal_pts, adj = build_adj(board, resid2, lmask)
            nv = len(adj)
            k = S.bit_count()
            # only need K when the position might be near-terminal
            # cheap necessary: K >= k + (max matching-ish); compute K always on n<=4
            if n <= 4:
                KS = K_of_fixed(board, S)
            else:
                lmv = board.legal_moves(S)
                if len(lmv) > 10:
                    continue
                KS = K_of_fixed(board, S)
            if KS - k <= 3:
                b067["near_terminal"] += 1
                if 3 <= nv <= 11:
                    b067["checked"] += 1
                    c = longest_induced_odd_cycle(adj)
                    if c and c >= 7:
                        b067["violations"].append(
                            {
                                "n": n,
                                "k": k,
                                "K": KS,
                                "S": [p for p in range(board.V) if S >> p & 1],
                                "odd": c,
                                "nv": nv,
                            }
                        )
        print(f"B067 after {n}: checked={b067['checked']} viol={len(b067['violations'])}", flush=True)
    result["b067"] = b067

    # ---------- B078: s_n and min_b on n=6 ----------
    # load n=6 geometry, enumerate all safe sets and find minimal maximal
    board6 = board_square(6)
    print("B078 n=6 enumerating all safe...", flush=True)
    safe6 = all_safe_masks(board6)
    print(f"  safe={len(safe6)}", flush=True)

    def b_vector(board, S):
        b = [0] * board.V
        for q in board.quads:
            inter = S & q
            if inter.bit_count() == 3:
                miss = q ^ inter
                b[miss.bit_length() - 1] += 1
        return b

    maximals = []
    for S in safe6:
        bv = b_vector(board6, S)
        empty = board6.full ^ S
        if any(empty >> p & 1 and bv[p] == 0 for p in range(board6.V)):
            continue
        vals = [bv[p] for p in range(board6.V) if (empty >> p) & 1]
        maximals.append((S, S.bit_count(), min(vals) if vals else 0, vals))
    s_n = min(m[1] for m in maximals)
    minrows = [m for m in maximals if m[1] == s_n]
    result["b078_n6"] = {
        "n_safe": len(safe6),
        "n_maximal": len(maximals),
        "s_n": s_n,
        "n_minimal_maximal": len(minrows),
        "all_have_b_eq_1": all(m[2] == 1 for m in minrows),
        "exists_b_eq_1": any(m[2] == 1 for m in minrows),
        "min_b_dist": dict(Counter(m[2] for m in minrows)),
        "examples_without_single": [
            {"S": [p for p in range(board6.V) if m[0] >> p & 1], "min_b": m[2]}
            for m in minrows
            if m[2] != 1
        ][:5],
    }
    print("B078", result["b078_n6"], flush=True)

    # ---------- B073/B074: orchard comparison ----------
    # b_S(p) equals number of 3-point lines of inverted S (Sylvester-Gallai applies).
    # Record known orchard numbers vs our max b at k.
    orchard = {3: 1, 4: 1, 5: 2, 6: 4, 7: 6, 8: 7, 9: 10, 10: 12, 11: 15, 12: 19}
    # our max b by k from geom results (n<=5 + n6 maxsafe)
    result["b073_note"] = {
        "argument": (
            "Inversion about p maps circles/lines through p to straight lines. "
            "b_S(p) = number of 3-point lines among the inverted images of S. "
            "Steiner equality (every pair in exactly one triple) would mean no ordinary line, "
            "contradicting Sylvester-Gallai for |S|>=4. Fano/STS(7) is not realizable over R. "
            "Hence B073 is false for |S|>=7."
        ),
        "steiner_bound": "floor(k(k-1)/6)",
        "orchard_real_plane_max": orchard,
    }
    result["b074_orchard"] = {
        "note": (
            "b_S(p) = orchard number t3(k) of inverted point set. Real-plane t3(k) grows "
            "quadratically (~k^2/6 - O(k)), so a lattice-independent linear bound is doubtful; "
            "lattice realization still open. Measured max b/k so far <= 0.91 at k=11."
        ),
        "measured_max_ratio": 0.91,
    }

    OUT.write_text(json.dumps(result, indent=2, default=str))
    print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
