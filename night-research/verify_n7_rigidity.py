#!/usr/bin/env python3
"""Independent verification of the n=7 K=14 rigidity result.

For every one of the 16 maximal safe sets S:
  - verify S is safe (no forbidden quad inside)
  - verify S is maximal (every empty point has >= 1 blocker triple)
  - verify NO single-stone swap exists: for every empty v and every r in S,
    S - r + v must be unsafe
  - compute tau_S(v) exactly (min hitting set of blocker triples) by brute
    force and confirm the reported tau histogram and rho = min tau.

This is an independent re-derivation of the key claim
  forall S in M_7: rho(S) >= 2  (indeed = 2),
i.e. the 1-swap graph on 7x7 maximal sets has no edges.
"""

import struct
from itertools import combinations
from pathlib import Path

N = 7
V = N * N
ROOT = Path(__file__).resolve().parents[1]


def det4(p0, p1, p2, p3):
    rows = [p0, p1, p2, p3]

    def minor3(r, cols):
        m = [[rows[i][c] for c in cols] for i in r]
        return (
            m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
        )

    det = 0
    for c0 in range(4):
        sign = 1 if c0 % 2 == 0 else -1
        cols = [c for c in range(4) if c != c0]
        det += sign * rows[0][c0] * minor3([1, 2, 3], cols)
    return det


rows = [(x * x + y * y, x, y, 1) for y in range(N) for x in range(N)]
quads = []
quads_by_pt = [[] for _ in range(V)]
for ids in combinations(range(V), 4):
    if det4(*[rows[i] for i in ids]) == 0:
        quads.append(ids)
        for i in ids:
            quads_by_pt[i].append(ids)
print(f"forbidden quads: {len(quads)}")

data = (ROOT / "night-research" / "maxsafe_n7_K14.bin").read_bytes()
sets = [struct.unpack_from("<Q", data, i)[0] for i in range(0, len(data), 8)]
print(f"maximal sets loaded: {len(sets)}")

total_swaps = 0
rho_hist = {}
tau_reported = {}

for si, S in enumerate(sets):
    stones = [i for i in range(V) if (S >> i) & 1]
    # safety
    bad = sum(1 for q in quads if all((S >> i) & 1 for i in q))
    assert bad == 0, f"set {si} not safe"
    empties = [v for v in range(V) if not ((S >> v) & 1)]
    assert len(stones) == 14 and len(empties) == 35
    taus = []
    for v in empties:
        blockers = [frozenset(q) - {v} for q in quads_by_pt[v]
                    if all((S >> i) & 1 for i in q if i != v) and v in q]
        # keep only quads whose other three points are all in S
        blockers = [frozenset(q) - {v} for q in quads_by_pt[v]
                    if (frozenset(q) - {v}) <= set(stones)]
        assert blockers, f"set {si} not maximal at empty {v}"
        # brute-force minimal hitting set size
        tau = None
        for size in range(1, 5):
            found = False
            for comb in combinations(stones, size):
                cs = set(comb)
                if all(cs & b for b in blockers):
                    found = True
                    break
            if found:
                tau = size
                break
        taus.append(tau)
        # explicit swap test: is S - r + v safe for any r?
        for r in stones:
            S2 = (S & ~(1 << r)) | (1 << v)
            if all(not all((S2 >> i) & 1 for i in q) for q in quads):
                total_swaps += 1
    rho = min(taus)
    rho_hist[rho] = rho_hist.get(rho, 0) + 1
    hist = {}
    for t in taus:
        hist[t] = hist.get(t, 0) + 1
    tau_reported[si] = hist

print()
print("rho distribution (independent brute force):", rho_hist)
print("total single-stone swaps found:", total_swaps)
print()
print("tau histograms per set:")
for si in sorted(tau_reported):
    print(f"  set {si}: {dict(sorted(tau_reported[si].items()))}")
print()
print("VERDICT:",
      "A - all n=7 maximal sets are 1-swap rigid (rho>=2), no swap edges"
      if total_swaps == 0 and min(rho_hist) >= 2 else
      "B - some n=7 maximal set admits a single-stone swap")
