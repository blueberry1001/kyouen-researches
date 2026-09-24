#!/usr/bin/env python3
"""探索2: max_search_depth=2n-1 の構造、5×5勝ち初手、禁止4点組の直線/円分解の正確な検証。"""
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


def on_same_circle(p, q, r, s):
    """整数演算で4点共円判定（3点が非共線のとき）。"""
    ax, ay = p
    bx, by = q
    cx, cy = r
    sx, sy = s
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if d == 0:
        return False
    a2 = ax * ax + ay * ay
    b2 = bx * bx + by * by
    c2 = cx * cx + cy * cy
    ux = a2 * (by - cy) + b2 * (cy - ay) + c2 * (ay - by)
    uy = a2 * (cx - bx) + b2 * (ax - cx) + c2 * (bx - ax)
    ls = (sx * d - ux) ** 2 + (sy * d - uy) ** 2
    lp = (ax * d - ux) ** 2 + (ay * d - uy) ** 2
    return ls == lp


def line_key(a, b):
    """2点を通る直線の正規形 (A,B,C): Ax+By+C=0。"""
    A = b[1] - a[1]
    B = a[0] - b[0]
    C = -(A * a[0] + B * a[1])
    g = math.gcd(math.gcd(abs(A), abs(B)), abs(C))
    if g:
        A, B, C = A // g, B // g, C // g
    if A < 0 or (A == 0 and B < 0):
        A, B, C = -A, -B, -C
    return (A, B, C)


def circle_key(p, q, r):
    """3点の外接円を正規形キーで返す。非共線なら (ux,uy,d,r2_num) 形式。"""
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
    r2_num = (ax * d - ux) ** 2 + (ay * d - uy) ** 2  # = r2 * d^2
    if d < 0:
        ux, uy, d = -ux, -uy, -d
    g = math.gcd(math.gcd(abs(ux), abs(uy)), abs(d))
    if g:
        ux, uy, d = ux // g, uy // g, d // g
        r2_num = r2_num // (g * g)
    return (ux, uy, d, r2_num)


def points_of(n):
    return [(i % n, i // n) for i in range(n * n)]


def exact_collinear_quads(n):
    """直線の点数から C(k,4) を計算して列挙と一致するか。"""
    pts = points_of(n)
    lines = defaultdict(list)
    for i in range(n * n):
        for j in range(i + 1, n * n):
            key = line_key(pts[i], pts[j])
            lines[key].append(i)
    # unique points per line
    line_sets = {k: tuple(sorted(set(v))) for k, v in lines.items()}
    sizes = Counter(len(v) for v in line_sets.values())
    expected = sum(math.comb(sz, 4) for sz in sizes if sz >= 4)
    # actual enumeration
    actual = 0
    for idx in itertools.combinations(range(n * n), 4):
        q = [pts[i] for i in idx]
        if is_collinear(q):
            actual += 1
    return {
        "n": n,
        "line_size_hist": dict(sorted(sizes.items())),
        "n_lines_ge4": sum(1 for sz in sizes if sz >= 4),
        "expected_collinear_quads": expected,
        "actual_collinear_quads": actual,
        "match": expected == actual,
    }


def exact_concyclic_structure(n):
    """共円4点組を円ごとに束ね、円上の格子点数分布を調べる。"""
    pts = points_of(n)
    circle_map = defaultdict(set)  # circle_key -> lattice points on it
    # for every non-collinear triple, record its circle
    for i in range(n * n):
        for j in range(i + 1, n * n):
            for k in range(j + 1, n * n):
                p, q, r = pts[i], pts[j], pts[k]
                key = circle_key(p, q, r)
                if key is None:
                    continue
                circle_map[key].update((i, j, k))

    # now for each circle, find ALL board points on it
    def on_circle(pt, key):
        ux, uy, d, r2_num = key
        x, y = pt
        return (x * d - ux) ** 2 + (y * d - uy) ** 2 == r2_num

    circle_points = {}
    for key, seed in circle_map.items():
        on = tuple(i for i in range(n * n) if on_circle(pts[i], key))
        circle_points[key] = on

    size_hist = Counter(len(v) for v in circle_points.values())
    quads_from_circles = sum(math.comb(sz, 4) for sz in size_hist if sz >= 4)

    # actual concyclic (non-collinear) quads
    actual_concyclic = 0
    actual_collinear = 0
    for idx in itertools.combinations(range(n * n), 4):
        q = [pts[i] for i in idx]
        if is_collinear(q):
            actual_collinear += 1
        elif on_same_circle(q[0], q[1], q[2], q[3]):
            actual_concyclic += 1

    # NOTE: 4 collinear points are also "concyclic" in the degenerate sense
    # and also satisfy det=0. Our classification is collinear first.
    # A circle with exactly 4+ points may include collinear 4-subsets only if
    # the circle is degenerate — we already exclude those (circle_key None).
    return {
        "n": n,
        "n_circles_ge3_points": len(circle_points),
        "circle_point_size_hist": dict(sorted(size_hist.items())),
        "max_points_on_circle": max(size_hist) if size_hist else 0,
        "quads_from_nondeg_circles": quads_from_circles,
        "actual_concyclic_quads": actual_concyclic,
        "actual_collinear_quads": actual_collinear,
        "concyclic_match": quads_from_circles == actual_concyclic,
    }


def maximal_safe_n4():
    """4x4 の極大安全配置を完全列挙。"""
    n = 4
    N = n * n
    pts = points_of(n)
    bad = set()
    for idx in itertools.combinations(range(N), 4):
        q = [pts[i] for i in idx]
        if is_collinear(q) or on_same_circle(q[0], q[1], q[2], q[3]):
            bad.add(idx)

    def safe(S):
        return all(q not in bad for q in itertools.combinations(sorted(S), 4))

    all_safe = Counter()
    maximal = []
    for r in range(0, N + 1):
        for S in itertools.combinations(range(N), r):
            if not safe(S):
                continue
            all_safe[r] += 1
            ext = False
            for p in range(N):
                if p in S:
                    continue
                if safe(S + (p,)):
                    ext = True
                    break
            if not ext:
                maximal.append(S)

    max_sizes = Counter(len(S) for S in maximal)
    return {
        "safe_hist": dict(sorted(all_safe.items())),
        "n_maximal": len(maximal),
        "maximal_size_hist": dict(sorted(max_sizes.items())),
        "max_safe": max(max_sizes) if max_sizes else 0,
        "min_maximal": min(max_sizes) if max_sizes else 0,
        "all_maximal_same_size": len(max_sizes) <= 1,
    }


def max_safe_upper_bound_construction(n):
    """2n-1 石の飽和配置が構成できるか、小さな n で試す。

    候補構成:
    - 2本の「密な」直線/円を重ねる
    - 端点を多く含む配置
    """
    pts = points_of(n)
    N = n * n

    def is_safe_set(S):
        S = sorted(S)
        if len(S) < 4:
            return True
        for idx in itertools.combinations(S, 4):
            q = [pts[i] for i in idx]
            if is_collinear(q) or on_same_circle(q[0], q[1], q[2], q[3]):
                return False
        return True

    def legal_moves(S):
        moves = []
        for p in range(N):
            if p in S:
                continue
            if is_safe_set(list(S) + [p]):
                moves.append(p)
        return moves

    results = {"n": n, "constructions": []}

    # Greedy DFS to find a saturated set of size 2n-1 or report max found
    target = 2 * n - 1
    found = []

    def dfs(S):
        if len(found) >= 5:
            return
        mv = legal_moves(S)
        if not mv:
            found.append(tuple(S))
            return
        if len(S) >= target:
            return
        # prefer moves that keep things tight: fewest legal moves after
        for p in mv:
            dfs(S + [p])
            if len(found) >= 5:
                return

    # start from empty and a few seeds
    for seed in ([], [0], [n // 2 * n + n // 2], [0, N - 1]):
        if not is_safe_set(seed):
            continue
        found.clear()
        dfs(list(seed))
        results["constructions"].append({
            "seed": seed,
            "saturated_sizes": [len(s) for s in found],
            "examples": [list(s) for s in found[:3]],
        })
    return results


def analyze_5x5_winning_firsts():
    """5×5 の勝ち初手9点の座標対称性を既知情報から推定し、D4軌道を記述。"""
    # From docs / known: 9 winning first moves on 5x5.
    # Without solver we locate them from any available artifacts.
    # Search results/ and docs for coordinates.
    return {"status": "need artifact coordinates"}


def analyze_depth_pattern():
    """max_search_depth と n の関係を精査。"""
    max_depth = {1: 1, 2: 3, 3: 5, 4: 7, 5: 9, 6: 11, 7: 14, 8: 15, 9: 17}
    # 2n-1 vs 2n
    rows = []
    for n, d in max_depth.items():
        rows.append({
            "n": n,
            "max_depth": d,
            "2n_1": 2 * n - 1,
            "2n": 2 * n,
            "delta_from_2n_1": d - (2 * n - 1),
            "delta_from_2n": d - 2 * n,
            "winner": {1: "F", 2: "F", 3: "F", 4: "S", 5: "F", 6: "F", 7: "S", 8: "S", 9: "F"}[n],
        })
    return rows


def main():
    report = {}

    print("=== A. max_search_depth パターン ===")
    report["depth_pattern"] = analyze_depth_pattern()
    print(json.dumps(report["depth_pattern"], indent=2))

    print("\n=== B. 直線4点組の正確な一致検証 ===")
    coll = {}
    for n in range(2, 9):
        coll[n] = exact_collinear_quads(n)
        print(f"  n={n}: {coll[n]}")
    report["collinear_exact"] = coll

    print("\n=== C. 円上の格子点と共円4点組 ===")
    circ = {}
    for n in range(2, 8):
        print(f"  n={n} ...")
        circ[n] = exact_concyclic_structure(n)
        print(f"    {circ[n]}")
    report["concyclic_exact"] = circ

    print("\n=== D. 4×4 極大安全配置 ===")
    report["maximal_n4"] = maximal_safe_n4()
    print(json.dumps(report["maximal_n4"], indent=2))

    print("\n=== E. 飽和配置の構成試行 (n=3,4,5) ===")
    sat = {}
    for n in (3, 4, 5):
        print(f"  n={n} ...")
        sat[n] = max_safe_upper_bound_construction(n)
        print(json.dumps(sat[n], indent=2)[:800])
    report["saturation_construction"] = sat

    out = OUT / "exploration_report_2.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
