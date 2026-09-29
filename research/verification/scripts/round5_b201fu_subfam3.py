#!/usr/bin/env python3
"""B224: find small forbidden-quad subfamilies on 3x4 reproducing standard W."""
from __future__ import annotations

import json
import sys
import time
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, board_rect  # noqa: E402

OUTDIR = Path(__file__).resolve().parents[1]


def solve_family(quads_masks, pts, name):
    b = Board(pts, name=name)
    # override quads
    b.quads = list(quads_masks)
    b.quads_by_pt = [[] for _ in range(b.V)]
    for m in b.quads:
        mm = m
        i = 0
        while mm:
            if mm & 1:
                b.quads_by_pt[i].append(m)
            mm >>= 1
            i += 1
    g = b.solve_grundy()
    W = [u for u in b.legal_moves(0) if g.get(1 << u, 0) == 0]
    return g[0], sorted(W), g


def main():
    w, h = 3, 4
    pts = [(x, y) for y in range(h) for x in range(w)]
    base = board_rect(w, h)
    quads = list(base.quads)  # masks
    g0, W, _ = solve_family(quads, pts, "std")
    print(f"standard: g0={g0} W={W} nq={len(quads)}", flush=True)

    t0 = time.time()
    best = None
    # singles
    for i, q in enumerate(quads):
        gi, Wi, _ = solve_family([q], pts, f"s{i}")
        if Wi == W and gi == g0:
            best = {"size": 1, "quads": [q], "W": Wi, "g0": gi, "at": i}
            break
    if best is None:
        # pairs
        for i, j in combinations(range(len(quads)), 2):
            gi, Wi, _ = solve_family([quads[i], quads[j]], pts, "p")
            if Wi == W and gi == g0:
                best = {
                    "size": 2,
                    "quads": [quads[i], quads[j]],
                    "W": Wi,
                    "g0": gi,
                    "at": (i, j),
                }
                break
    if best is None:
        nq = len(quads)
        tried = 0
        for i, j, k in combinations(range(nq), 3):
            gi, Wi, _ = solve_family(
                [quads[i], quads[j], quads[k]], pts, "t"
            )
            tried += 1
            if Wi == W and gi == g0:
                best = {
                    "size": 3,
                    "quads": [quads[i], quads[j], quads[k]],
                    "W": Wi,
                    "g0": gi,
                    "at": (i, j, k),
                    "tried": tried,
                }
                break
            if tried % 2000 == 0:
                print(f"  tried {tried} t={time.time()-t0:.1f}s", flush=True)

    out = {
        "w": w,
        "h": h,
        "n_quads": len(quads),
        "W_std": W,
        "g0_std": g0,
        "best": best,
        "seconds": round(time.time() - t0, 2),
        "quad_masks_note": "bitmask y*w+x",
    }
    p = OUTDIR / "round5_b201fu_subfam3_3x4.json"
    p.write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote {p}", flush=True)
    if best:
        # decode quads to coords
        decoded = []
        for m in best["quads"]:
            coords = []
            mm = m
            i = 0
            while mm:
                if mm & 1:
                    coords.append([i % w, i // w])
                mm >>= 1
                i += 1
            decoded.append(coords)
        best["decoded"] = decoded
        print("best decoded", decoded, flush=True)


if __name__ == "__main__":
    main()
