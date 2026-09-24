#!/usr/bin/env python3
"""探索12: 共線4点組の閉形式、n=10..13 の幾何量、勝敗の外挿制約。"""
from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "exploration"


def collinear_quads_by_primitive_slope(n: int) -> dict:
    """primitive 方向 (dx,dy) (dx>=0, dy 任意, gcd=1) ごとの共線4点組数。"""
    detail = {}
    total = 0
    dirs = set()
    for dx in range(0, n):
        for dy in range(-n + 1, n):
            if dx == 0 and dy <= 0:
                continue
            if dx > 0 and math.gcd(dx, abs(dy)) != 1:
                continue
            if dx == 0 and dy != 1:
                continue
            dirs.add((dx, dy))
    for dx, dy in sorted(dirs):
        seen = set()
        quads = 0
        for x in range(n):
            for y in range(n):
                px, py = x, y
                while 0 <= px - dx < n and 0 <= py - dy < n:
                    px -= dx
                    py -= dy
                if (px, py) in seen:
                    continue
                k = 0
                cx, cy = px, py
                while 0 <= cx < n and 0 <= cy < n:
                    seen.add((cx, cy))
                    k += 1
                    cx += dx
                    cy += dy
                if k >= 4:
                    quads += math.comb(k, 4)
        if quads:
            detail[f"({dx},{dy})"] = quads
            total += quads
    return {"n": n, "total": total, "by_dir": detail}


def collinear_closed_form_value(n: int) -> int:
    """軸・対角・斜辺方向を公式化して合計 (n ≤ 12 で方向は有限)。"""
    # For each primitive (dx,dy), the number of maximal segments with k points
    # in an n x n grid, then sum C(k,4).
    # A segment with step (dx,dy) has k points iff the bounding box of the
    # step run has size (k-1)*|dx| by (k-1)*|dy| fitting in n x n.
    # Number of such segments of length k is (n - (k-1)|dx|) * (n - (k-1)|dy|)
    # for undirected we must not double-count opposite directions — use dx>0
    # or (dx=0, dy=1).
    total = 0
    for dx in range(0, n):
        for dy in range(0, n):
            if dx == 0 and dy != 1:
                continue
            if dy == 0 and dx != 1:
                continue
            if dx > 0 and dy > 0 and math.gcd(dx, dy) != 1:
                continue
            if dx > 0 and dy > 0:
                # two diagonal families: (dx,dy) and (dx,-dy)
                mult = 2
            else:
                mult = 1
            for k in range(4, n + 1):
                span_x = (k - 1) * dx
                span_y = (k - 1) * dy
                if span_x >= n or span_y >= n:
                    break
                count = (n - span_x) * (n - span_y)
                total += mult * count * math.comb(k, 4)
    return total


def geometric_table():
    """n=4..13 の禁止数・密度・F/n^6・共線。"""
    forbidden = {
        4: 194, 5: 826, 6: 2491, 7: 6364, 8: 14564,
        9: 29152, 10: 54441, 11: 95670, 12: 158426,
    }
    collinear = {}
    for n in range(4, 13):
        collinear[n] = collinear_closed_form_value(n)
    rows = []
    for n, f in sorted(forbidden.items()):
        dens = f / math.comb(n * n, 4)
        rows.append({
            "n": n,
            "forbidden": f,
            "collinear": collinear.get(n),
            "concyclic_est": f - collinear[n] if n in collinear else None,
            "density_times_n2": dens * n * n,
            "F_over_n6": f / n ** 6,
        })
    return rows


def winner_extrapolation_constraints():
    """勝敗列 n=1..10 に対して、単純則が全部死んでいることを再整理し、外挿制約を列挙。"""
    winners = {1: "F", 2: "F", 3: "F", 4: "S", 5: "F", 6: "F", 7: "S", 8: "S", 9: "F", 10: "S"}
    K = {1: 1, 2: 3, 3: 5, 4: 7, 5: 9, 6: 11, 7: 14, 8: 15, 9: 17, 10: None}
    return {
        "winners": winners,
        "K_n": K,
        "dead_rules": [
            "n の奇偶",
            "n mod 3,4,5",
            "forbidden(n) mod m (m<=8)",
            "K_n の奇偶 (n=4,8 で反例)",
            "盤面拡大の単調性",
            "勝ち初手密度 (n=5 のみ例外)",
        ],
        "still_open": [
            "modulus 11+ で分離するか",
            "K_n が常に 2n-1 か 2n かの分類 (n=7 のみ 2n)",
            "終局石数スペクトルの奇偶構造と勝敗の同値性 (n<=6 で成立)",
        ],
    }


def main():
    report = {}
    print("=== 共線閉形式の検証 ===", flush=True)
    for n in range(4, 11):
        enum = collinear_quads_by_primitive_slope(n)
        formula = collinear_closed_form_value(n)
        match = enum["total"] == formula
        print(f"  n={n}: enum={enum['total']} formula={formula} match={match} dirs={enum['by_dir']}", flush=True)
        report[f"collinear_n{n}"] = {"enum": enum, "formula": formula, "match": match}

    print("\n=== 幾何テーブル ===", flush=True)
    report["geometry_table"] = geometric_table()
    for r in report["geometry_table"]:
        print(f"  n={r['n']}: F={r['forbidden']} coll={r['collinear']} "
              f"circ~{r['concyclic_est']} F/n6={r['F_over_n6']:.5f} dens*n2={r['density_times_n2']:.4f}", flush=True)

    print("\n=== 勝敗外挿の制約 ===", flush=True)
    report["winner_extrap"] = winner_extrapolation_constraints()
    print(json.dumps(report["winner_extrap"], indent=2, ensure_ascii=False))

    out = OUT / "exploration_report_12.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
