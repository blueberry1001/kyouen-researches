#!/usr/bin/env python3
"""Cycle 39c — fast widest A–B path on A0∪B0 (restricted hypergraph)."""
from __future__ import annotations

import heapq
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import NR, RES, forbidden_quads, load_n7, occupancy_vector, stones

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


def main() -> None:
    sets = load_n7()
    a_sets = [s for s in sets if (s >> 24) & 1]
    b_sets = [s for s in sets if not (s >> 24) & 1]
    best_pair = None
    for x in a_sets:
        for y in b_sets:
            d = (x ^ y).bit_count()
            if best_pair is None or d < best_pair[0]:
                best_pair = (d, x, y)
    d_stones, A0, B0 = best_pair
    quads = forbidden_quads(N)
    union = A0 | B0
    cells = stones(union, 49)
    idx = {p: i for i, p in enumerate(cells)}
    U = len(cells)
    A_idx = 0
    B_idx = 0
    for p in stones(A0, 49):
        A_idx |= 1 << idx[p]
    for p in stones(B0, 49):
        B_idx |= 1 << idx[p]

    union_quads = []
    for q in quads:
        if all(p in idx for p in q):
            qm = 0
            for p in q:
                qm |= 1 << idx[p]
            union_quads.append(qm)
    quads_by_cell = [[] for _ in range(U)]
    for qm in union_quads:
        w = qm
        while w:
            b = w & -w
            i = b.bit_length() - 1
            quads_by_cell[i].append(qm)
            w ^= b

    def add_ok(m: int, i: int) -> bool:
        nm = m | (1 << i)
        for qm in quads_by_cell[i]:
            if (nm & qm) == qm:
                return False
        return True

    def full_mask(im: int) -> int:
        m = 0
        w = im
        while w:
            b = w & -w
            m |= 1 << cells[b.bit_length() - 1]
            w ^= b
        return m

    # widest path Dijkstra
    best = {A_idx: bin(A_idx).count("1")}
    prev = {}
    pq = [(-best[A_idx], A_idx)]
    n_pops = 0
    while pq:
        negb, m = heapq.heappop(pq)
        b = -negb
        n_pops += 1
        if b < best.get(m, -1):
            continue
        if m == B_idx:
            break
        for i in range(U):
            bit = 1 << i
            if m & bit:
                nm = m & ~bit  # remove always safe if m safe
            else:
                if not add_ok(m, i):
                    continue
                nm = m | bit
            nsz = bin(nm).count("1")
            nb = min(b, nsz)
            if nb > best.get(nm, -1):
                best[nm] = nb
                prev[nm] = m
                heapq.heappush(pq, (-nb, nm))

    width = best.get(B_idx)
    bottlenecks = []
    for m, b in best.items():
        if width is not None and b >= width and bin(m).count("1") == width:
            fm = full_mask(m)
            ov = occupancy_vector(fm, N)
            bottlenecks.append(
                {
                    "occ": [ov.get(k, 0) for k in ORDER],
                    "uses_22": ov.get((2, 2), 0) > 0,
                    "uses_center": ov.get((3, 3), 0) > 0,
                }
            )
    results = {
        "min_AB_symdiff_stones": d_stones,
        "union_cells": U,
        "n_union_quads": len(union_quads),
        "restricted_widest_width": width,
        "n_states": len(best),
        "n_pops": n_pops,
        "n_bottlenecks": len(bottlenecks),
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
        "bottleneck_sample": bottlenecks[:15],
    }
    outp = RES / "cycle39c_widest_path_fast.json"
    outp.write_text(json.dumps(results, indent=2), encoding="utf-8")
    lines = [
        "# Cycle 39c — widest A–B path on A0∪B0 (fast restricted)",
        "",
        f"- |A∪B| = {U}; quads inside union = {len(union_quads)}",
        f"- **restricted widest width = {width}** (COMPLETE on union graph)",
        f"- bottleneck states: {len(bottlenecks)}",
        f"- uses (2,2) rate: {results['bottleneck_uses_22_rate']}",
        f"- uses center rate: {results['bottleneck_uses_center_rate']}",
        "",
        "| bottleneck occ | (2,2) | center |",
        "|---|---|---|",
    ]
    for x in bottlenecks[:12]:
        lines.append(f"| {x['occ']} | {x['uses_22']} | {x['uses_center']} |")
    lines += ["", f"Artifact: `{outp.name}`"]
    md = NR / "CYCLE39C_WIDEST_PATH_FAST.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2)[:2500])
    print("Wrote", outp, md)


if __name__ == "__main__":
    main()
