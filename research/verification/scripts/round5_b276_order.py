#!/usr/bin/env python3
"""B276 / B279 / B273-B274 supporting computations.

B276: order parameter for D4 symmetry breaking under high-lambda Gibbs.
  Compute distribution of an asymmetry statistic over maximal / near-maximal
  configs on n=5 (100 maximal) and n=6 (sample of maximal if available).

B279: match E[|S|] between n=4 and n=4-hole, compare spectral gaps.

B273/B274: look for two-phase structure in near-maximal level of n=5/6
  (clustering of maximal configs by fingerprint).
"""
import json
from pathlib import Path
from collections import defaultdict, Counter
from itertools import combinations

import numpy as np

OUT = Path(r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round5_b276_order.json")


def det4(rows):
    a = [[int(rows[i][j]) for j in range(4)] for i in range(4)]
    total = 0
    for i in range(4):
        mm = [[a[r2][c2] for c2 in range(1, 4)] for r2 in range(4) if r2 != i]
        d3 = (mm[0][0] * (mm[1][1] * mm[2][2] - mm[1][2] * mm[2][1])
              - mm[0][1] * (mm[1][0] * mm[2][2] - mm[1][2] * mm[2][0])
              + mm[0][2] * (mm[1][0] * mm[2][1] - mm[1][1] * mm[2][0]))
        total += (1 if i % 2 == 0 else -1) * a[i][0] * d3
    return total


def build_quads(n):
    V = n * n
    pts = [(x, y) for y in range(n) for x in range(n)]
    rows = [(x * x + y * y, x, y, 1) for (x, y) in pts]
    triples = [[] for _ in range(V)]
    quads = []
    for a, b, c, d in combinations(range(V), 4):
        if det4([rows[a], rows[b], rows[c], rows[d]]) == 0:
            q = (a, b, c, d)
            quads.append(q)
            for t in q:
                triples[t].append(tuple(x for x in q if x != t))
    return V, pts, triples, quads


def safe(mask, triples, p):
    for t in triples[p]:
        if all(x in mask for x in t):
            return False
    return True


def enumerate_safe(n):
    V, pts, triples, quads = build_quads(n)
    from collections import deque
    start = frozenset()
    seen = {start}
    q = deque([start])
    while q:
        s = q.popleft()
        for p in range(V):
            if p in s:
                continue
            if safe(s, triples, p):
                ns = frozenset(s | {p})
                if ns not in seen:
                    seen.add(ns)
                    q.append(ns)
    return seen, V, pts, triples, quads


def d4_orbit(pts_set, n):
    """Return canonical min tuple under D4."""
    def transform(s, op):
        out = set()
        for p in s:
            x, y = p % n, p // n
            if op == 0:
                nx, ny = x, y
            elif op == 1:
                nx, ny = n - 1 - x, y
            elif op == 2:
                nx, ny = x, n - 1 - y
            elif op == 3:
                nx, ny = n - 1 - x, n - 1 - y
            elif op == 4:
                nx, ny = y, x
            elif op == 5:
                nx, ny = n - 1 - y, x
            elif op == 6:
                nx, ny = y, n - 1 - x
            elif op == 7:
                nx, ny = n - 1 - y, n - 1 - x
            out.add(ny * n + nx)
        return frozenset(out)
    cands = [transform(pts_set, op) for op in range(8)]
    return min(tuple(sorted(c)) for c in cands)


def asymmetry(s, n):
    """Order parameter: max over D4 of |s Δ g(s)| / |s| — 0 iff D4-invariant."""
    if not s:
        return 0.0
    best = 0
    for op in range(8):
        # count how many points move
        moved = 0
        for p in s:
            x, y = p % n, p // n
            if op == 0:
                nx, ny = x, y
            elif op == 1:
                nx, ny = n - 1 - x, y
            elif op == 2:
                nx, ny = x, n - 1 - y
            elif op == 3:
                nx, ny = n - 1 - x, n - 1 - y
            elif op == 4:
                nx, ny = y, x
            elif op == 5:
                nx, ny = n - 1 - y, x
            elif op == 6:
                nx, ny = y, n - 1 - x
            elif op == 7:
                nx, ny = n - 1 - y, n - 1 - x
            if ny * n + nx not in s:
                moved += 1
        best = max(best, moved)
    return best / len(s)


def main():
    out = {}

    # --- B279: E[|S|] matching and gap comparison ---
    # reuse thermo from levels
    # n=4 levels from known
    lev4 = [1, 16, 120, 560, 1626, 2360, 1064, 64]
    # n=4 hole: enumerate
    print("enum n=4 hole for B279 ...")
    # quick: reuse mixing json gaps + compute E|S| from enumerate
    states4, V4, pts4, tri4, q4 = enumerate_safe(4)
    states4h, V4h, pts4h, tri4h, q4h = enumerate_safe(4)  # will redo hole below

    def level_of(states):
        c = Counter(len(s) for s in states)
        return [c.get(k, 0) for k in range(max(c) + 1)]

    def E_k(level, lam):
        Z = 0
        s1 = 0
        pl = 1.0
        for k, a in enumerate(level):
            Z += a * pl
            s1 += k * a * pl
            pl *= lam
        return s1 / Z if Z else 0.0

    lev4_real = level_of(states4)
    out["n4_levels"] = lev4_real

    # hole: remove point id of (1,1) = 1*4+1 = 5 (not center 10). use 10 = (2,2)
    def enumerate_hole(n, hole):
        V, pts, triples, quads = build_quads(n)
        from collections import deque
        start = frozenset()
        seen = {start}
        q = deque([start])
        while q:
            s = q.popleft()
            for p in range(V):
                if p == hole or p in s:
                    continue
                if safe(s, triples, p):
                    ns = frozenset(s | {p})
                    if ns not in seen:
                        seen.add(ns)
                        q.append(ns)
        return seen

    states4h = enumerate_hole(4, 10)
    lev4h = level_of(states4h)
    out["n4hole_levels"] = lev4h
    out["n4hole_nstates"] = len(states4h)

    # gaps from previous mixing run
    mix = json.load(open(r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round5_b278_mixing.json"))
    n4_gaps = mix["B278_summary"]["n4_gaps"]
    n4h_gaps = mix["B278_summary"]["n4hole_gaps"]

    # find lam_h such that E_k matches E_k at some lam_n4
    b279 = []
    for lam4 in [1.0, 2.0, 3.0, 5.0, 8.0]:
        e4 = E_k(lev4_real, lam4)
        # binary search lam_h
        lo, hi = 0.1, 50.0
        for _ in range(40):
            mid = (lo + hi) / 2
            if E_k(lev4h, mid) < e4:
                lo = mid
            else:
                hi = mid
        lam_h = (lo + hi) / 2
        e_h = E_k(lev4h, lam_h)
        # nearest computed gaps (use lam4 for n4 and lam_h interpolate roughly)
        # use nearest in the computed list
        def nearest_gap(gaps, lam):
            keys = [float(k) for k in gaps]
            best = min(keys, key=lambda x: abs(x - lam))
            return gaps[str(int(best)) if str(int(best)) in gaps else str(best)]
        g4 = nearest_gap(n4_gaps, lam4)
        gh = nearest_gap(n4h_gaps, lam_h)
        b279.append({
            "lam4": lam4, "E4": e4, "lam_h": lam_h, "E_h": e_h,
            "gap4": g4, "gap_h": gh,
            "gap_ratio": (g4 / gh) if gh else None,
        })
    out["B279_Ematched"] = b279

    # --- B276: asymmetry of maximal configs n=5 ---
    print("B276 n=5 maximal asymmetry ...")
    states5, V5, pts5, tri5, q5 = enumerate_safe(5)
    K5 = max(len(s) for s in states5)
    maximal = [s for s in states5 if all(not safe(s, tri5, p) for p in range(V5) if p not in s)]
    out["n5_K"] = K5
    out["n5_nstates"] = len(states5)
    out["n5_nmaximal"] = len(maximal)
    asym = [asymmetry(s, 5) for s in maximal]
    out["B276_n5_asym_hist"] = dict(Counter(round(a, 3) for a in asym))
    out["B276_n5_asym_mean"] = float(np.mean(asym))
    out["B276_n5_asym_min"] = float(min(asym))
    out["B276_n5_asym_max"] = float(max(asym))
    # D4 orbit count of maximal
    orbits = {}
    for s in maximal:
        c = d4_orbit(s, 5)
        orbits[c] = orbits.get(c, 0) + 1
    out["n5_maximal_d4_orbits"] = len(orbits)
    out["n5_orbit_sizes"] = sorted(orbits.values(), reverse=True)[:20]

    # near-maximal (K-1)
    near = [s for s in states5 if len(s) == K5 - 1]
    asym_n = [asymmetry(s, 5) for s in near]
    out["B276_n5_near_asym_mean"] = float(np.mean(asym_n)) if asym_n else None
    out["B276_n5_near_n"] = len(near)

    # --- B273/B274: two-phase structure in near-maximal ---
    # cluster maximal configs by "row occupancy profile"
    def profile(s, n):
        rows = [0] * n
        cols = [0] * n
        for p in s:
            rows[p // n] += 1
            cols[p % n] += 1
        return tuple(sorted(rows)), tuple(sorted(cols))

    profs = Counter(profile(s, 5) for s in maximal)
    out["n5_maximal_profile_classes"] = len(profs)
    out["n5_maximal_profile_top"] = profs.most_common(10)

    OUT.write_text(json.dumps(out, indent=2, default=str))
    print("WROTE", OUT)
    for k in ["B276_n5_asym_mean", "B276_n5_asym_min", "B276_n5_nmaximal",
              "n5_maximal_d4_orbits", "n5_maximal_profile_classes", "B279_Ematched"]:
        print(k, out.get(k))


if __name__ == "__main__":
    main()
