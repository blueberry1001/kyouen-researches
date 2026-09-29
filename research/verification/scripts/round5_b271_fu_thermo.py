#!/usr/bin/env python3
"""Followup: B274 finer profile ratios, B277 Gibbs mass, B280 phase exclusion, B276 order param.

Reads existing s1 JSON where possible; recomputes multigraded profiles for n=4.

Writes round5_b271_fu_thermo.json
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from fractions import Fraction
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, is_forbidden_quad, square_points

OUT = Path(__file__).resolve().parents[1] / "round5_b271_fu_thermo.json"
S1 = Path(__file__).resolve().parents[1] / "round5_b271_s1.json"


def d4_orbit_of(n):
    def d4(x, y):
        cands = [
            (x, y), (y, n - 1 - x), (n - 1 - x, n - 1 - y), (n - 1 - y, x),
            (y, x), (x, n - 1 - y), (n - 1 - x, y), (n - 1 - y, n - 1 - x),
        ]
        return min(cands)
    V = n * n
    orbit_rep = {}
    orbit_of = [None] * V
    for y in range(n):
        for x in range(n):
            rep = d4(x, y)
            if rep not in orbit_rep:
                orbit_rep[rep] = len(orbit_rep)
            orbit_of[y * n + x] = orbit_rep[rep]
    return orbit_of, sorted(orbit_rep.keys())


def multigraded(n=4):
    pts = square_points(n)
    V = n * n
    b = Board(pts, name=f"{n}x{n}")
    orbit_of, reps = d4_orbit_of(n)
    n_orb = len(reps)
    hist = defaultdict(int)
    for occ in range(1 << V):
        ok = True
        for q in b.quads:
            if (occ & q) == q:
                ok = False
                break
        if not ok:
            continue
        k = occ.bit_count()
        cnt = [0] * n_orb
        for p in range(V):
            if (occ >> p) & 1:
                cnt[orbit_of[p]] += 1
        hist[(k, tuple(cnt))] += 1
    return hist, n_orb, reps


def main():
    s1 = json.loads(S1.read_text())
    result = {"s1_Z": s1["B271_B272"]["Z_coeffs"], "s1_levels": {"n4": s1["B275"]["n4"]["profile"], "n5": s1["B275"]["n5"]["profile"]}}

    print("multigraded n=4 ...", flush=True)
    hist, n_orb, reps = multigraded(4)
    # group by k
    by_k = defaultdict(list)
    for (k, cnt), v in hist.items():
        by_k[k].append((cnt, v))

    # B274: type A = s<0 (inner-rich), type B = s>0 (corner-rich)
    # orbits: 0=corner? need order. reps sorted -> (0,0) corner, (0,1) edge, (1,1) inner for n=4
    # n=4: corner rep (0,0) size 4, edge (0,1) size 8, inner (1,1) size 4
    # s = cnt[corner_orb] - cnt[inner_orb]
    # identify orbit index by rep
    corner_i = reps.index((0, 0)) if (0, 0) in reps else 0
    inner_i = reps.index((1, 1)) if (1, 1) in reps else len(reps) - 1
    print(f"  reps={reps} corner_i={corner_i} inner_i={inner_i}", flush=True)

    b274 = {}
    for k in sorted(by_k):
        A = B = eq = 0
        # finer: pair of specific profiles
        prof_counts = {}
        for cnt, v in by_k[k]:
            s = cnt[corner_i] - cnt[inner_i]
            if s < 0:
                A += v
            elif s > 0:
                B += v
            else:
                eq += v
            prof_counts[str(cnt)] = prof_counts.get(str(cnt), 0) + v
        # specific comparison (1,3,3) vs (3,3,1) in order (corner, edge, inner) — adjust to actual orbit order
        # We'll list all profiles
        b274[k] = {
            "A_s_neg": A,
            "B_s_pos": B,
            "eq_s0": eq,
            "A_over_B": (A / B) if B else None,
            "profiles": prof_counts,
        }

    # B277: Gibbs mass ratios
    levels = {4: [1, 16, 120, 560, 1626, 2360, 1064, 64], 5: [1, 25, 300, 2300, 11824, 37272, 59192, 35208, 5172, 100]}
    b277 = {}
    for n, lv in levels.items():
        K = max(i for i, v in enumerate(lv) if v > 0)
        mass = {}
        for lam in [0.25, 0.5, 1, 2, 4, 8, 16, 32, 64]:
            Z = sum(a * (lam ** k) for k, a in enumerate(lv))
            mK = lv[K] * (lam ** K) / Z
            mK1 = lv[K - 1] * (lam ** (K - 1)) / Z if K >= 1 else 0
            mK2 = lv[K - 2] * (lam ** (K - 2)) / Z if K >= 2 else 0
            mass[str(lam)] = {
                "mass_K": mK,
                "mass_Km1": mK1,
                "mass_Km2": mK2,
                "ratio_Km1_over_K": (mK1 / mK) if mK else None,
                "E_k": sum(k * a * (lam ** k) for k, a in enumerate(lv)) / Z,
            }
        b277[n] = {"K": K, "levels": lv, "A_K": lv[K], "A_Km1": lv[K - 1], "mass": mass}

    # B276: order parameter s distribution at high lambda from multigraded
    b276 = {}
    for lam in [2, 8, 21, 55, 144]:
        Z = 0.0
        wsum = defaultdict(float)
        for (k, cnt), v in hist.items():
            w = v * (lam ** k)
            Z += w
            s = cnt[corner_i] - cnt[inner_i]
            wsum[s] += w
        dist = {str(s): wsum[s] / Z for s in sorted(wsum)}
        b276[str(lam)] = dist

    # B280: mutual exclusion — co-occurrence is zero by definition (one profile per set),
    # but we can measure whether profiles are 'compatible' via whether mixed profiles exist.
    # For top degree K=7, list profiles and pairwise: do any sets have profile = average/mix?
    top = [(cnt, v) for (k, cnt), v in hist.items() if k == 7]
    # exclusion metric: min Hamming between distinct top profiles, and whether a profile
    # between two others exists
    profs = [cnt for cnt, v in top]
    b280 = {
        "top_profiles": [{"profile": list(cnt), "count": v} for cnt, v in top],
        "n_top_profiles": len(top),
        "sum_top": sum(v for _, v in top),
        "profile_pairs": [],
    }
    for i in range(len(profs)):
        for j in range(i + 1, len(profs)):
            a, b = profs[i], profs[j]
            ham = sum(x != y for x, y in zip(a, b))
            # midpoint profile?
            mid = tuple((x + y) // 2 for x, y in zip(a, b))
            mid_exists = any(tuple(cnt) == mid for cnt, _ in top)
            b280["profile_pairs"].append({
                "a": list(a), "b": list(b), "hamming": ham, "midpoint": list(mid),
                "midpoint_in_top": mid_exists,
            })

    result["B274"] = b274
    result["B277"] = b277
    result["B276"] = b276
    result["B280"] = b280
    OUT.write_text(json.dumps(result, indent=2, default=str))
    print("WROTE", OUT, flush=True)


if __name__ == "__main__":
    main()
