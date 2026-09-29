#!/usr/bin/env python3
"""n=6 fractional capacity LP using float simplex (numpy). Also B285 small boards.

Writes round5_b271_s2lp_n6.json and merges B285 into round5_b271_s2lp.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, det4, square_points, rect_points, is_forbidden_quad

OUT_N6 = Path(__file__).resolve().parents[1] / "round5_b271_s2lp_n6.json"
OUT_MAIN = Path(__file__).resolve().parents[1] / "round5_b271_s2lp.json"


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


def float_simplex_max(c, A, b, max_iter=20000):
    """max c.x, A x <= b, x >= 0. numpy float simplex."""
    m = len(A)
    n = len(c)
    T = np.zeros((m + 1, n + m + 1), dtype=np.float64)
    for i in range(m):
        T[i, :n] = A[i]
        T[i, n + i] = 1.0
        T[i, -1] = b[i]
    T[m, :n] = c
    basis = list(range(n, n + m))
    for _ in range(max_iter):
        col = -1
        best = 0.0
        for j in range(n + m):
            if T[m, j] > best + 1e-12:
                best = T[m, j]
                col = j
        if col < 0:
            break
        r = -1
        br = None
        for i in range(m):
            if T[i, col] > 1e-12:
                ratio = T[i, -1] / T[i, col]
                if br is None or ratio < br - 1e-12:
                    br = ratio
                    r = i
        if r < 0:
            raise ValueError("unbounded")
        piv = T[r, col]
        T[r, :] /= piv
        T[m, :] -= T[m, col] * T[r, :]
        for i in range(m):
            if i != r and abs(T[i, col]) > 1e-15:
                T[i, :] -= T[i, col] * T[r, :]
        basis[r] = col
    x = np.zeros(n)
    for i, bi in enumerate(basis):
        if bi < n:
            x[bi] = T[i, -1]
    return float(T[m, -1]), x


def n6_lp():
    n = 6
    pts = square_points(n)
    V = n * n
    print("enumerating carriers ...", flush=True)
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
    A = []
    b = []
    for car in carriers:
        row = [0.0] * V
        for p in car:
            row[p] = 1.0
        A.append(row)
        b.append(3.0)
    for p in range(V):
        row = [0.0] * V
        row[p] = 1.0
        A.append(row)
        b.append(1.0)
    c = [1.0] * V
    print("solving float LP ...", flush=True)
    obj, x = float_simplex_max(c, A, b)
    K = 11
    print(f"  frac={obj} K={K} gap={obj-K}", flush=True)
    return {
        "V": V,
        "K_n_known": K,
        "n_carriers": len(carriers),
        "n_lines": n_line,
        "n_circles": n_circ,
        "line_size_hist": dict(Counter(line_sizes)),
        "circle_size_hist": dict(Counter(circ_sizes)),
        "max_line_size": max(line_sizes) if line_sizes else 0,
        "max_circle_size": max(circ_sizes) if circ_sizes else 0,
        "fractional_lp_optimum_float": obj,
        "gap_frac_minus_K": obj - K,
        "x_frac": [float(v) for v in x],
    }


def b285():
    candidates = {
        "single_origin": [(0, 0)],
        "row2": [(0, 0), (1, 0)],
        "diag2": [(0, 0), (1, 1)],
        "L_shape": [(0, 0), (1, 0), (0, 1)],
        "tri3": [(0, 0), (2, 0), (0, 2)],
        "k2_far": [(0, 0), (2, 1)],
        "safe4": [(0, 0), (1, 0), (0, 1), (2, 2)],
        "safe4b": [(0, 0), (1, 0), (2, 1), (1, 2)],
        "safe5": [(0, 0), (1, 0), (0, 1), (2, 2), (3, 1)],
    }
    boards = {
        "4x4": square_points(4),
        "5x4": rect_points(5, 4),
        "4x5": rect_points(4, 5),
        "3x5": rect_points(3, 5),
        "5x5minus3": [p for p in square_points(5) if p not in {(0, 0), (4, 4), (4, 0)}],
    }
    results = {}
    for name, S in candidates.items():
        if len(S) >= 4 and any(is_forbidden_quad(list(c)) for c in combinations(S, 4)):
            results[name] = {"error": "S contains a forbidden quad", "S": S}
            continue
        vals = {}
        for bname, bpts in boards.items():
            bset = set(bpts)
            if any(p not in bset for p in S):
                vals[bname] = None
                continue
            b = Board(bpts, name=bname)
            index = {p: i for i, p in enumerate(bpts)}
            occ = 0
            for p in S:
                occ |= 1 << index[p]
            if not b.is_safe(occ):
                vals[bname] = "S not safe"
                continue
            memo = b.solve_grundy()
            vals[bname] = memo.get(occ)
        distinct = sorted({v for v in vals.values() if isinstance(v, int)})
        results[name] = {
            "S": S,
            "grundy_by_board": vals,
            "n_distinct": len(distinct),
            "distinct": distinct,
        }
    return results


def main():
    res_n6 = n6_lp()
    OUT_N6.write_text(json.dumps({"n6": res_n6}, indent=2, default=str))
    print("WROTE", OUT_N6, flush=True)

    print("B285 ...", flush=True)
    b285_res = b285()
    for k, v in b285_res.items():
        print(" ", k, v.get("grundy_by_board"), "distinct", v.get("n_distinct"), flush=True)

    # merge into main json if present
    main_path = OUT_MAIN
    data = {}
    if main_path.exists():
        data = json.loads(main_path.read_text())
    data["B288_B289_B290"] = data.get("B288_B289_B290", {})
    data["B288_B289_B290"]["n6"] = res_n6
    data["B285"] = b285_res
    main_path.write_text(json.dumps(data, indent=2, default=str))
    print("WROTE", main_path, flush=True)


if __name__ == "__main__":
    main()
