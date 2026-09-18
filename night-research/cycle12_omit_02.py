#!/usr/bin/env python3
"""Occupancy of n=7 safe sets at max size when (0,2) orbit is forbidden.

COMPLETE count@12 was 3464 (cycle8_b_maxsafe max --forbid-orbit 0,2).
This script enumerates a SAMPLE of those 12-sets via target DFS and reports
occupancy, to see what replaces the missing (0,2) stones.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import RES, occupancy_vector  # noqa: E402

# rebuild members
N = 7
mem = {}
def ck(x, y):
    return min({(x, y), (N - 1 - x, y), (x, N - 1 - y), (N - 1 - x, N - 1 - y),
                (y, x), (N - 1 - y, x), (y, N - 1 - x), (N - 1 - y, N - 1 - x)})
for y in range(N):
    for x in range(N):
        mem.setdefault(ck(x, y), []).append(y * N + x)


def build_triples(n: int):
    from cycle8_lib import det4
    v = n * n
    rows = [[x * x + y * y, x, y, 1] for y in range(n) for x in range(n)]
    triples = [[] for _ in range(v)]
    for a in range(v - 3):
        for b in range(a + 1, v - 2):
            for c in range(b + 1, v - 1):
                for d in range(c + 1, v):
                    if det4([rows[a], rows[b], rows[c], rows[d]]) != 0:
                        continue
                    q = (1 << a) | (1 << b) | (1 << c) | (1 << d)
                    for t in (a, b, c, d):
                        triples[t].append(q & ~(1 << t))
    return triples


def enum_k(triples, target, forbid_mask, max_sets=80, node_budget=3_000_000):
    v = 49
    all_cells = ((1 << v) - 1) & ~forbid_mask
    found = []
    nodes = 0

    def dfs(cand, count, mask, cc):
        nonlocal nodes
        if len(found) >= max_sets or nodes > node_budget:
            return
        nodes += 1
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
                wmask = o & ~mask & all_cells
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
        if len(found) >= max_sets:
            return
        dfs(cand & ~(1 << u), count, mask, cc)

    dfs(all_cells, 0, 0, [0] * v)
    return found, nodes


def main():
    triples = build_triples(7)
    forbid = 0
    for p in mem[(0, 2)]:
        forbid |= 1 << p
    sets, nodes = enum_k(triples, 12, forbid, max_sets=60, node_budget=4_000_000)
    print(f"sampled {len(sets)} size-12 sets with (0,2) forbidden, nodes={nodes}")
    keys = sorted(mem)
    occ_hist = Counter()
    uses22 = usesC = 0
    for s in sets:
        ov = occupancy_vector(s, 7)
        assert ov[(0, 2)] == 0
        occ_hist[tuple(ov[k] for k in keys)] += 1
        if ov[(2, 2)]:
            uses22 += 1
        if ov[(3, 3)]:
            usesC += 1
    out = {
        "package": "Cycle12-omit-0,2",
        "evidence": "SAMPLE size-12 safe sets under forbid orbit (0,2); COMPLETE max=12 inherited",
        "n_samples": len(sets),
        "nodes": nodes,
        "distinct_occupancy": len(occ_hist),
        "uses_22": uses22,
        "uses_center": usesC,
        "top_occupancy": [
            {"vec": list(v), "count": c} for v, c in occ_hist.most_common(8)
        ],
        "keys": list(keys),
    }
    Path(RES / "cycle12_omit_02_sample.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2)[:2000])


if __name__ == "__main__":
    main()
