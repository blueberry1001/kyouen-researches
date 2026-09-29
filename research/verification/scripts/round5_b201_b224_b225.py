#!/usr/bin/env python3
"""B224: sub-family of forbidden quads reproducing standard W.
B225: q-point (q=5) cocircular ban, saturation / max-g vs occupancy.
"""
from __future__ import annotations

import sys
import time
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, board_square, det4, is_forbidden_quad  # noqa: E402


def build_custom(pts, quads_ids):
    b = Board(pts, name="custom")
    b.quads = []
    b.quads_by_pt = [[] for _ in range(len(pts))]
    for ids in quads_ids:
        m = 0
        for i in ids:
            m |= 1 << i
        b.quads.append(m)
        for i in ids:
            b.quads_by_pt[i].append(m)
    return b


def job_subfam(w, h):
    pts = [(x, y) for y in range(h) for x in range(w)]
    V = w * h
    quads = []
    for ids in combinations(range(V), 4):
        p4 = [pts[t] for t in ids]
        if is_forbidden_quad(p4):
            quads.append(ids)
    std = build_custom(pts, quads)
    g = std.solve_grundy()
    W_std = sorted(u for u in std.legal_moves(0) if g.get(1 << u, 0) == 0)
    g0 = g[0]
    print(f"{w}x{h} standard: g0={g0} |W|={len(W_std)} W={W_std} quads={len(quads)}", flush=True)

    # try every single quad
    for i, q in enumerate(quads):
        b = build_custom(pts, [q])
        gq = b.solve_grundy()
        Wq = sorted(u for u in b.legal_moves(0) if gq.get(1 << u, 0) == 0)
        if Wq == W_std and gq[0] == g0:
            print(f"  MATCH size1: {q}", flush=True)
            return {"size": 1, "quads": [list(q)], "W": W_std, "g0": g0}
    print("  no size-1 match", flush=True)

    # try pairs, but only quads that appear in some "tight" configuration
    # limit to first 80 quads to keep runtime sane
    limit = min(len(quads), 80)
    for i, j in combinations(range(limit), 2):
        b = build_custom(pts, [quads[i], quads[j]])
        gq = b.solve_grundy()
        Wq = sorted(u for u in b.legal_moves(0) if gq.get(1 << u, 0) == 0)
        if Wq == W_std and gq[0] == g0:
            print(f"  MATCH size2: {quads[i]} {quads[j]}", flush=True)
            return {
                "size": 2,
                "quads": [list(quads[i]), list(quads[j])],
                "W": W_std,
                "g0": g0,
            }
    print("  no size-2 match (first 80)", flush=True)
    return {"size": None, "W": W_std, "g0": g0, "n_quads": len(quads)}


def qcol_det(pts, ids):
    """det for 4-subsets of a q-tuple; for q=5 we need 5 concyclic iff all 4-subsets det=0?
    Actually 5 concyclic is stronger. Use: 5 points concyclic if they lie on a common circle.
    Integer test: for 5 points, they are concyclic iff every 4-subset has det=0
    AND they are not in a degenerate configuration. That's the standard test.
    """
    from itertools import combinations as C

    for sub in C(ids, 4):
        p4 = [pts[t] for t in sub]
        if not is_forbidden_quad(p4):
            return False
    return True


def job_q5(n):
    """Forbid any 5 concyclic points. Compute K and max g on n x n."""
    pts = [(x, y) for y in range(n) for x in range(n)]
    V = n * n
    quints = []
    for ids in combinations(range(V), 5):
        if qcol_det(pts, ids):
            quints.append(ids)
    print(f"n={n} 5-cocircular sets: {len(quints)}", flush=True)
    # Build as Board with quads replaced by quintuples
    b = Board(pts, name=f"q5_{n}")
    b.quads = []
    b.quads_by_pt = [[] for _ in range(V)]
    for ids in quints:
        m = 0
        for i in ids:
            m |= 1 << i
        b.quads.append(m)
        for i in ids:
            b.quads_by_pt[i].append(m)
    t = time.time()
    g = b.solve_grundy()
    K = max(occ.bit_count() for occ in g)
    W = [u for u in b.legal_moves(0) if g.get(1 << u, 0) == 0]
    max_g = max(g.values())
    # occupancy at which max_g is first reached
    first_max = min(occ.bit_count() for occ, gv in g.items() if gv == max_g)
    print(
        f"  q5 n={n}: g0={g[0]} K={K} max_g={max_g} first_max_g_occ={first_max} "
        f"|W|={len(W)} pos={len(g)} {time.time()-t:.1f}s",
        flush=True,
    )
    return {
        "n_quints": len(quints),
        "g0": g[0],
        "K": K,
        "max_g": max_g,
        "first_max_g_occ": first_max,
        "W": len(W),
        "npos": len(g),
    }


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "subfam":
        w, h = int(sys.argv[2]), int(sys.argv[3])
        r = job_subfam(w, h)
        print("RESULT", r)
    elif cmd == "q5":
        n = int(sys.argv[2])
        r = job_q5(n)
        print("RESULT", r)
