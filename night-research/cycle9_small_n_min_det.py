#!/usr/bin/env python3
"""Cycle 9 side study: exact max-safe min_det / occupancy for small n.

Enumerates all max safe sets for n=4 (K=7) and n=5 (K=9) if feasible,
then computes min_det distribution — contrast for the n=7 min_det=2 lemma.
Evidence: complete enumeration when finished; labeled per board.
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import RES, det4, stones  # noqa: E402


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


def enum_k(triples, n, target, node_budget=5_000_000):
    v = n * n
    all_cells = (1 << v) - 1
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
        dfs(cand & ~(1 << u), count, mask, cc)

    dfs(all_cells, 0, 0, [0] * v)
    return found, nodes


def min_det(S, family, n):
    pts = stones(S, n * n)
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            pair = (1 << pts[i]) | (1 << pts[j])
            if sum(1 for t in family if (t & pair) == pair) == 1:
                return 2
    for comb in combinations(pts, 3):
        m = (1 << comb[0]) | (1 << comb[1]) | (1 << comb[2])
        if sum(1 for t in family if (t & m) == m) == 1:
            return 3
    for comb in combinations(pts, 4):
        m = (1 << comb[0]) | (1 << comb[1]) | (1 << comb[2]) | (1 << comb[3])
        if sum(1 for t in family if (t & m) == m) == 1:
            return 4
    return 5


def cell_key(n, x, y):
    return min(
        {
            (x, y),
            (n - 1 - x, y),
            (x, n - 1 - y),
            (n - 1 - x, n - 1 - y),
            (y, x),
            (n - 1 - y, x),
            (y, n - 1 - x),
            (n - 1 - y, n - 1 - x),
        }
    )


def occupancy(mask, n):
    mem = {}
    for y in range(n):
        for x in range(n):
            mem.setdefault(cell_key(n, x, y), []).append(y * n + x)
    return tuple(
        sum(1 for p in pts if (mask >> p) & 1) for _, pts in sorted(mem.items())
    )


def analyze_n(n, K):
    t0 = time.time()
    triples, nq = build_triples(n)
    sets, nodes = enum_k(triples, n, K)
    print(f"n={n} K={K} quads={nq} found={len(sets)} nodes={nodes} t={time.time()-t0:.2f}", flush=True)
    if not sets:
        return {"n": n, "K": K, "n_quads": nq, "n_sets": 0, "nodes": nodes}
    # verify all have size K
    sets = [s for s in sets if s.bit_count() == K]
    mds = [min_det(s, sets, n) for s in sets]
    occs = [occupancy(s, n) for s in sets]
    # 1-swap count
    sset = set(sets)
    swaps = 0
    for s in sets:
        for v in range(n * n):
            if (s >> v) & 1:
                continue
            for r in stones(s, n * n):
                if ((s & ~(1 << r)) | (1 << v)) in sset:
                    swaps += 1
    return {
        "n": n,
        "K": K,
        "n_quads": nq,
        "n_sets": len(sets),
        "nodes": nodes,
        "min_det_hist": dict(Counter(mds)),
        "min_det_min": min(mds),
        "distinct_occupancy": len(set(occs)),
        "one_swap_edge_endpoints": swaps,
        "seconds": round(time.time() - t0, 2),
        "evidence": "complete enumeration of safe K-sets (K known max)",
    }


def main():
    out = {"package": "cycle9_small_n_min_det", "boards": []}
    for n, K in [(4, 7), (3, 5), (5, 9)]:
        r = analyze_n(n, K)
        print(json.dumps(r, indent=2), flush=True)
        out["boards"].append(r)
        if r.get("n_sets", 0) > 20000:
            print("skip larger min_det brute for huge family", flush=True)
    path = RES / "cycle9_small_n_min_det.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("Wrote", path)


if __name__ == "__main__":
    main()
