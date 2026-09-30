#!/usr/bin/env python3
# Mechanical D4 coverage check for 11x11 one-stone first moves.
# Verifies the 21 representatives cover all 121 cells exactly.
import itertools

N = 11
V = N * N

def d4_orbits():
    """Return the 8 D4 images of a point index."""
    def pt(v):
        return (v % N, v // N)
    def idx(x, y):
        return y * N + x
    def images(v):
        x, y = pt(v)
        s = set()
        for (a, b) in [(x, y), (y, x), (N - 1 - x, y), (y, N - 1 - x),
                       (x, N - 1 - y), (N - 1 - y, x),
                       (N - 1 - x, N - 1 - y), (N - 1 - y, N - 1 - x)]:
            s.add(idx(a, b))
        return s
    return images

def main():
    images = d4_orbits()
    reps = [60, 0, 1, 12, 2, 13, 24, 3, 14, 25, 36, 4, 15, 26,
            37, 48, 5, 16, 27, 38, 49]
    covered = {}
    sizes = {}
    for r in reps:
        orb = images(r)
        sizes[r] = len(orb)
        for v in orb:
            covered[v] = r
    # 1. sizes match the documented table
    doc = {60: 1, 0: 4, 1: 8, 12: 4, 2: 8, 13: 8, 24: 4, 3: 8,
           14: 8, 25: 8, 36: 4, 4: 8, 15: 8, 26: 8, 37: 8, 48: 4,
           5: 4, 16: 4, 27: 4, 38: 4, 49: 4}
    bad = [r for r in reps if sizes[r] != doc[r]]
    print("size mismatches:", bad if bad else "none")
    # 2. coverage is exact: every cell covered exactly once
    print("cells covered:", len(covered), "/", V)
    missing = [v for v in range(V) if v not in covered]
    dup = {}
    for r in reps:
        for v in images(r):
            dup.setdefault(v, []).append(r)
    multi = {v: rs for v, rs in dup.items() if len(rs) > 1}
    print("uncovered cells:", missing if missing else "none")
    print("cells covered by >1 rep:",
          dict(list(multi.items())[:5]) if multi else "none")
    # 3. orbit-size histogram
    hist = {}
    for r in reps:
        hist[sizes[r]] = hist.get(sizes[r], 0) + 1
    print("orbit-size histogram:", hist)
    total = sum(k * v for k, v in hist.items())
    print("total cells:", total, "(must be 121)")
    assert not bad and not missing and not multi and total == V
    print("COVER_OK")

main()
