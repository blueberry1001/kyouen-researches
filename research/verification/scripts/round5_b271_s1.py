#!/usr/bin/env python3
"""Stage 1: B271/B272 n=4 correlation + B275/B277 thermo + B280 multigraded Z.

Writes round5_b271_s1.json (merged later).
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from fractions import Fraction
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, det4, is_forbidden_quad, square_points

OUT = Path(__file__).resolve().parents[1] / "round5_b271_s1.json"
KNOWN_K = {4: 7, 5: 9, 6: 11}
KNOWN_MAX = {4: 64, 5: 100, 6: 349132}


def poly_mul(a, b):
    r = [0] * (len(a) + len(b) - 1)
    for i, ai in enumerate(a):
        if ai == 0:
            continue
        for j, bj in enumerate(b):
            if bj == 0:
                continue
            r[i + j] += ai * bj
    return r


def poly_sub(a, b):
    n = max(len(a), len(b))
    r = [0] * n
    for i in range(n):
        ai = a[i] if i < len(a) else 0
        bi = b[i] if i < len(b) else 0
        r[i] = ai - bi
    return r


def poly_eval(a, lam):
    v = 0
    p = 1
    for c in a:
        v += c * p
        p *= lam
    return v


def positive_sign_changes(coeffs):
    import numpy as np

    a = list(coeffs)
    while a and a[-1] == 0:
        a.pop()
    if len(a) <= 1 or all(c == 0 for c in a):
        return 0, []
    s0 = 0
    for c in a:
        if c != 0:
            s0 = 1 if c > 0 else -1
            break
    try:
        roots = np.roots([float(c) for c in a])
    except Exception:
        return -1, []
    pos_real = sorted(
        float(r.real) for r in roots if abs(r.imag) < 1e-8 and r.real > 1e-12
    )
    sc = 0
    last_sign = s0
    last_x = 0.0
    roots_used = []
    for rt in pos_real:
        mid = (last_x + rt) / 2 if last_x > 0 else rt / 2
        val = poly_eval(a, mid)
        if val == 0:
            continue
        sgn = 1 if val > 0 else -1
        if sgn != last_sign:
            sc += 1
            last_sign = sgn
            roots_used.append(rt)
        last_x = rt
    if pos_real:
        big = pos_real[-1] * 2 + 1
        val = poly_eval(a, big)
        if val != 0:
            sgn = 1 if val > 0 else -1
            if sgn != last_sign:
                sc += 1
                roots_used.append("tail")
    return sc, roots_used[:8]


def b271_b272(n=4):
    pts = square_points(n)
    V = n * n
    b = Board(pts, name=f"{n}x{n}")
    quads = b.quads
    Z = [0] * (V + 1)
    Wp = [[0] * (V + 1) for _ in range(V)]
    Wpq = [[0] * (V + 1) for _ in range(V * V)]
    n_safe = 0
    for occ in range(1 << V):
        ok = True
        for q in quads:
            if (occ & q) == q:
                ok = False
                break
        if not ok:
            continue
        n_safe += 1
        k = occ.bit_count()
        Z[k] += 1
        members = [p for p in range(V) if (occ >> p) & 1]
        for p in members:
            Wp[p][k] += 1
        for p, q in combinations(members, 2):
            Wpq[p * V + q][k] += 1
            Wpq[q * V + p][k] += 1

    sign_changes = []
    all_pair_status = []  # compact: sc for every pair
    for p, q in combinations(range(V), 2):
        N = poly_sub(poly_mul(Wpq[p * V + q], Z), poly_mul(Wp[p], Wp[q]))
        sc, roots = positive_sign_changes(N)
        all_pair_status.append(sc)
        if sc > 0:
            sign_changes.append({
                "p": [p // n, p % n],
                "q": [q // n, q % n],
                "n_sign_changes": sc,
                "approx_positive_roots": [str(r) for r in roots],
                "N_coeffs": N,
            })

    K = KNOWN_K[n]
    max_sets = []
    for occ in range(1 << V):
        if occ.bit_count() != K:
            continue
        ok = True
        for q in quads:
            if (occ & q) == q:
                ok = False
                break
        if ok:
            max_sets.append(occ)
    cnt_p = [0] * V
    cnt_pq = [[0] * V for _ in range(V)]
    M = len(max_sets)
    for occ in max_sets:
        members = [p for p in range(V) if (occ >> p) & 1]
        for p in members:
            cnt_p[p] += 1
        for p, q in combinations(members, 2):
            cnt_pq[p][q] += 1
            cnt_pq[q][p] += 1
    in_same_quad = [[False] * V for _ in range(V)]
    for qmask in quads:
        ms = [p for p in range(V) if (qmask >> p) & 1]
        for p, q in combinations(ms, 2):
            in_same_quad[p][q] = in_same_quad[q][p] = True

    pos, neg, competing = [], [], []
    for p, q in combinations(range(V), 2):
        num = M * cnt_pq[p][q] - cnt_p[p] * cnt_p[q]
        entry = {
            "p": [p // n, p % n],
            "q": [q // n, q % n],
            "cnt_p": cnt_p[p],
            "cnt_q": cnt_p[q],
            "cnt_pq": cnt_pq[p][q],
            "cov_num": num,
            "in_same_forbidden_quad": in_same_quad[p][q],
        }
        if num > 0:
            pos.append(entry)
            if in_same_quad[p][q]:
                competing.append(entry)
        elif num < 0:
            neg.append(entry)

    return {
        "n": n,
        "V": V,
        "n_safe_sets": n_safe,
        "Z_coeffs": Z,
        "K": K,
        "n_maximal": M,
        "n_pairs_total": len(all_pair_status),
        "n_sign_changing_pairs": len(sign_changes),
        "sign_changes": sign_changes[:30],
        "max_phase": {
            "n_positive_cov_pairs": len(pos),
            "n_negative_cov_pairs": len(neg),
            "n_competing_positive": len(competing),
            "competing_positive_sample": competing[:20],
            "positive_sample": pos[:10],
            "negative_sample": neg[:10],
            "cnt_p": cnt_p,
            "K": K,
            "M": M,
        },
    }


def thermo_from_levels(level):
    K = max(i for i, v in enumerate(level) if v > 0)
    profile = {}
    best = None
    for lam in [Fraction(1, 2), 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377,
                610, 987, 1597, 2584, 4181, 6765, 10946, 17711, 28657, 46368,
                75025, 121393, 196418, 317811, 514229, 832040, 1346269]:
        Z = 0
        s1 = 0
        s2 = 0
        pl = Fraction(1)
        lamf = Fraction(lam)
        for k, a in enumerate(level):
            if a == 0:
                pl *= lamf
                continue
            Z += a * pl
            s1 += k * a * pl
            s2 += k * k * a * pl
            pl *= lamf
        if Z == 0:
            continue
        Ek = Fraction(s1, Z)
        Ek2 = Fraction(s2, Z)
        var = Ek2 - Ek * Ek
        profile[str(lam)] = {"E_k": float(Ek), "Var": float(var)}
        if best is None or var > best[1]:
            best = (lam, var, Ek)
    return {
        "K": K,
        "var_max_lambda": str(best[0]) if best else None,
        "var_max": float(best[1]) if best else None,
        "E_k_at_var_max": float(best[2]) if best else None,
        "profile": profile,
    }


def multigraded_Z(n=4):
    pts = square_points(n)
    V = n * n
    b = Board(pts, name=f"{n}x{n}")

    def d4(x, y):
        cands = [
            (x, y), (y, n - 1 - x), (n - 1 - x, n - 1 - y), (n - 1 - y, x),
            (y, x), (x, n - 1 - y), (n - 1 - x, y), (n - 1 - y, n - 1 - x),
        ]
        return min(cands)

    orbit_rep = {}
    orbit_of = [None] * V
    for y in range(n):
        for x in range(n):
            rep = d4(x, y)
            if rep not in orbit_rep:
                orbit_rep[rep] = len(orbit_rep)
            orbit_of[y * n + x] = orbit_rep[rep]
    n_orb = len(orbit_rep)
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
    K = KNOWN_K[n]
    top = {str(kc): v for (k, kc), v in hist.items() if k == K}
    # also k=K-1 profiles
    near = {str(kc): v for (k, kc), v in hist.items() if k == K - 1}
    return {
        "n": n,
        "n_orbits": n_orb,
        "orbit_sizes": [sum(1 for p in range(V) if orbit_of[p] == o) for o in range(n_orb)],
        "orbit_reps": sorted(orbit_rep.keys()),
        "n_multi_terms": len(hist),
        "top_degree_orbit_profiles": top,
        "top_degree_sum": sum(top.values()),
        "known_maximal": KNOWN_MAX.get(n),
        "near_top_orbit_profiles": near,
    }


def main():
    result = {}
    print("B271/B272 ...", flush=True)
    result["B271_B272"] = b271_b272(4)
    print("B275/B277 ...", flush=True)
    LEVELS = {
        4: [1, 16, 120, 560, 1626, 2360, 1064, 64],
        5: [1, 25, 300, 2300, 11824, 37272, 59192, 35208, 5172, 100],
    }
    result["B275"] = {f"n{n}": thermo_from_levels(lv) for n, lv in LEVELS.items()}
    result["B277"] = {}
    for n, level in LEVELS.items():
        K = max(i for i, v in enumerate(level) if v > 0)
        result["B277"][f"n{n}"] = {
            "levels": level,
            "K": K,
            "A_K": level[K],
            "A_Kminus1": level[K - 1],
            "A_Kminus2": level[K - 2],
            "ratio_Km1_over_K": level[K - 1] / level[K],
            "ratio_Km2_over_K": level[K - 2] / level[K],
        }
    print("B280 ...", flush=True)
    result["B280"] = multigraded_Z(4)
    OUT.write_text(json.dumps(result, indent=2, default=str))
    print("WROTE", OUT)


if __name__ == "__main__":
    main()
