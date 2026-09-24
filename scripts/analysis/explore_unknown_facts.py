#!/usr/bin/env python3
"""非自明な事実の系統的探索。

禁止4点組の幾何分類、勝敗列の数論、勝ち初手のパターンを機械的に調べる。
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


def det3(m):
    return (
        m[0, 0] * (m[1, 1] * m[2, 2] - m[1, 2] * m[2, 1])
        - m[0, 1] * (m[1, 0] * m[2, 2] - m[1, 2] * m[2, 0])
        + m[0, 2] * (m[1, 0] * m[2, 1] - m[1, 1] * m[2, 0])
    )


def det4(m):
    return (
        m[0, 0] * det3(m[1:, 1:])
        - m[0, 1] * det3(m[[1, 2, 3]][:, [0, 2, 3]])
        + m[0, 2] * det3(m[[1, 2, 3]][:, [0, 1, 3]])
        - m[0, 3] * det3(m[1:, :3])
    )


def area2(a, b, c):
    """三角形の符号付き面積の2倍。"""
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def is_collinear(pts):
    a, b, c, d = pts
    return area2(a, b, c) == 0 and area2(a, b, d) == 0


def circumcircle_params(p, q, r):
    """3点を通る円の (cx*2, cy*2, r2*4) を整数で返す。存在しなければ None。"""
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
    # center = (ux/d, uy/d)
    # r2 = ((ax-ux/d)^2 + (ay-uy/d)^2)
    # 4*r2 * d^2 = (2*ax*d - 2*ux)^2 + (2*ay*d - 2*uy)^2
    # keep (2*cx_num, 2*cy_num, 4*r2*d^2 / 4?) simpler: store (ux, uy, d, and check 4th point)
    return (ux, uy, d, a2, ax, ay)


def on_same_circle(p, q, r, s):
    """4点が同一円周上か（共線は除く想定の呼び出し側で扱う）。整数演算のみ。"""
    params = circumcircle_params(p, q, r)
    if params is None:
        return False
    ux, uy, d, _, _, _ = params
    # s が同じ円: |s - c|^2 = |p - c|^2, c = (ux/d, uy/d)
    # (sx*d - ux)^2 + (sy*d - uy)^2 == (px*d - ux)^2 + (py*d - uy)^2
    sx, sy = s
    px, py = p
    ls = (sx * d - ux) ** 2 + (sy * d - uy) ** 2
    lp = (px * d - ux) ** 2 + (py * d - uy) ** 2
    return ls == lp


def classify_quad(pts):
    if is_collinear(pts):
        return "collinear"
    if on_same_circle(pts[0], pts[1], pts[2], pts[3]):
        return "concyclic"
    return "neither"


def points_of(n):
    return [(i % n, i // n) for i in range(n * n)]


def enumerate_forbidden(n):
    pts = points_of(n)
    collinear = []
    concyclic = []
    for idx in itertools.combinations(range(n * n), 4):
        q = [pts[i] for i in idx]
        kind = classify_quad(q)
        if kind == "collinear":
            collinear.append(idx)
        elif kind == "concyclic":
            concyclic.append(idx)
    return collinear, concyclic


def line_key(pts):
    """通る直線を整数係数 (A,B,C) の正規形で返す。 Ax+By+C=0, gcd(|A|,|B|,|C|)=1, A>0 or (A=0 and B>0)。"""
    a, b, c, d = pts
    # use a,b as direction; c should be on line
    A = b[1] - a[1]
    B = a[0] - b[0]
    C = a[0] * b[1] - a[1] * b[0]  # wait: Ax+By = A*ax+B*ay = (b1-a1)*ax + (a0-b0)*ay
    # actually C should satisfy A*x+B*y+C=0 => C = -(A*ax+B*ay)
    C = -(A * a[0] + B * a[1])
    g = math.gcd(math.gcd(abs(A), abs(B)), abs(C))
    if g:
        A, B, C = A // g, B // g, C // g
    if A < 0 or (A == 0 and B < 0):
        A, B, C = -A, -B, -C
    return (A, B, C)


def circle_key(p, q, r):
    """円を整数正規形で返す。中心 (ux/d, uy/d) と半径2乗。"""
    params = circumcircle_params(p, q, r)
    if params is None:
        return None
    ux, uy, d, a2, ax, ay = params
    # r2 * d^2 = (ax*d - ux)^2 + (ay*d - uy)^2  ... wait center is (ux/d, uy/d)
    # Actually standard formula: center = (ux/d, uy/d) where
    # ux = a2*(by-cy)+..., uy = a2*(cx-bx)+..., d = 2*(...)
    # r2_num = (ax*d - ux)^2 + (ay*d - uy)^2  equals r2 * d^2
    r2_num = (ax * d - ux) ** 2 + (ay * d - uy) ** 2
    # normalize sign of d
    if d < 0:
        ux, uy, d = -ux, -uy, -d
    g = math.gcd(math.gcd(abs(ux), abs(uy)), math.gcd(abs(d), abs(r2_num)))
    # don't over-reduce r2_num vs d; use gcd of all
    if g:
        ux, uy, d, r2_num = ux // g, uy // g, d // g, r2_num // (g * g) if (g * g) and r2_num % (g * g) == 0 else r2_num
    return (ux, uy, d, r2_num)


def analyze_geometry(n):
    collinear, concyclic = enumerate_forbidden(n)
    pts = points_of(n)

    # collinear lines: all 4-subsets on each line
    line_groups = defaultdict(list)
    for idx in collinear:
        q = [pts[i] for i in idx]
        line_groups[line_key(q)].append(idx)

    # circle groups among concyclic
    circle_groups = defaultdict(list)
    ungrouped = 0
    for idx in concyclic:
        q = [pts[i] for i in idx]
        key = circle_key(q[0], q[1], q[2])
        if key is None:
            ungrouped += 1
            continue
        circle_groups[key].append(idx)

    # lines with >=4 lattice points
    all_lines = defaultdict(list)
    for i in range(n * n):
        for j in range(i + 1, n * n):
            a, b = pts[i], pts[j]
            A = b[1] - a[1]
            B = a[0] - b[0]
            C = -(A * a[0] + B * a[1])
            g = math.gcd(math.gcd(abs(A), abs(B)), abs(C) or 1)
            if g:
                A, B, C = A // g, B // g, C // g
            if A < 0 or (A == 0 and B < 0):
                A, B, C = -A, -B, -C
            all_lines[(A, B, C)].append(i)

    line_sizes = Counter(len(v) for v in all_lines.values())
    collinear_sizes = Counter(len(v) for v in line_groups.values())

    # expected collinear quads from line sizes
    expected_coll = 0
    for size in line_sizes.values():
        if size >= 4:
            expected_coll += math.comb(size, 4)

    return {
        "n": n,
        "n_collinear_quads": len(collinear),
        "n_concyclic_quads": len(concyclic),
        "n_forbidden": len(collinear) + len(concyclic),
        "n_distinct_forbidden_lines": len(line_groups),
        "n_distinct_forbidden_circles": len(circle_groups),
        "line_size_hist": dict(sorted(line_sizes.items())),
        "collinear_line_size_hist": dict(sorted(collinear_sizes.items())),
        "expected_collinear_from_lines": expected_coll,
        "collinear_match": expected_coll == len(collinear),
        "circle_group_size_hist": dict(sorted(Counter(len(v) for v in circle_groups.values()).items())),
        "max_points_on_line": max(line_sizes) if line_sizes else 0,
        "ungrouped_concyclic": ungrouped,
    }


def analyze_known_sequences():
    """既知の完全分類データから数論パターンを抽出する。"""
    winners = {1: "F", 2: "F", 3: "F", 4: "S", 5: "F", 6: "F", 7: "S", 8: "S", 9: "F", 10: "S"}
    first_win_count = {1: 1, 2: 4, 3: 9, 4: 0, 5: 9, 6: 36, 7: 0, 8: 0, 9: 81, 10: 0}
    forbidden = {1: 0, 2: 1, 3: 14, 4: 194, 5: 826, 6: 2491, 7: 6364, 8: 14564, 9: 29152, 10: 54441}
    cert_nodes = {1: 2, 2: 5, 3: 28, 4: 135, 5: 1217, 6: 21712, 7: 393550, 8: 8744406, 9: 13457134}
    search_states = {1: 2, 2: 5, 3: 28, 4: 207, 5: 5775, 6: 51958, 7: 4060657, 8: 35961745, 9: 57078016}

    facts = {}

    # winning first move counts: look for squares / triangular etc
    fw = first_win_count
    facts["first_win_counts"] = fw
    facts["first_win_is_square_when_first"] = {
        n: (fw[n] == n * n) for n in fw if winners.get(n) == "F"
    }
    facts["first_win_is_full_board"] = {
        n: fw[n] == n * n for n in fw
    }
    facts["density_of_winning_first_moves"] = {
        n: fw[n] / (n * n) for n in fw
    }

    # forbidden count ratios
    ratios = {}
    for n in range(2, 11):
        ratios[n] = forbidden[n] / forbidden[n - 1] if forbidden[n - 1] else None
    facts["forbidden_growth_ratio"] = ratios

    # forbidden / n^4  (asymptotic density of bad 4-sets)
    density = {n: forbidden[n] / math.comb(n * n, 4) if n >= 4 else None for n in range(4, 11)}
    facts["forbidden_density_of_all_4sets"] = density

    # search_states / cert_nodes
    facts["search_to_cert_ratio"] = {
        n: search_states[n] / cert_nodes[n] for n in cert_nodes
    }

    # winners modulo small periods
    seq = "".join(winners[n] for n in range(1, 11))
    facts["winner_sequence_n1_to_n10"] = seq

    # max search depth from results.csv: 1,3,5,7,9,11,14,15,17
    max_depth = {1: 1, 2: 3, 3: 5, 4: 7, 5: 9, 6: 11, 7: 14, 8: 15, 9: 17}
    facts["max_search_depth"] = max_depth
    facts["max_search_depth_minus_2n"] = {n: max_depth[n] - 2 * n for n in max_depth}
    # stones placed at max depth = depth of game tree? notes say 17 stones on 9x9 is terminal
    # results max_search_depth for 9 is 17 — matches 17-stone terminal!
    facts["max_depth_equals_terminal_stones_9x9"] = max_depth[9] == 17

    return facts


def analyze_first_move_orbits_9x9():
    """9×9 の勝ち初手コスト (visited) と D4 軌道構造。"""
    path = ROOT / "night-research" / "first-moves-9x9.csv"
    rows = []
    if not path.exists():
        return {"error": "missing first-moves-9x9.csv"}
    with path.open(encoding="utf-8") as f:
        header = f.readline()
        for line in f:
            parts = line.strip().split(",")
            if len(parts) < 8:
                continue
            a, b, first_id, verdict = int(parts[0]), int(parts[1]), int(parts[2]), parts[3]
            states = int(parts[5])
            seconds = float(parts[8])
            rows.append({
                "a": a,
                "b": b,
                "id": first_id,
                "verdict": verdict,
                "states": states,
                "seconds": seconds,
                "dist_center": abs(a - 4) + abs(b - 4),
                "max_norm": max(abs(a - 4), abs(b - 4)),
                "is_center": (a, b) == (4, 4),
                "is_corner_class": (a, b) == (0, 0),
                "on_diag": a == b or a + b == 8,
            })
    rows.sort(key=lambda r: -r["states"])
    summary = {
        "n_rows": len(rows),
        "all_win": all(r["verdict"] == "FIRST_WIN" for r in rows),
        "states_min": min(r["states"] for r in rows),
        "states_max": max(r["states"] for r in rows),
        "states_median": float(np.median([r["states"] for r in rows])),
        "by_max_norm": {},
        "heaviest": rows[:5],
        "lightest": rows[-5:],
    }
    by = defaultdict(list)
    for r in rows:
        by[r["max_norm"]].append(r["states"])
    for k in sorted(by):
        summary["by_max_norm"][k] = {
            "n": len(by[k]),
            "median_states": float(np.median(by[k])),
            "min": min(by[k]),
            "max": max(by[k]),
        }
    return summary


def analyze_winner_vs_forbidden():
    """勝敗と禁止4点組数の関係。"""
    # hypothesize: second win when forbidden is in some residue class
    forbidden = {1: 0, 2: 1, 3: 14, 4: 194, 5: 826, 6: 2491, 7: 6364, 8: 14564, 9: 29152, 10: 54441}
    winners = {1: "F", 2: "F", 3: "F", 4: "S", 5: "F", 6: "F", 7: "S", 8: "S", 9: "F", 10: "S"}
    out = {"by_n": {}}
    for n in range(1, 11):
        f = forbidden[n]
        out["by_n"][n] = {
            "winner": winners[n],
            "forbidden": f,
            "forbidden_mod_3": f % 3,
            "forbidden_mod_4": f % 4,
            "forbidden_mod_5": f % 5,
            "forbidden_mod_7": f % 7,
            "n_mod_3": n % 3,
            "n_mod_4": n % 4,
            "is_square": int(math.isqrt(n)) ** 2 == n,
            "is_prime": n >= 2 and all(n % d for d in range(2, int(math.sqrt(n)) + 1)),
        }
    # check if any single modulus separates F and S
    for m in (2, 3, 4, 5, 6, 7, 8):
        classes = defaultdict(set)
        for n, w in winners.items():
            classes[forbidden[n] % m].add(w)
        out[f"forbidden_mod_{m}_separates"] = {
            str(k): sorted(v) for k, v in classes.items()
        }
        out[f"forbidden_mod_{m}_is_pure"] = all(len(v) == 1 for v in classes.values())

    # n-based classes
    for m in (2, 3, 4, 5):
        classes = defaultdict(set)
        for n, w in winners.items():
            classes[n % m].add(w)
        out[f"n_mod_{m}_separates"] = {str(k): sorted(v) for k, v in classes.items()}
        out[f"n_mod_{m}_is_pure"] = all(len(v) == 1 for v in classes.values())

    return out


def analyze_saturation_geometry(n, sample_terminal_stones=None):
    """小盤面で、極大安全配置 (飽和) のサイズ分布を完全列挙する。

    n<=4 なら完全、n=5 はランダムサンプル。
    """
    pts = points_of(n)
    # precompute dangerous masks for each pair-of-pairs? better: for each 4-set
    all_quads = list(itertools.combinations(range(n * n), 4))
    bad = []
    for idx in all_quads:
        q = [pts[i] for i in idx]
        if is_collinear(q) or on_same_circle(q[0], q[1], q[2], q[3]):
            bad.append(idx)
    bad_set = set(bad)

    def is_safe(S):
        S = tuple(sorted(S))
        if len(S) < 4:
            return True
        for q in itertools.combinations(S, 4):
            if q in bad_set:
                return False
        return True

    # For n<=3, enumerate all safe sets and find maximal ones
    if n * n > 16:
        return {"n": n, "skipped": "board too large for full enum"}

    maximal = []
    all_safe_counts = Counter()
    N = n * n
    # enumerate by increasing size using DFS
    def dfs(chosen, start):
        if chosen:
            all_safe_counts[len(chosen)] += 1
            # maximal if no extension
            can_extend = False
            for p in range(start if False else 0, N):
                if p in chosen:
                    continue
                # try add
                trial = list(chosen) + [p]
                ok = True
                for q in itertools.combinations(sorted(trial), 4):
                    if q in bad_set:
                        ok = False
                        break
                if ok:
                    can_extend = True
                    break
            if not can_extend:
                maximal.append(tuple(sorted(chosen)))
        if len(chosen) >= N:
            return
        for p in range(0, N):
            if p in chosen:
                continue
            if chosen and p < chosen[-1]:
                continue  # combinations order
            trial = list(chosen) + [p]
            ok = True
            for q in itertools.combinations(sorted(trial), 4):
                if q in bad_set:
                    ok = False
                    break
            if ok:
                dfs(trial, p + 1)

    # simpler: iterate all subsets for tiny boards
    if N <= 9:  # n<=3
        for r in range(1, N + 1):
            for S in itertools.combinations(range(N), r):
                if not is_safe(S):
                    continue
                all_safe_counts[r] += 1
                # maximal?
                maximal_flag = True
                for p in range(N):
                    if p in S:
                        continue
                    if is_safe(S + (p,)):
                        maximal_flag = False
                        break
                if maximal_flag:
                    maximal.append(S)

    max_sizes = Counter(len(S) for S in maximal)
    return {
        "n": n,
        "n_points": N,
        "n_bad_quads": len(bad_set),
        "safe_set_size_hist": dict(sorted(all_safe_counts.items())),
        "n_maximal_safe": len(maximal),
        "maximal_size_hist": dict(sorted(max_sizes.items())),
        "max_safe_size": max(max_sizes) if max_sizes else 0,
        "min_maximal_size": min(max_sizes) if max_sizes else 0,
    }


def main():
    report = {}

    print("=== 1. 既知シーケンスの数論 ===")
    report["sequences"] = analyze_known_sequences()
    seq = report["sequences"]
    print(json.dumps(seq, indent=2, ensure_ascii=False, default=str))

    print("\n=== 2. 禁止4点組の幾何分類 (n=2..8) ===")
    geom = {}
    for n in range(2, 9):
        print(f"  n={n} ...")
        geom[n] = analyze_geometry(n)
        g = geom[n]
        print(f"    collinear={g['n_collinear_quads']} concyclic={g['n_concyclic_quads']} "
              f"lines={g['n_distinct_forbidden_lines']} circles={g['n_distinct_forbidden_circles']} "
              f"match={g['collinear_match']}")
    report["geometry"] = geom

    print("\n=== 3. 9×9 勝ち初手コスト ===")
    report["first_moves_9x9"] = analyze_first_move_orbits_9x9()
    print(json.dumps(report["first_moves_9x9"], indent=2, ensure_ascii=False, default=str))

    print("\n=== 4. 勝敗 vs 禁止数の剰余 ===")
    report["winner_vs_forbidden"] = analyze_winner_vs_forbidden()
    print(json.dumps(report["winner_vs_forbidden"], indent=2, ensure_ascii=False, default=str))

    print("\n=== 5. 小盤面の極大安全配置 ===")
    sat = {}
    for n in (2, 3, 4):
        print(f"  n={n} ...")
        sat[n] = analyze_saturation_geometry(n)
        print(json.dumps(sat[n], indent=2, ensure_ascii=False, default=str))
    report["saturation"] = sat

    out_path = OUT / "exploration_report.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
