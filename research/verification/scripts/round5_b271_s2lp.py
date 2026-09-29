#!/usr/bin/env python3
"""Stage 2b-final: fractional capacity LP for n=4,5,6 (no slow bundle).

Writes round5_b271_s2lp.json
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

OUT = Path(__file__).resolve().parents[1] / "round5_b271_s2lp.json"
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


def solve_lp_max(c, A, b, max_iter=100000):
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
    for i, bi in enumerate(basis):
        if bi < n:
            x[bi] = T[i][-1]
    return -z[-1], x


def frac_lp(carriers, V):
    c = [1] * V
    A = []
    b = []
    for car in carriers:
        row = [0] * V
        for p in car:
            row[p] = 1
        A.append(row)
        b.append(3)
    for p in range(V):
        row = [0] * V
        row[p] = 1
        A.append(row)
        b.append(1)
    return solve_lp_max(c, A, b)


def main():
    result = {}
    for n in [4, 5, 6]:
        print(f"=== n={n} ===", flush=True)
        pts = square_points(n)
        V = n * n
        carriers = enumerate_carriers(pts)
        print(f"  carriers={len(carriers)}", flush=True)
        n_line = n_circ = 0
        line_sizes, circ_sizes = [], []
        for car in carriers:
            cl = list(car)
            if collinear(pts[cl[0]], pts[cl[1]], pts[cl[2]]):
                n_line += 1
                line_sizes.append(len(car))
            else:
                n_circ += 1
                circ_sizes.append(len(car))
        K = KNOWN_K[n]
        b = Board(pts, name=f"{n}x{n}")
        K_calc = b.max_safe_size()
        obj_frac, x_frac = frac_lp(carriers, V)
        print(f"  K={K_calc} frac={obj_frac} gap={obj_frac-K}", flush=True)

        # light B290: only pairs of carriers with |c1∩c2|>=3 (very few)
        pair_rows = []
        for c1, c2 in combinations(carriers, 2):
            if len(c1 & c2) >= 3:
                U = sorted(c1 | c2)
                pair_rows.append((U, 5))
        obj_bundle = None
        if pair_rows and n <= 5:
            obj_bundle, _ = frac_lp(carriers, V)  # placeholder, do real below
            # real with extra rows
            c = [1] * V
            A = []
            bb = []
            for car in carriers:
                row = [0] * V
                for p in car:
                    row[p] = 1
                A.append(row)
                bb.append(3)
            for idxs, rhs in pair_rows:
                row = [0] * V
                for p in idxs:
                    row[p] = 1
                A.append(row)
                bb.append(rhs)
            for p in range(V):
                row = [0] * V
                row[p] = 1
                A.append(row)
                bb.append(1)
            obj_bundle, _ = solve_lp_max(c, A, bb)
            print(f"  light-bundle rows={len(pair_rows)} obj={obj_bundle}", flush=True)

        result[f"n{n}"] = {
            "V": V,
            "K_n_known": K,
            "K_n_calculated": K_calc,
            "n_carriers": len(carriers),
            "n_lines": n_line,
            "n_circles": n_circ,
            "line_size_hist": dict(Counter(line_sizes)),
            "circle_size_hist": dict(Counter(circ_sizes)),
            "max_line_size": max(line_sizes) if line_sizes else 0,
            "max_circle_size": max(circ_sizes) if circ_sizes else 0,
            "fractional_lp_optimum": float(obj_frac),
            "fractional_lp_optimum_frac": f"{obj_frac.numerator}/{obj_frac.denominator}",
            "gap_frac_minus_K": float(obj_frac - K),
            "x_frac": [float(v) for v in x_frac],
            "n_light_bundle_rows": len(pair_rows),
            "light_bundle_optimum": (float(obj_bundle) if obj_bundle is not None else None),
            "light_bundle_frac": (
                f"{obj_bundle.numerator}/{obj_bundle.denominator}" if obj_bundle is not None else None
            ),
        }
        OUT.write_text(json.dumps({"B288_B289_B290": result}, indent=2, default=str))
        print("  wrote", flush=True)


if __name__ == "__main__":
    main()
