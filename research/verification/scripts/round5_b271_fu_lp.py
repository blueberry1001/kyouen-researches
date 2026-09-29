#!/usr/bin/env python3
"""Followup: B288 exact n=6 LP + B290 rank/cut inequalities + dual certificates.

Writes round5_b271_fu_lp.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from fractions import Fraction
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, det4, square_points

OUT = Path(__file__).resolve().parents[1] / "round5_b271_fu_lp.json"
KNOWN_K = {4: 7, 5: 9, 6: 11}


def _det_row(pt):
    x, y = pt
    return (x * x + y * y, x, y, 1)


def collinear(p, q, r):
    return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]) == 0


def enumerate_carriers(pts):
    V = len(pts)
    seen = set()
    carriers = []
    for i, j, k in combinations(range(V), 3):
        ri, rj, rk = _det_row(pts[i]), _det_row(pts[j]), _det_row(pts[k])
        memb = [t for t, pt in enumerate(pts) if det4(ri, rj, rk, _det_row(pt)) == 0]
        if len(memb) < 4:
            continue
        fs = frozenset(memb)
        if fs not in seen:
            seen.add(fs)
            carriers.append(fs)
    return carriers


def solve_lp_max_frac(c, A, b, max_iter=200000):
    """max c.x, A x <= b, x >= 0. Exact Fraction simplex. Returns (obj, x, duals_y)."""
    m = len(A)
    n = len(c)
    T = []
    for i in range(m):
        row = [Fraction(A[i][j]) for j in range(n)] + [Fraction(int(k == i)) for k in range(m)] + [Fraction(b[i])]
        T.append(row)
    z = [Fraction(c[j]) for j in range(n)] + [Fraction(0)] * m + [Fraction(0)]
    basis = [n + i for i in range(m)]
    for _ in range(max_iter):
        col = -1
        for j in range(n + m):
            if z[j] > 0 and (col < 0 or z[j] > z[col]):
                col = j
        if col < 0:
            break
        r = -1
        br = None
        for i in range(m):
            if T[i][col] > 0:
                ratio = T[i][-1] / T[i][col]
                if br is None or ratio < br:
                    br = ratio
                    r = i
        if r < 0:
            raise ValueError("LP unbounded")
        piv = T[r][col]
        T[r] = [v / piv for v in T[r]]
        z = [z[j] - z[col] * T[r][j] for j in range(len(z))]
        for i in range(m):
            if i != r and T[i][col] != 0:
                fac = T[i][col]
                T[i] = [T[i][j] - fac * T[r][j] for j in range(len(T[i]))]
        basis[r] = col
    x = [Fraction(0)] * n
    y = [Fraction(0)] * m
    for i, bi in enumerate(basis):
        if bi < n:
            x[bi] = T[i][-1]
        # dual: y_i = z[n+i] after pivots?  Standard: y = reduced cost of slack
        # After solving max, z[n+i] holds -y_i or y_i depending on convention.
        # We recover duals from z-row of slack columns: z[n+i] = -y_i in this tableau.
    for i in range(m):
        y[i] = -z[n + i] if z[n + i] < 0 else z[n + i]
    # Prefer the convention that matches complementary slackness; compute both.
    y_raw = [-z[n + i] for i in range(m)]
    obj = -z[-1]
    return obj, x, y_raw


def build_constraints(carriers, V, extra_rows=None):
    A = []
    b = []
    for car in carriers:
        row = [0] * V
        for p in car:
            row[p] = 1
        A.append(row)
        b.append(3)
    if extra_rows:
        for U, rhs in extra_rows:
            row = [0] * V
            for p in U:
                row[p] = 1
            A.append(row)
            b.append(rhs)
    for p in range(V):
        row = [0] * V
        row[p] = 1
        A.append(row)
        b.append(1)
    return A, b


def max_safe_on_subset(pts_full, quads_full, subset_indices):
    """Max safe size restricted to subset of point-indices. Brute force if |subset|<=22."""
    k = len(subset_indices)
    if k > 22:
        return None
    idx_of = {orig: i for i, orig in enumerate(subset_indices)}
    quads = []
    for q in quads_full:
        ms = [idx_of[p] for p in subset_indices if (q >> p) & 1]
        # need all 4 points of q inside subset
        members = [p for p in range(len(pts_full)) if (q >> p) & 1]
        if all(p in idx_of for p in members):
            m = 0
            for p in members:
                m |= 1 << idx_of[p]
            quads.append(m)
    best = 0
    for occ in range(1 << k):
        sz = occ.bit_count()
        if sz <= best:
            continue
        ok = True
        for q in quads:
            if (occ & q) == q:
                ok = False
                break
        if ok:
            best = sz
    return best


def b288_exact_n6():
    n = 6
    pts = square_points(n)
    V = n * n
    print("n6: enumerating carriers ...", flush=True)
    carriers = enumerate_carriers(pts)
    print(f"  carriers={len(carriers)}", flush=True)
    A, b = build_constraints(carriers, V)
    print("n6: solving exact Fraction LP ...", flush=True)
    obj, x, y = solve_lp_max_frac([1] * V, A, b)
    print(f"  frac={obj} = {float(obj)}", flush=True)
    nz_x = sum(1 for v in x if v != 0)
    y_pos = [v for v in y if v > 0]
    return {
        "V": V,
        "n_carriers": len(carriers),
        "fractional_lp_optimum_frac": f"{obj.numerator}/{obj.denominator}",
        "fractional_lp_optimum_float": float(obj),
        "K_n_known": KNOWN_K[n],
        "gap_frac_minus_K": float(obj - KNOWN_K[n]),
        "x_frac": [f"{v.numerator}/{v.denominator}" for v in x],
        "x_float": [float(v) for v in x],
        "n_nonzero_x": nz_x,
        "n_positive_duals": len(y_pos),
        "dual_sum_3y": f"{(3 * sum(y)).numerator}/{(3 * sum(y)).denominator}" if y else None,
        "dual_obj_float": float(3 * sum(y)) if y else None,
    }


def b290_rank_cuts(n=4):
    """Add rank inequalities on the LP support / carrier unions. Iterate cutting planes."""
    pts = square_points(n)
    V = n * n
    b = Board(pts, name=f"{n}x{n}")
    carriers = enumerate_carriers(pts)
    print(f"n={n}: carriers={len(carriers)}", flush=True)
    K = KNOWN_K[n]

    # collect all safe sets (small n only)
    safe = []
    for occ in range(1 << V):
        ok = True
        for q in b.quads:
            if (occ & q) == q:
                ok = False
                break
        if ok:
            safe.append(occ)
    print(f"  safe sets={len(safe)}", flush=True)

    def width(U):
        U = list(U)
        mask = 0
        for p in U:
            mask |= 1 << p
        best = 0
        for occ in safe:
            best = max(best, (occ & mask).bit_count())
        return best

    # initial LP with carrier rows only
    A, bb = build_constraints(carriers, V)
    obj, x, y = solve_lp_max_frac([1] * V, A, bb)
    print(f"  initial frac={float(obj)}", flush=True)

    cuts = []
    iterations = []
    for it in range(12):
        support = [p for p in range(V) if x[p] > 0]
        # candidate U's: support itself, and unions of pairs of carriers
        cands = [frozenset(support)]
        for c1, c2 in combinations(carriers, 2):
            U = c1 | c2
            if 6 <= len(U) <= 18:
                cands.append(U)
        # also top-weight subsets: take points with x>=0.5
        heavy = [p for p in range(V) if x[p] >= Fraction(1, 2)]
        if len(heavy) >= 5:
            cands.append(frozenset(heavy))

        added = 0
        seen_u = set()
        for U in cands:
            if U in seen_u:
                continue
            seen_u.add(U)
            su = sum(x[p] for p in U)
            w = width(U)
            if su > w:
                cuts.append({"U": sorted(U), "rhs": w, "violated_sum": f"{su.numerator}/{su.denominator}", "it": it})
                row = [0] * V
                for p in U:
                    row[p] = 1
                A.append(row)
                bb.append(w)
                added += 1
        print(f"  it={it} frac={float(obj)} cuts_added={added} total_cuts={len(cuts)}", flush=True)
        iterations.append({"it": it, "frac": float(obj), "n_cuts_added": added, "n_cuts_total": len(cuts)})
        if added == 0:
            break
        obj, x, y = solve_lp_max_frac([1] * V, A, bb)

    return {
        "n": n,
        "K_n": K,
        "n_safe_sets": len(safe),
        "n_carriers": len(carriers),
        "final_frac": f"{obj.numerator}/{obj.denominator}",
        "final_frac_float": float(obj),
        "gap_after_cuts": float(obj - K),
        "n_cuts": len(cuts),
        "cuts_sample": cuts[:30],
        "iterations": iterations,
    }


def b288_dual_cert_n4():
    """Explicit dual certificate for n=4: find y on carriers with sum 3 y_c close to obj."""
    n = 4
    pts = square_points(n)
    V = n * n
    carriers = enumerate_carriers(pts)
    A, b = build_constraints(carriers, V)
    obj, x, y = solve_lp_max_frac([1] * V, A, b)
    # verify dual feasibility: sum_{c in p} y_c >= 1
    cover = [Fraction(0)] * V
    for i, car in enumerate(carriers):
        for p in car:
            cover[p] += y[i]
    # unit constraints y for x_p <= 1 are the last V entries; y has length m
    m = len(carriers) + V
    # re-read: build_constraints puts unit rows last
    dual_unit = y[len(carriers):]
    cover2 = [cover[p] + dual_unit[p] for p in range(V)]
    return {
        "n": n,
        "frac_opt": f"{obj.numerator}/{obj.denominator}",
        "frac_opt_float": float(obj),
        "K_n": KNOWN_K[n],
        "n_carriers": len(carriers),
        "dual_cover_min": f"{min(cover2).numerator}/{min(cover2).denominator}",
        "dual_cover_max": f"{max(cover2).numerator}/{max(cover2).denominator}",
        "dual_obj_3sum_y": f"{(3 * sum(y[:len(carriers)])).numerator}/{(3 * sum(y[:len(carriers)])).denominator}",
        "dual_unit_sum": f"{sum(dual_unit).numerator}/{sum(dual_unit).denominator}",
    }


def main():
    result = {}
    print("=== B288 exact n=6 ===", flush=True)
    result["b288_n6_exact"] = b288_exact_n6()
    OUT.write_text(json.dumps(result, indent=2, default=str))
    print("wrote partial", flush=True)

    print("=== B288 dual cert n=4 ===", flush=True)
    result["b288_dual_n4"] = b288_dual_cert_n4()
    OUT.write_text(json.dumps(result, indent=2, default=str))

    print("=== B290 rank cuts n=4 ===", flush=True)
    result["b290_n4"] = b290_rank_cuts(4)
    OUT.write_text(json.dumps(result, indent=2, default=str))

    print("=== B290 rank cuts n=5 ===", flush=True)
    result["b290_n5"] = b290_rank_cuts(5)
    OUT.write_text(json.dumps(result, indent=2, default=str))

    print("WROTE", OUT, flush=True)


if __name__ == "__main__":
    main()
