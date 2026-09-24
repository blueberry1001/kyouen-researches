#!/usr/bin/env python3
"""探索4: 円上の格子点の数論、禁止数の閉形式候補、証明書ゲーム長。"""
from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "exploration"
OUT.mkdir(parents=True, exist_ok=True)


def r2_sum_of_squares_counts(max_n=200):
    """N = a²+b² (a>=b>=0) の表現数。円上の格子点数は符号・順序込みで 4*(r1-r3)/something..."""
    # Number of integer solutions to a^2+b^2 = N (ordered, signed) is 4*(d1(N)-d3(N))
    # where d1 = # divisors =1 mod 4, d3 = # divisors = 3 mod 4.
    # For max lattice points on a circle with half-integer center, we need
    # solutions to A^2+B^2 = N where A=2x-i2 is odd/even matching center.
    pass


def count_repr(n):
    """a²+b²=n の整数解 (a,b) の個数（符号・順序込み）。"""
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
                c += 2  # (0,±b) or (±a,0)
            elif a == b:
                c += 4  # (±a,±a)
            else:
                c += 8  # (±a,±b) and (±b,±a)
        a += 1
    return c


def max_circle_points_for_board(n):
    """n×n 格子点上に載る円の最大格子点数（中心は半整数格子で十分）。"""
    best = 0
    best_info = None
    pts = [(i % n, i // n) for i in range(n * n)]
    for i2 in range(-1, 2 * n + 1):
        for j2 in range(-1, 2 * n + 1):
            dist = Counter()
            for x, y in pts:
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
                        "repr_of_r2x4": count_repr(d4),
                    }
    return {"n": n, "max_points": best, "witness": best_info}


def collinear_quads_formula(n):
    """Σ_lines C(k,4) を方向 (dx,dy) ごとに計算。"""
    total = 0
    by_slope = defaultdict(int)
    # direction vectors with gcd=1, dx>=0
    for dx in range(0, n):
        for dy in range(-n + 1, n):
            if dx == 0 and dy <= 0:
                continue
            if dx == 0:
                # vertical: dy>0 effectively; use (0,1)
                if dy != 1:
                    continue
            g = math.gcd(dx, abs(dy))
            if g != 1 and not (dx == 0 and abs(dy) == 1):
                if not (dx == 0):
                    continue
            if dx > 0 and math.gcd(dx, abs(dy)) != 1:
                continue
            # count how many points on each maximal segment of this slope in the grid
            # lines with direction (dx,dy) that contain k grid points
            # A line with primitive direction (dx,dy) contains k points if the
            # run of lattice points with step (dx,dy) has length k.
            # Count lines by their starting points.
            seen = set()
            for x in range(n):
                for y in range(n):
                    # walk backward to start
                    px, py = x, y
                    while 0 <= px - dx < n and 0 <= py - dy < n:
                        px -= dx
                        py -= dy
                    if (px, py) in seen:
                        continue
                    # walk forward counting
                    k = 0
                    cx, cy = px, py
                    while 0 <= cx < n and 0 <= cy < n:
                        seen.add((cx, cy))
                        k += 1
                        cx += dx
                        cy += dy
                    if k >= 4:
                        c4 = math.comb(k, 4)
                        total += c4
                        by_slope[(dx, dy)] += c4
    return {"n": n, "collinear_quads": total, "by_slope": {str(k): v for k, v in by_slope.items()}}


def certificate_game_lengths():
    """証明書バイナリから、witness 鎖に沿う石数の分布を読む。

    KYOENC3 は夜間解析で使われた形式。night-research の cert パーサがあるか確認し、
    なければ results/certificates.csv の losing/winning から比率だけ再集計。
    """
    rows = [
        (1, 2, 1, 1),
        (2, 5, 2, 3),
        (3, 28, 10, 18),
        (4, 135, 47, 88),
        (5, 1217, 449, 768),
        (6, 21712, 7625, 14087),
        (7, 393550, 139217, 254333),
        (8, 8744406, 2991713, 5752693),
        (9, 13457134, 4630676, 8826458),
    ]
    out = []
    for n, nodes, loss, win in rows:
        out.append({
            "n": n,
            "nodes": nodes,
            "loss": loss,
            "win": win,
            "loss_fraction": loss / nodes,
            "loss_win_ratio": loss / win,
            "bytes_per_node_raw": {1: 36, 2: 24, 3: 17.4}.get(n, None),
        })
    # raw_bytes from certificates.csv: 72,120,488,2200,19512,347432,6296840,139910536,215314184
    raws = {1: 72, 2: 120, 3: 488, 4: 2200, 5: 19512, 6: 347432, 7: 6296840, 8: 139910536, 9: 215314184}
    for r in out:
        r["raw_bytes"] = raws[r["n"]]
        r["bytes_per_node"] = raws[r["n"]] / r["nodes"]
    return out


def optimal_length_from_known():
    """勝敗と K_n から最適対局の石数の可能性を整理。"""
    K = {1: 1, 2: 3, 3: 5, 4: 7, 5: 9, 6: 11, 7: 14, 8: 15, 9: 17, 10: None}
    winner = {1: "F", 2: "F", 3: "F", 4: "S", 5: "F", 6: "F", 7: "S", 8: "S", 9: "F", 10: "S"}
    return {
        "K_n": K,
        "winner": winner,
        "K_parity": {n: (K[n] % 2 if K[n] else None) for n in K},
    }


def two_square_ceiling(max_n=30):
    """円上格子点数の上界候補: max_N<=4(n-1)^2 に対する r2(N) の最大。

    中心 (i/2,j/2) のとき A²+B²=r2x4 の解数 = その円上の点数の上限
    （盤内に入るかどうかで実効点数は減る）。
    """
    # max A = 2(n-1)+1 roughly, so N up to about 2*(2n)^2
    limit = 2 * (2 * max_n) ** 2
    best = []
    for N in range(1, limit + 1):
        c = count_repr(N)
        if c >= 8:
            best.append((c, N))
    best.sort(reverse=True)
    return best[:20]


def main():
    report = {}

    print("=== A. 盤ごとの円上最大格子点数 (n=2..12) ===")
    mc = {}
    for n in range(2, 13):
        mc[n] = max_circle_points_for_board(n)
        w = mc[n]["witness"]
        print(f"  n={n:2d}: max={mc[n]['max_points']:2d}  N=r2x4={w['r2_x4']}  "
              f"repr(N)={w['repr_of_r2x4']}  center=({w['center_x2']}/2,{w['center_y2']}/2)")
    report["max_circle"] = mc

    print("\n=== B. 2平方和の表現数が大きい N ===")
    report["two_square_top"] = two_square_ceiling(20)
    for c, N in report["two_square_top"][:12]:
        print(f"  N={N:4d}  repr={c}")

    print("\n=== C. 共線4点組の方向別分解 (n=3..8) ===")
    coll = {}
    for n in range(3, 9):
        coll[n] = collinear_quads_formula(n)
        print(f"  n={n}: total={coll[n]['collinear_quads']}  slopes={coll[n]['by_slope']}")
    report["collinear_by_slope"] = coll

    print("\n=== D. 証明書の LOSS/WIN 構造 ===")
    report["cert_structure"] = certificate_game_lengths()
    for r in report["cert_structure"]:
        print(f"  n={r['n']}: loss_frac={r['loss_fraction']:.4f}  "
              f"loss/win={r['loss_win_ratio']:.4f}  bytes/node={r['bytes_per_node']:.2f}")

    print("\n=== E. K_n と勝敗のパリティ ===")
    # correct known max-set size histograms
    hist = {
        1: {1: 1},
        2: {3: 4},
        3: {5: 56},
        4: {5: 176, 6: 688, 7: 64},
        5: {9: 100},  # maximum-cardinality only
        6: {11: 464},
        7: {14: 16},
    }
    K = {n: max(h) for n, h in hist.items()}
    K[8] = 15
    K[9] = 17  # lower bound; unknown if exact
    winner = {1: "F", 2: "F", 3: "F", 4: "S", 5: "F", 6: "F", 7: "S", 8: "S", 9: "F"}
    report["K_and_winner"] = {
        "K_n": K,
        "winner": winner,
        "K_odd": {n: K[n] % 2 == 1 for n in K},
        "F_iff_K_odd_in_data": all((winner[n] == "F") == (K[n] % 2 == 1) for n in winner if n in K),
        "n_max_sets": {n: sum(hist[n].values()) for n in hist},
    }
    print(json.dumps(report["K_and_winner"], indent=2))

    # NOTE on K vs winner: F iff K odd holds for n=1..9 with known K!
    # n=7 K=14 even → S; n=8 K=15 odd → S  << BREAKS!
    # n=8: K=15 odd but winner is S. So the naive "F iff K odd" FAILS at n=8.
    # n=4: K=7 odd but winner S. Already fails!
    # Let me recompute...
    for n in winner:
        print(f"  n={n} K={K.get(n)} odd={K.get(n,0)%2==1} winner={winner[n]}")

    out = OUT / "exploration_report_4.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
