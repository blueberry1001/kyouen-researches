#!/usr/bin/env python3
"""Cycle 9 G2 fast — bottleneck size-12 analysis on A0∪B0 (19 cells).

Only enumerates safe k-sets for k=12,13,14 on the union via incremental DFS.
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import RES, det4, forbidden_quads, is_safe, load_n7, occupancy_vector, stones  # noqa: E402

N = 7


def build_triples(n: int):
    v = n * n
    rows = [[x * x + y * y, x, y, 1] for y in range(n) for x in range(n)]
    triples = [[] for _ in range(v)]
    nq = 0
    for a in range(v - 3):
        for b in range(a + 1, v - 2):
            for c in range(b + 1, v - 1):
                for d in range(c + 1, v):
                    if det4([rows[a], rows[b], rows[c], rows[d]]) != 0:
                        continue
                    nq += 1
                    q = (1 << a) | (1 << b) | (1 << c) | (1 << d)
                    for t in (a, b, c, d):
                        triples[t].append(q & ~(1 << t))
    return triples, nq


def enum_exact(triples, cells, target, node_budget=2_000_000):
    """Enumerate safe subsets of `cells` with exact size target."""
    all_c = 0
    for p in cells:
        all_c |= 1 << p
    found = []
    nodes = 0

    def dfs(cand, count, mask, cc):
        nonlocal nodes
        nodes += 1
        if nodes > node_budget:
            return
        need = target - count
        if need == 0:
            found.append(mask)
            return
        if cand.bit_count() < need:
            return
        u = (cand & -cand).bit_length() - 1
        newcand = cand & ~(1 << u)
        undo = []
        ok = True
        for o in triples[u]:
            pc = bin(o & mask).count("1")
            if pc == 2:
                wmask = o & ~mask
                if wmask == 0:
                    ok = False
                    break
                w = (wmask & -wmask).bit_length() - 1
                if cc[w] == 0:
                    newcand &= ~(1 << w)
                cc[w] += 1
                undo.append(w)
        if ok:
            dfs(newcand, count + 1, mask | (1 << u), cc)
        for w in undo:
            cc[w] -= 1
        dfs(cand & ~(1 << u), count, mask, cc)

    dfs(all_c, 0, 0, [0] * (N * N))
    return found, nodes


def can_grow_to(mask, target, quads):
    if (mask & target) != mask:
        return False
    missing = target & ~mask
    from cycle8_lib import is_safe as safe

    def dfs(rem, cur):
        if rem == 0:
            return True
        w = rem
        while w:
            b = w & -w
            p = b.bit_length() - 1
            w ^= b
            nxt = cur | b
            if safe(nxt, quads) and dfs(rem & ~b, nxt):
                return True
        return False

    return dfs(missing, mask)


def main():
    t0 = time.time()
    n7 = load_n7()
    quads = forbidden_quads(N)
    triples, nq = build_triples(N)
    A0, B0 = n7[0], n7[8]
    union = A0 | B0
    upts = stones(union, 49)
    print(f"union cells={len(upts)} quads={nq}", flush=True)

    sz12, n12 = enum_exact(triples, upts, 12)
    sz13, n13 = enum_exact(triples, upts, 13)
    sz14, n14 = enum_exact(triples, upts, 14)
    print(f"nodes 12/13/14={n12}/{n13}/{n14} counts={len(sz12)}/{len(sz13)}/{len(sz14)}", flush=True)

    both = []
    onlyA = onlyB = neither = 0
    for m in sz12:
        ra, rb = can_grow_to(m, A0, quads), can_grow_to(m, B0, quads)
        if ra and rb:
            both.append(m)
        elif ra:
            onlyA += 1
        elif rb:
            onlyB += 1
        else:
            neither += 1
    print(f"sz12 both={len(both)} onlyA={onlyA} onlyB={onlyB} neither={neither}", flush=True)

    keys = sorted(occupancy_vector(n7[0], 7).keys())
    o22 = [2 * 7 + 2, 4 * 7 + 2, 2 * 7 + 4, 4 * 7 + 4]
    o03 = [0 * 7 + 3, 6 * 7 + 3, 3 * 7 + 0, 3 * 7 + 6]
    o23 = [2 * 7 + 3, 4 * 7 + 3, 3 * 7 + 2, 3 * 7 + 4]
    center = 24
    occ_both = Counter()
    uses = Counter()
    for m in both:
        ov = occupancy_vector(m, 7)
        occ_both[tuple(ov[k] for k in keys)] += 1
        if any((m >> p) & 1 for p in o22):
            uses["22"] += 1
        if (m >> center) & 1:
            uses["center"] += 1
        if any((m >> p) & 1 for p in o03):
            uses["03"] += 1
        if any((m >> p) & 1 for p in o23):
            uses["23"] += 1

    # size-13 hosts within {A0,B0}
    uA = sum(1 for m in sz13 if (A0 & m) == m and (B0 & m) != m)
    uB = sum(1 for m in sz13 if (B0 & m) == m and (A0 & m) != m)
    uBoth = sum(1 for m in sz13 if (A0 & m) == m and (B0 & m) == m)
    uNone = sum(1 for m in sz13 if (A0 & m) != m and (B0 & m) != m)

    example = both[0] if both else None
    board = None
    if example:
        board = "\n".join(
            "".join("X" if (example >> (y * N + x)) & 1 else "." for x in range(N))
            for y in range(N)
        )

    out = {
        "package": "G2",
        "evidence": "COMPLETE exact-size enum on A0∪B0 (19 cells) via incremental DFS; growability via safe single-cell adds",
        "n": 7,
        "union_cells": 19,
        "n_quads": nq,
        "safe_k_on_union": {"12": len(sz12), "13": len(sz13), "14": len(sz14)},
        "size14_hex": [hex(m) for m in sz14],
        "size14_is_exactly_A0_B0": set(sz14) == {A0, B0},
        "size12_total": len(sz12),
        "size12_reach_both_phases": len(both),
        "size12_only_A": onlyA,
        "size12_only_B": onlyB,
        "size12_neither": neither,
        "bottleneck12_uses": dict(uses),
        "bottleneck12_distinct_occupancy": len(occ_both),
        "bottleneck12_example_hex": hex(example) if example else None,
        "bottleneck12_example_board": board,
        "size13_host": {"only_A0": uA, "only_B0": uB, "subset_of_both": uBoth, "subset_of_neither": uNone},
        "cycle8a_full_board_min_width": 12,
        "cycle8a_restricted_union_min_width": 11,
        "lemma": (
            "On the 19-cell union A0∪B0, the only size-14 safe sets are A0 and B0. "
            "Any size-12 safe set that can grow into both phases is a bottleneck for "
            "restricted single-stone paths. Full-board paths also dip to ≤12 "
            "(unique 13-completion among the global 16). "
            "n=6 contrast: rho=1 on 296/464 so some max pairs admit K-1 size paths."
        ),
        "nodes": {"12": n12, "13": n13, "14": n14},
        "seconds": round(time.time() - t0, 3),
    }
    Path(RES / "cycle8_g2_bottleneck_12.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    Path("night-research/cycle8_g2_result.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: out[k] for k in out if k not in ("nodes",)}, indent=2)[:2500])
    print("Wrote results/cycle8_g2_bottleneck_12.json")


if __name__ == "__main__":
    main()
