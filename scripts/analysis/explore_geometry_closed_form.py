#!/usr/bin/env python3
"""探索3: 禁止4点組の閉形式分解、円上の格子点極値、近接行列式分布。

正確な線/円の格子点カウントから forbidden = Σ C(|L|,4) + Σ C(|C|,4) を検証する。
"""
from __future__ import annotations

import itertools
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "exploration"
OUT.mkdir(parents=True, exist_ok=True)


def area2(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def is_collinear(pts):
    a, b, c, d = pts
    return area2(a, b, c) == 0 and area2(a, b, d) == 0


def det4_quad(p, q, r, s):
    """整数4×4行列式 |x²+y², x, y, 1|。"""
    pts = (p, q, r, s)
    A = np.zeros((4, 4), dtype=object)
    for i, (x, y) in enumerate(pts):
        A[i, 0] = x * x + y * y
        A[i, 1] = x
        A[i, 2] = y
        A[i, 3] = 1
    # exact integer det via expansion
    def det3(m):
        return (
            m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
        )

    return (
        A[0][0] * det3([[A[i][j] for j in (1, 2, 3)] for i in (1, 2, 3)])
        - A[0][1] * det3([[A[i][j] for j in (0, 2, 3)] for i in (1, 2, 3)])
        + A[0][2] * det3([[A[i][j] for j in (0, 1, 3)] for i in (1, 2, 3)])
        - A[0][3] * det3([[A[i][j] for j in (0, 1, 2)] for i in (1, 2, 3)])
    )


def line_norm(A, B, C):
    g = math.gcd(math.gcd(abs(A), abs(B)), abs(C))
    if g:
        A, B, C = A // g, B // g, C // g
    if A < 0 or (A == 0 and B < 0):
        A, B, C = -A, -B, -C
    return (A, B, C)


def collect_lines(n):
    pts = [(i % n, i // n) for i in range(n * n)]
    lines = defaultdict(set)
    for i in range(n * n):
        xi, yi = pts[i]
        for j in range(i + 1, n * n):
            xj, yj = pts[j]
            A = yj - yi
            B = xi - xj
            C = -(A * xi + B * yi)
            key = line_norm(A, B, C)
            lines[key].add(i)
            lines[key].add(j)
    return {k: frozenset(v) for k, v in lines.items()}


def circle_params(p, q, r):
    ax, ay = p
    bx, by = q
    cx, cy = r
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if d == 0:
        return None
    a2 = ax * ax + ay * ay
    b2 = bx * bx + by * by
    c2 = cx * cx + cy * cy
    ux = a2 * (by - cy) + b2 * (cy - ay) + c2 * (ay - by)
    uy = a2 * (cx - bx) + b2 * (ax - cx) + c2 * (bx - ax)
    r2_num = (ax * d - ux) ** 2 + (ay * d - uy) ** 2  # r² d²
    # normalize (ux,uy,d) by gcd; r2_num scales by g²
    if d < 0:
        ux, uy, d = -ux, -uy, -d
    g = math.gcd(math.gcd(abs(ux), abs(uy)), abs(d))
    if g:
        ux, uy, d = ux // g, uy // g, d // g
        assert r2_num % (g * g) == 0
        r2_num //= g * g
    return (ux, uy, d, r2_num)


def on_circle(pt, params):
    ux, uy, d, r2_num = params
    x, y = pt
    return (x * d - ux) ** 2 + (y * d - uy) ** 2 == r2_num


def collect_circles(n):
    """非退化円を、その上の格子点全体の集合として列挙。"""
    pts = [(i % n, i // n) for i in range(n * n)]
    circles = {}
    # seed with every non-collinear triple
    for i in range(n * n):
        for j in range(i + 1, n * n):
            for k in range(j + 1, n * n):
                p, q, r = pts[i], pts[j], pts[k]
                if area2(p, q, r) == 0:
                    continue
                params = circle_params(p, q, r)
                if params is None:
                    continue
                if params in circles:
                    continue
                on = frozenset(idx for idx in range(n * n) if on_circle(pts[idx], params))
                if len(on) >= 4:
                    circles[params] = on
    return circles


def analyze_board(n):
    pts = [(i % n, i // n) for i in range(n * n)]
    lines = collect_lines(n)
    circles = collect_circles(n)

    line_c4 = 0
    line_hist = Counter()
    max_line = 0
    for s in lines.values():
        k = len(s)
        line_hist[k] += 1
        max_line = max(max_line, k)
        if k >= 4:
            line_c4 += math.comb(k, 4)

    circle_c4 = 0
    circle_hist = Counter()
    max_circle = 0
    max_circles = []
    for params, s in circles.items():
        k = len(s)
        circle_hist[k] += 1
        if k > max_circle:
            max_circle = k
            max_circles = [(params, sorted(s))]
        elif k == max_circle:
            max_circles.append((params, sorted(s)))
        if k >= 4:
            circle_c4 += math.comb(k, 4)

    # actual det=0 count and split
    n_coll = 0
    n_circ = 0
    det_hist = Counter()
    min_abs_nonzero = None
    for comb in itertools.combinations(range(n * n), 4):
        q = [pts[i] for i in comb]
        if is_collinear(q):
            n_coll += 1
            det_hist[0] += 1
            continue
        d = det4_quad(*q)
        if d == 0:
            n_circ += 1
            det_hist[0] += 1
        else:
            ad = abs(int(d))
            det_hist[ad if ad < 20 else "ge20"] += 1
            if min_abs_nonzero is None or ad < min_abs_nonzero:
                min_abs_nonzero = ad

    # Does every circle k-set's C(k,4) equal concyclic quads?
    # Note: 4 collinear are NOT on a finite circle, so sets are disjoint.
    return {
        "n": n,
        "n_points": n * n,
        "line_size_hist": dict(sorted(line_hist.items())),
        "max_points_on_line": max_line,
        "collinear_quads_from_lines": line_c4,
        "actual_collinear_quads": n_coll,
        "collinear_match": line_c4 == n_coll,
        "circle_size_hist": dict(sorted(circle_hist.items())),
        "n_circles_ge4": sum(v for k, v in circle_hist.items() if k >= 4),
        "max_points_on_circle": max_circle,
        "max_circle_examples": [
            {"params": list(p), "points_xy": [(pts[i][0], pts[i][1]) for i in s]}
            for p, s in max_circles[:3]
        ],
        "concyclic_quads_from_circles": circle_c4,
        "actual_concyclic_quads": n_circ,
        "concyclic_match": circle_c4 == n_circ,
        "total_forbidden": n_coll + n_circ,
        "published_forbidden": {
            1: 0, 2: 1, 3: 14, 4: 194, 5: 826, 6: 2491,
            7: 6364, 8: 14564, 9: 29152, 10: 54441,
        }.get(n),
        "min_abs_nonzero_det": min_abs_nonzero,
        "det_abs_hist_small": {str(k): v for k, v in sorted(det_hist.items(), key=lambda x: str(x[0])) if k != 0},
        "n_zero_det": det_hist[0],
    }


def formula_prediction(n):
    """行・円のヒストグラムが与えられたときの理論値は analyze_board で計算済み。

    追加: 公式の候補。Σ_lines C(k,4) + Σ_circles C(k,4)。
    円の列挙は重いので、n<=7 まで。
    """
    return None


def max_circle_lattice_theory(n):
    """n×n 格子点集合上の円の最大格子点数を、半径2乗の分類で近似列挙。

    中心を格子点/半格子点に置き、r² = a²+b² の表現数から上限を推定。
    ここでは「実際に何点乗るか」の完全列挙は collect_circles に任せる。
    """
    # Count representability of r2 as sum of two squares within the box,
    # for centers on half-integer lattice.
    # For each center (cx, cy) with 2cx, 2cy integers in range, count points
    # at each squared distance (scaled).
    pts = [(i % n, i // n) for i in range(n * n)]
    best = 0
    best_info = None
    # centers: (i/2, j/2) for i,j covering the board plus margin
    for i2 in range(-1, 2 * n + 1):
        for j2 in range(-1, 2 * n + 1):
            # center = (i2/2, j2/2)
            dist = Counter()
            for x, y in pts:
                # 4 * r2 = (2x - i2)^2 + (2y - j2)^2
                d4 = (2 * x - i2) ** 2 + (2 * y - j2) ** 2
                dist[d4] += 1
            # skip d4=0 (center is a point — circle radius 0 has 1 point)
            for d4, cnt in dist.items():
                if d4 > 0 and cnt > best:
                    best = cnt
                    best_info = {
                        "center_x2": i2,
                        "center_y2": j2,
                        "r2_x4": d4,
                        "count": cnt,
                    }
    return {"n": n, "max_on_circle": best, "witness": best_info}


def main():
    report = {}
    print("=== 円の最大格子点数 (中心=半整数格子) ===")
    maxc = {}
    for n in range(2, 10):
        maxc[n] = max_circle_lattice_theory(n)
        print(f"  n={n}: max={maxc[n]['max_on_circle']}  {maxc[n]['witness']}")
    report["max_circle_points"] = maxc

    print("\n=== 完全な線/円分解と det=0 検証 ===")
    boards = {}
    for n in range(2, 8):
        print(f"  n={n} ...")
        boards[n] = analyze_board(n)
        b = boards[n]
        print(f"    collinear match={b['collinear_match']} ({b['actual_collinear_quads']})  "
              f"concyclic match={b['concyclic_match']} ({b['actual_concyclic_quads']})  "
              f"total={b['total_forbidden']} published={b['published_forbidden']}  "
              f"max_circle={b['max_points_on_circle']}")
    report["boards"] = boards

    out = OUT / "exploration_report_3.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
