#!/usr/bin/env python3
"""Variant comparison on rectangles: standard / circles-only / lines-only.
Supports B218, B221, B222.
"""
from __future__ import annotations

import sys
import time
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, is_forbidden_quad  # noqa: E402


def area2(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def is_coll4(p4):
    return all(
        area2(p4[a], p4[b], p4[c]) == 0
        for a, b, c in [(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)]
    )


def variant(w: int, h: int, mode: str) -> dict:
    pts = [(x, y) for y in range(h) for x in range(w)]
    V = w * h
    quads = []
    n_coll = 0
    n_circ = 0
    for ids in combinations(range(V), 4):
        p4 = [pts[t] for t in ids]
        if not is_forbidden_quad(p4):
            continue
        col = is_coll4(p4)
        if col:
            n_coll += 1
        else:
            n_circ += 1
        if mode == "std" or (mode == "circ" and not col) or (mode == "line" and col):
            quads.append(ids)
    b = Board(pts, name=f"{w}x{h}-{mode}")
    b.quads = []
    b.quads_by_pt = [[] for _ in range(V)]
    for ids in quads:
        m = 0
        for i in ids:
            m |= 1 << i
        b.quads.append(m)
        for i in ids:
            b.quads_by_pt[i].append(m)
    g = b.solve_grundy()
    K = max(occ.bit_count() for occ in g)
    W = [u for u in b.legal_moves(0) if g.get(1 << u, 0) == 0]
    return {
        "g0": g[0],
        "K": K,
        "W": len(W),
        "W_list": W,
        "npos": len(g),
        "nq": len(quads),
        "n_coll": n_coll,
        "n_circ": n_circ,
    }


def main():
    pairs = [(2, 6), (2, 8), (3, 5), (3, 6), (3, 7)]
    for w, h in pairs:
        row = {"w": w, "h": h}
        for mode in ["std", "circ", "line"]:
            t = time.time()
            r = variant(w, h, mode)
            r["sec"] = round(time.time() - t, 2)
            row[mode] = r
            print(
                f"{w}x{h} {mode}: g0={r['g0']} K={r['K']} |W|={r['W']} "
                f"pos={r['npos']} quads={r['nq']} {r['sec']}s",
                flush=True,
            )
        # disagreement on common positions: compare winners of empty
        agree_empty = (row["std"]["g0"] == 0) == (row["circ"]["g0"] == 0)
        print(f"  empty agree std/circ? {agree_empty}", flush=True)


if __name__ == "__main__":
    main()
