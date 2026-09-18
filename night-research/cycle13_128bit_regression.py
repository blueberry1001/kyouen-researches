#!/usr/bin/env python3
"""Cycle 13 — 128-bit mask prototype + n=7/n=6 regression counts.

Implements Mask128 ops and a target-existence DFS using 128-bit style
storage (still fine in Python ints) to re-count known values:
  n=7 K=14 → 16
  n=6 K=11 → 464
This is the regression gate required before any K9 UNSAT design work.
No n=9 search is run.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import RES, det4  # noqa: E402


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


def count_exact_k(triples, n, target, node_budget=50_000_000):
    v = n * n
    all_cells = (1 << v) - 1
    found = 0
    nodes = 0

    def dfs(cand, count, mask, cc):
        nonlocal nodes, found
        nodes += 1
        if nodes > node_budget:
            return
        need = target - count
        if need == 0:
            found += 1
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


def main():
    results = []
    for n, K, expect in [(7, 14, 16), (6, 11, 464)]:
        t0 = time.time()
        triples, nq = build_triples(n)
        cnt, nodes = count_exact_k(triples, n, K)
        ok = cnt == expect
        row = {
            "n": n,
            "K": K,
            "quads": nq,
            "count": cnt,
            "expected": expect,
            "pass": ok,
            "nodes": nodes,
            "seconds": round(time.time() - t0, 2),
            "note": "regression for future 128-bit solver; not a new proof of K",
        }
        print(row, flush=True)
        results.append(row)
    out = {
        "package": "Cycle13-128bit-regression",
        "evidence": "COMPLETE recount of known max-set counts via 128-bit-capable DFS (Python int)",
        "results": results,
        "k9": "not attempted; design only in CYCLE9H_K9_128BIT_DESIGN.md",
        "all_pass": all(r["pass"] for r in results),
    }
    Path(RES / "cycle13_128bit_regression.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("Wrote", RES / "cycle13_128bit_regression.json")
    if not out["all_pass"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
