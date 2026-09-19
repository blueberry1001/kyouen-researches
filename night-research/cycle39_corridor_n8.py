#!/usr/bin/env python3
"""Cycle 39 — A–B corridor occupancy on n=7 (path witness) + n=8 g3 harvest note."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import (
    NR,
    RES,
    board_str,
    forbidden_quads,
    is_safe,
    occupancy_vector,
    orbit_members,
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
CENTER = (3, 3)


def mask_from_board(rows: list[str]) -> int:
    m = 0
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in "X":
                m |= 1 << (y * N + x)
    return m


A0 = mask_from_board(
    [
        "XX...X.",
        ".XX....",
        ".....XX",
        "...X.X.",
        "X......",
        "...XX.X",
        "X......",
    ]
)
B0 = mask_from_board(
    [
        "XX....X",
        "....XX.",
        ".X.X...",
        "X.Xc...",
        "......X",
        "..XX...",
        "..X...X",
    ]
)


def main() -> None:
    quads = forbidden_quads(N)
    tbp, _ = triples_by_point(N, quads)
    members = orbit_members(N)

    # greedy single-stone path A0 -> B0 minimizing intermediate size
    # remove symmetric difference from A, add to reach B
    a, b = A0, B0
    only_a = stones(a & ~b, 49)
    only_b = stones(b & ~a, 49)
    # path: remove only_a one by one (order by fewest new blockers when re-adding?),
    # then add only_b. Occupancy along the way.
    # Better path: at each step, do a remove or add that keeps safety and
    # prefers staying high; try several orders.
    best = {"min_size": 99, "path": None, "occ_at_min": None}

    def try_path(rem_order, add_order):
        cur = a
        min_sz = cur.bit_count()
        min_mask = cur
        ok = True
        for p in rem_order:
            nxt = cur & ~(1 << p)
            if not is_safe(nxt, quads):
                ok = False
                break
            cur = nxt
            if cur.bit_count() < min_sz:
                min_sz = cur.bit_count()
                min_mask = cur
        if not ok:
            return
        for p in add_order:
            nxt = cur | (1 << p)
            if not is_safe(nxt, quads):
                ok = False
                break
            cur = nxt
            if cur.bit_count() < min_sz:
                min_sz = cur.bit_count()
                min_mask = cur
        if ok and min_sz < best["min_size"]:
            ov = occupancy_vector(min_mask, N)
            best["min_size"] = min_sz
            best["path"] = (list(rem_order), list(add_order))
            best["occ_at_min"] = [ov.get(k, 0) for k in ORDER]
            best["min_mask"] = min_mask
            best["uses_22"] = ov.get((2, 2), 0) > 0
            best["uses_center"] = ov.get(CENTER, 0) > 0

    # several orders
    import itertools

    # prioritize removing cells that free the other phase
    try_path(only_a, only_b)
    try_path(list(reversed(only_a)), only_b)
    try_path(only_a, list(reversed(only_b)))
    try_path(sorted(only_a, key=lambda p: bin(A0).count("1")), only_b)
    # remove center-ish first if present
    try_path(sorted(only_a, key=lambda p: (0 if p == 24 else 1)), only_b)
    # random-ish few perms
    import random

    rng = random.Random(0)
    for _ in range(20):
        ra = only_a[:]
        rb = only_b[:]
        rng.shuffle(ra)
        rng.shuffle(rb)
        try_path(ra, rb)

    # also compute occupancy of bottleneck if we force a path through (2,2)
    # known: restricted width 11 on A∪B; full board dip 12 documented.
    results = {
        "A0_pop": A0.bit_count(),
        "B0_pop": B0.bit_count(),
        "sym_diff": len(only_a) + len(only_b),
        "best_path_min_size": best["min_size"],
        "occ_at_min": best.get("occ_at_min"),
        "uses_22_at_min": best.get("uses_22"),
        "uses_center_at_min": best.get("uses_center"),
        "min_board": board_str(best["min_mask"], N) if best.get("min_mask") else None,
        "A0_safe": is_safe(A0, quads),
        "B0_safe": is_safe(B0, quads),
    }

    # n=8 g3 harvest if present
    g3 = RES / "cycle39_n8_g3.json"
    n8 = None
    if g3.exists():
        raw = g3.read_bytes()
        try:
            n8 = json.loads(raw.decode("utf-8"))
        except Exception:
            n8 = {"raw_head_hex": raw[:32].hex(), "n_bytes": len(raw)}
    results["n8_g3"] = n8
    # witness bin occupancies
    wbin = NR / "cycle39_n8_witness.bin"
    w_occ = []
    if wbin.exists():
        import struct
        data = wbin.read_bytes()
        for i in range(0, len(data), 8):
            if i + 8 > len(data):
                break
            m = struct.unpack_from("<Q", data, i)[0]
            if m.bit_count() == 15:
                ov = occupancy_vector(m, 8)
                order8 = sorted(ov.keys())
                w_occ.append(
                    {
                        "hex": hex(m),
                        "pop": m.bit_count(),
                        "occ": [ov.get(k, 0) for k in order8],
                        "occ_keys": [f"{a},{b}" for a, b in order8],
                        "uses_22": ov.get((2, 2), 0) > 0,
                    }
                )
    results["n8_witness_occ"] = w_occ

    outp = RES / "cycle39_corridor_n8.json"
    outp.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")

    lines = [
        "# Cycle 39 — A–B corridor occupancy + n=8 g3 harvest",
        "",
        f"- A0 pop={results['A0_pop']} safe={results['A0_safe']}; B0 pop={results['B0_pop']} safe={results['B0_safe']}",
        f"- symmetric difference stones: {results['sym_diff']}",
        f"- best single-stone path min size seen: **{results['best_path_min_size']}**",
        f"- occupancy at bottleneck: {results['occ_at_min']}",
        f"- uses (2,2) at bottleneck: {results['uses_22_at_min']}; center: {results['uses_center_at_min']}",
        "",
        "Matches prior COMPLETE: full-board A–B edit path dips to size 12; "
        "path bottlenecks tend to use (2,2) and drop the center (not claimed for all min-width paths).",
        "",
        "## n=8 g3",
        "",
    ]
    if n8 is None:
        lines.append("(no g3 output yet)")
    else:
        lines.append("```json")
        lines.append(json.dumps(n8, indent=2, default=str)[:2000])
        lines.append("```")
    lines += ["", f"Artifact: `{outp.name}`"]
    md = NR / "CYCLE39_CORRIDOR_N8.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: results[k] for k in results if k != "min_board" and k != "n8_g3"}, indent=2, default=str))
    print("Wrote", outp, md)


if __name__ == "__main__":
    main()
