#!/usr/bin/env python3
"""B288 true fractional LP + B289 gap + B290 crossing-circle inequalities.

Primal (capacity relaxation of safe-set size):
  max  sum_p x_p
  s.t. sum_{p in q} x_p <= 3   for each forbidden quad q
       0 <= x_p <= 1
K_n is the integer optimum. frac_opt = LP optimum.

B290: add small-circle-bundle inequalities and see if they close the gap.
"""
import json
from pathlib import Path
from itertools import combinations

import numpy as np
from scipy.optimize import linprog

OUT = Path(r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round5_b288_frac_lp.json")


def det4(rows):
    m = np.array(rows, dtype=object)
    # exact integer det via expansion
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
    quads = []
    for a, b, c, d in combinations(range(V), 4):
        m = [rows[a], rows[b], rows[c], rows[d]]
        if det4(m) == 0:
            quads.append((a, b, c, d))
    return V, pts, quads


def frac_lp(n, extra_ineq=None):
    V, pts, quads = build_quads(n)
    nq = len(quads)
    # variables x_0..x_{V-1}
    c = -np.ones(V)  # maximize sum x
    A = np.zeros((nq, V))
    for qi, q in enumerate(quads):
        for p in q:
            A[qi, p] = 1.0
    b_ub = np.full(nq, 3.0)
    if extra_ineq:
        for row, rhs in extra_ineq:
            A = np.vstack([A, row])
            b_ub = np.append(b_ub, rhs)
    bounds = [(0.0, 1.0)] * V
    res = linprog(c, A_ub=A, b_ub=b_ub, bounds=bounds, method="highs")
    return {
        "n": n,
        "V": V,
        "nquads": nq,
        "success": bool(res.success),
        "frac_opt": float(-res.fun) if res.success else None,
        "x": [float(v) for v in res.x] if res.success else None,
        "status": int(res.status),
        "message": res.message,
    }


def circle_bundle_ineqs(n, V, pts, quads, max_extra=20):
    """B290: inequalities from small circle bundles.
    A circle through 3 lattice points defines a candidate 4th.
    Bundle: for points on a common circle (>=4 on a circle), the whole
    circle-set C satisfies |S ∩ C| <= 3 (since any 4 on the circle is a quad).
    Also for lines: |S ∩ L| <= 3.
    Collect circles with >=4 points and lines with >=4 points on the n x n grid.
    """
    from collections import defaultdict
    # lines: ax+by=c with >=4 grid points
    lines = []
    # horizontal / vertical / diagonal
    for y in range(n):
        lines.append({y * n + x for x in range(n)})
    for x in range(n):
        lines.append({y * n + x for y in range(n)})
    # general lines with >=4 points: use pairs and extend
    line_set = set()
    for i in range(V):
        for j in range(i + 1, V):
            x1, y1 = pts[i]
            x2, y2 = pts[j]
            dx, dy = x2 - x1, y2 - y1
            g = np.gcd(dx, dy)
            dx, dy = dx // g, dy // g
            # canonical direction
            if dx < 0 or (dx == 0 and dy < 0):
                dx, dy = -dx, -dy
            # walk
            S = set()
            x, y = x1, y1
            while 0 <= x < n and 0 <= y < n:
                S.add(y * n + x)
                x += dx
                y += dy
            x, y = x1 - dx, y1 - dy
            while 0 <= x < n and 0 <= y < n:
                S.add(y * n + x)
                x -= dx
                y -= dy
            if len(S) >= 4:
                key = tuple(sorted(S))
                line_set.add(key)
    # circles: through 3 points, check how many grid points lie on it
    # circle eq: (x^2+y^2) + D x + E y + F = 0
    # Use the det condition: 4 points cocircular iff det=0.
    # Enumerate all 4-subsets already in quads; group quads into circles
    # by checking 5-point consistency.
    # Simpler: for each triple, solve circle, count points.
    circles = set()
    for i, j, k in combinations(range(V), 3):
        (x1, y1), (x2, y2), (x3, y3) = pts[i], pts[j], pts[k]
        # solve for D,E,F in x^2+y^2 + D x + E y + F = 0
        A = np.array([[x1, y1, 1.0], [x2, y2, 1.0], [x3, y3, 1.0]], dtype=float)
        bvec = np.array([-(x1 * x1 + y1 * y1), -(x2 * x2 + y2 * y2), -(x3 * x3 + y3 * y3)], dtype=float)
        if abs(np.linalg.det(A)) < 1e-12:
            continue  # collinear
        sol = np.linalg.solve(A, bvec)
        D, E, F = sol
        on = []
        for p in range(V):
            x, y = pts[p]
            val = x * x + y * y + D * x + E * y + F
            if abs(val) < 1e-6:
                on.append(p)
        if len(on) >= 4:
            key = tuple(sorted(on))
            circles.add(key)
    # build inequalities |S ∩ C| <= 3
    ineqs = []
    for key in list(line_set) + list(circles):
        row = np.zeros(V)
        for p in key:
            row[p] = 1.0
        ineqs.append((row, 3.0))
    return ineqs, len(line_set), len(circles)


KNOWN_K = {2: 3, 3: 5, 4: 7, 5: 9, 6: 11, 7: 14}


def main():
    out = {}
    for n in (4, 5):
        base = frac_lp(n)
        K = KNOWN_K[n]
        base["K_n"] = K
        base["gap_frac_minus_K"] = (base["frac_opt"] - K) if base["frac_opt"] is not None else None
        # B290: add circle/line bundle inequalities
        V, pts, quads = build_quads(n)
        ineqs, nlines, ncircles = circle_bundle_ineqs(n, V, pts, quads)
        # Note: each quad already enforces sum<=3 on its 4 points.
        # Circle/line inequalities are implied when the circle has exactly 4
        # points (that's the same quad). They add value when the circle/line
        # has >=5 points.
        big = [(row, rhs) for row, rhs in ineqs if row.sum() >= 5]
        with_bundles = frac_lp(n, extra_ineq=big)
        with_bundles["K_n"] = K
        with_bundles["n_bundle_ineqs"] = len(big)
        with_bundles["nlines_ge4"] = nlines
        with_bundles["ncircles_ge4"] = ncircles
        with_bundles["gap_frac_minus_K"] = (
            with_bundles["frac_opt"] - K if with_bundles["frac_opt"] is not None else None
        )
        out[f"n{n}_base"] = base
        out[f"n{n}_bundles"] = with_bundles
        print(f"n={n} frac={base['frac_opt']} K={K} gap={base['gap_frac_minus_K']}")
        print(f"  bundles: frac={with_bundles['frac_opt']} n_ineq={len(big)} "
              f"lines={nlines} circles={ncircles}")
    OUT.write_text(json.dumps(out, indent=2))
    print("WROTE", OUT)


if __name__ == "__main__":
    main()
