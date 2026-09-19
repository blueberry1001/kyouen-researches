#!/usr/bin/env python3
"""Cycle 39b — widest A–B path on union A0∪B0 (COMPLETE on 19 cells).

Widest path: maximize the minimum safe-set size along single-stone edits.
"""
from __future__ import annotations

import heapq
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import (
    NR,
    RES,
    board_str,
    forbidden_quads,
    is_safe,
    occupancy_vector,
    stones,
    triples_by_point,
)

N = 7
ORDER = [
    (0, 0),
    (0, 1),
    (0, 2),
    (0, 3),
    (1, 1),
    (1, 2),
    (1, 3),
    (2, 2),
    (2, 3),
    (3, 3),
]


def mask_from_board(rows: list[str]) -> int:
    m = 0
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in "X":
                m |= 1 << (y * N + x)
    return m


A0 = mask_from_board(
    ["XX...X.", ".XX....", ".....XX", "...X.X.", "X......", "...XX.X", "X......"]
)
B0 = mask_from_board(
    ["XX....X", "....XX.", ".X.X...", "X.Xc...", "......X", "..XX...", "..X...X"]
)


def main() -> None:
    quads = forbidden_quads(N)
    tbp, _ = triples_by_point(N, quads)
    union = A0 | B0
    cells = stones(union, 49)
    idx = {p: i for i, p in enumerate(cells)}
    U = len(cells)
    A_idx = sum(1 << idx[p] for p in stones(A0, 49))
    B_idx = sum(1 << idx[p] for p in stones(B0, 49))

    def full_mask(im: int) -> int:
        m = 0
        w = im
        while w:
            b = w & -b if False else w & -w
            i = b.bit_length() - 1
            m |= 1 << cells[i]
            w ^= b
        return m

    # safe cache for restricted masks
    safe_cache = {A_idx: True}

    def restricted_safe(im: int) -> bool:
        if im in safe_cache:
            return safe_cache[im]
        fm = full_mask(im)
        ok = is_safe(fm, quads)
        safe_cache[im] = ok
        return ok

    # Dijkstra widest
    INF_NEG = -1
    best = {A_idx: A_idx.bit_count()}
    prev = {}
    pq = [(-best[A_idx], A_idx)]
    while pq:
        negb, m = heapq.heappop(pq)
        b = -negb
        if b < best.get(m, INF_NEG):
            continue
        if m == B_idx:
            break
        for i in range(U):
            nm = m ^ (1 << i)
            if not restricted_safe(nm):
                continue
            nsz = nm.bit_count()
            nb = min(b, nsz)
            if nb > best.get(nm, INF_NEG):
                best[nm] = nb
                prev[nm] = m
                heapq.heappush(pq, (-nb, nm))

    width = best.get(B_idx, None)
    # reconstruct one path achieving width
    path = []
    if B_idx in best:
        cur = B_idx
        while cur != A_idx:
            path.append(cur)
            cur = prev[cur]
        path.append(A_idx)
        path.reverse()

    # occupancy at minimum-size states along this path
    min_sz = None
    min_occ = None
    min_uses22 = None
    for im in path:
        fm = full_mask(im)
        sz = fm.bit_count()
        if min_sz is None or sz < min_sz:
            min_sz = sz
            ov = occupancy_vector(fm, N)
            min_occ = [ov.get(k, 0) for k in ORDER]
            min_uses22 = ov.get((2, 2), 0) > 0

    # all bottlenecks: states with size == width that appear on some widest path
    # (states m with best[m] >= width and size(m) == width reachable)
    bottlenecks = []
    for m, b in best.items():
        if b >= width and m.bit_count() == width:
            fm = full_mask(m)
            ov = occupancy_vector(fm, N)
            bottlenecks.append(
                {
                    "hex": hex(fm),
                    "occ": [ov.get(k, 0) for k in ORDER],
                    "uses_22": ov.get((2, 2), 0) > 0,
                    "uses_center": ov.get((3, 3), 0) > 0,
                }
            )

    results = {
        "union_cells": U,
        "restricted_widest_width": width,
        "path_len_states": len(path),
        "path_min_size": min_sz,
        "path_min_occ": min_occ,
        "path_min_uses_22": min_uses22,
        "n_states_visited": len(best),
        "n_bottleneck_states": len(bottlenecks),
        "bottleneck_sample": bottlenecks[:12],
        "bottleneck_uses_22_rate": (
            sum(1 for x in bottlenecks if x["uses_22"]) / len(bottlenecks)
            if bottlenecks
            else None
        ),
        "bottleneck_uses_center_rate": (
            sum(1 for x in bottlenecks if x["uses_center"]) / len(bottlenecks)
            if bottlenecks
            else None
        ),
    }
    outp = RES / "cycle39b_widest_path.json"
    outp.write_text(json.dumps(results, indent=2), encoding="utf-8")
    lines = [
        "# Cycle 39b — widest A–B path on A0∪B0 (COMPLETE restricted)",
        "",
        f"- union cells: {U} (2^{U} subsets; Dijkstra widest on safe ones)",
        f"- **restricted widest width = {width}** (prior COMPLETE: restricted path width ≤11; this recomputes the max-min)",
        f"- bottleneck states at width: {results['n_bottleneck_states']}",
        f"- fraction of bottlenecks using (2,2): {results['bottleneck_uses_22_rate']}",
        f"- fraction using center: {results['bottleneck_uses_center_rate']}",
        "",
        "Sample bottleneck occupancies:",
        "",
        "| occ (00..33) | uses (2,2) | uses center |",
        "|---|---|---|",
    ]
    for x in bottlenecks[:10]:
        lines.append(f"| {x['occ']} | {x['uses_22']} | {x['uses_center']} |")
    lines += ["", f"Artifact: `{outp.name}`"]
    md = NR / "CYCLE39B_WIDEST_PATH.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2)[:2000])
    print("Wrote", outp, md)


if __name__ == "__main__":
    main()
