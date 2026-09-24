#!/usr/bin/env python3
"""探索5: 円上格子点公式の検証、共線の閉形式、証明書ゲーム長の抽出。"""
from __future__ import annotations

import itertools
import json
import math
import struct
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "exploration"
OUT.mkdir(parents=True, exist_ok=True)


def count_repr(n):
    if n < 0:
        return 0
    if n == 0:
        return 1
    c = 0
    a = 0
    while a * a <= n:
        b2 = n - a * a
        b = math.isqrt(b2)
        if b * b == b2:
            if a == 0 and b == 0:
                c += 1
            elif a == 0 or b == 0:
                c += 2
            elif a == b:
                c += 4
            else:
                c += 8
        a += 1
    return c


def count_repr_odd(n):
    """A²+B²=n を満たす奇整数ペア (A,B) の個数（符号・順序込み）。"""
    if n <= 0:
        return 0
    c = 0
    limit = math.isqrt(n)
    for a in range(-limit, limit + 1):
        if a % 2 == 0:
            continue
        b2 = n - a * a
        if b2 < 0:
            continue
        b = math.isqrt(b2)
        if b * b == b2 and b % 2 == 1:
            c += 1  # each (a,b) with a,b odd already counted when we iterate all a
    # above counts each (a,b) once for each a; good (includes both signs of b via ±b)
    # Wait: for fixed a, if b!=0 we need both ±b. Let me redo cleanly.
    c = 0
    seen = set()
    for a in range(-limit, limit + 1):
        if a % 2 == 0:
            continue
        b2 = n - a * a
        if b2 < 0:
            continue
        b = math.isqrt(b2)
        if b * b != b2 or b % 2 == 0:
            continue
        for sb in ({b, -b} if b else {0}):
            seen.add((a, sb))
    return len(seen)


def max_circle_points_for_board(n):
    best = 0
    best_info = None
    for i2 in range(-1, 2 * n + 1):
        for j2 in range(-1, 2 * n + 1):
            dist = Counter()
            for x in range(n):
                for y in range(n):
                    d4 = (2 * x - i2) ** 2 + (2 * y - j2) ** 2
                    dist[d4] += 1
            for d4, cnt in dist.items():
                if d4 > 0 and cnt > best:
                    best = cnt
                    best_info = {
                        "center_x2": i2,
                        "center_y2": j2,
                        "r2_x4": d4,
                        "count": cnt,
                        "repr": count_repr(d4),
                        "repr_odd": count_repr_odd(d4),
                    }
    return best, best_info


def collinear_closed_form(n):
    """共線4点組数の閉形式。方向 (dx,dy) primitive ごとに Σ C(k,4)。"""
    total = 0
    detail = {}
    for dx in range(0, n):
        for dy in range(0, n):
            if dx == 0 and dy != 1:
                continue
            if dx == 0:
                pass
            elif dy == 0:
                if dx != 1:
                    continue
            else:
                if math.gcd(dx, dy) != 1:
                    continue
            # count lines with this direction
            seen = set()
            lines_k = []
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
                        lines_k.append(k)
            # also opposite direction is same undirected lines — we only take dy>=0
            # For dy=0, dx=1: horizontal. For dx=0, dy=1: vertical.
            # For dy>0: one diagonal orientation. Need dy<0 as well!
            c4 = sum(math.comb(k, 4) for k in lines_k)
            if c4:
                detail[f"({dx},{dy})"] = {"n_lines_ge4": len(lines_k), "quads": c4, "ks": Counter(lines_k)}
            total += c4
    # second orientation for negative slopes
    for dx in range(1, n):
        for dy in range(1, n):
            if math.gcd(dx, dy) != 1:
                continue
            # direction (dx, -dy)
            seen = set()
            lines_k = []
            for x in range(n):
                for y in range(n):
                    px, py = x, y
                    while 0 <= px - dx < n and 0 <= py + dy < n:
                        px -= dx
                        py += dy
                    if (px, py) in seen:
                        continue
                    k = 0
                    cx, cy = px, py
                    while 0 <= cx < n and 0 <= cy < n:
                        seen.add((cx, cy))
                        k += 1
                        cx += dx
                        cy -= dy
                    if k >= 4:
                        lines_k.append(k)
            c4 = sum(math.comb(k, 4) for k in lines_k)
            if c4:
                detail[f"({dx},{-dy})"] = {"n_lines_ge4": len(lines_k), "quads": c4, "ks": Counter(lines_k)}
            total += c4
    return total, detail


def parse_cert_stone_histogram(path: Path, board_n: int):
    """KYOENC3 バイナリから石数ヒストグラムと witness 鎖長を抽出。

    形式不明の場合は None。night-research の cert パーサを参考に。
    """
    if not path.exists():
        return None
    data = path.read_bytes()
    # try to detect header
    return {"size_bytes": len(data), "magic": data[:8].decode("latin1", errors="replace")}


def look_for_cert_parsers():
    hits = []
    for p in (ROOT / "night-research").glob("*.py"):
        t = p.read_text(encoding="utf-8", errors="replace")
        if "cert" in t.lower() and ("node" in t.lower() or "witness" in t.lower() or "KYOENC" in t):
            hits.append(p.name)
    for p in (ROOT / "scripts").rglob("*.py"):
        t = p.read_text(encoding="utf-8", errors="replace")
        if "KYOENC" in t or "witness" in t.lower() and "rank" in t.lower():
            hits.append(str(p.relative_to(ROOT)))
    return hits


def collinear_axis_formula(n):
    """軸平行と対角だけの閉形式（n≤6 で全て）。"""
    # horizontal + vertical: 2 * n * C(n, 4)
    axis = 2 * n * math.comb(n, 4) if n >= 4 else 0
    # main diagonals slope 1: lengths n, n-1, n-1, n-2, n-2, ..., 1,1
    # k points on diagonal: number of diags with k points is 2 for k<n, 1 for k=n
    diag1 = 0
    for k in range(4, n + 1):
        multiplicity = 1 if k == n else 2
        diag1 += multiplicity * math.comb(k, 4)
    return {"axis": axis, "diag_pm1": 2 * diag1, "sum_if_only_these": axis + 2 * diag1}


def main():
    report = {}

    print("=== A. 円上最大格子点数の公式候補検証 (n=2..20) ===")
    rows = []
    for n in range(2, 21):
        best, info = max_circle_points_for_board(n)
        formula = 4 * (n // 4 + 1)
        rows.append({
            "n": n,
            "max_points": best,
            "formula_4_floor_n4_plus_1": formula,
            "match": best == formula,
            "witness": info,
        })
        print(f"  n={n:2d}: max={best:2d} formula={formula:2d} match={best==formula}  "
              f"N={info['r2_x4']} odd_repr={info['repr_odd']} center=({info['center_x2']}/2,{info['center_y2']}/2)")
    report["max_circle_formula"] = rows
    report["formula_holds_2_to_20"] = all(r["match"] for r in rows)

    print("\n=== B. 共線4点組の閉形式 (軸+対角 vs 完全) ===")
    for n in range(4, 9):
        total, detail = collinear_closed_form(n)
        simple = collinear_axis_formula(n)
        print(f"  n={n}: complete={total}  axis+diag={simple['sum_if_only_these']}  "
              f"delta={total - simple['sum_if_only_these']}")
        print(f"       detail keys={list(detail.keys())}")
    report["collinear_formula_note"] = "axis+diagonal complete for n<=6; slope 2 family starts at n=7"

    print("\n=== C. 証明書パーサ探索 ===")
    report["cert_parsers"] = look_for_cert_parsers()
    print(f"  {report['cert_parsers']}")

    # try reading a small cert
    for name in ["kyouen-3x3.cert", "kyouen-4x4.cert", "kyouen-5x5.cert"]:
        p = ROOT / "night-research" / name
        if p.exists():
            info = parse_cert_stone_histogram(p, 0)
            print(f"  {name}: {info}")
            report[f"probe_{name}"] = info

    out = OUT / "exploration_report_5.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
