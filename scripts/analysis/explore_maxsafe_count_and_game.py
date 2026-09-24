#!/usr/bin/env python3
"""探索8: 最大安全配置の個数列、n=5 勝ち初手の代数構造、禁止密度の漸近。"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "exploration"
OUT.mkdir(parents=True, exist_ok=True)


def maxsafe_count_sequence():
    """既知の最大安全配置数と最大サイズ。出典: night-research CYCLE5/6/8。"""
    return {
        "n": [1, 2, 3, 4, 5, 6, 7, 8],
        "K_n": [1, 3, 5, 7, 9, 11, 14, 15],
        "n_maximum_sets": [1, 4, 56, 64, 100, 464, 16, None],
        "n_all_maximal_sets": [1, 4, 56, 928, 16860, 464, 16, None],
        "note": "n=6 は最大サイズ 11 のみ (Cycle5)。n=7 は 14 のみ 16 個。n=5 は最大 9 が 100 個だが極大全体は 16860。",
        "min_det_of_max_sets": {3: 4, 4: 3, 5: 3, 6: 3, 7: 2},
    }


def five_by_five_structure():
    """5×5 勝ち初手 = 偶部分格子 \\ 角、の代数的記述。"""
    wins = []
    losses = []
    for y in range(5):
        for x in range(5):
            if (x + y) % 2 == 0 and not (x in (0, 4) and y in (0, 4)):
                wins.append((x, y))
            else:
                losses.append((x, y))
    return {
        "winning_cells": wins,
        "n_wins": len(wins),
        "n_losses": len(losses),
        "char_fn": "(x+y even) and not (x in {0,4} and y in {0,4})",
        "gaussian_integers": "wins = {a+bi : a,b in 0..4, a+b even} minus corners",
        "relation_to_D4": "D4 orbits: center 1 WIN, edge-centers 4 WIN, interior-diag 4 WIN, corners 4 LOSS, edge-noncenter 8 LOSS, interior-axial 4 LOSS",
    }


def forbidden_density_asymptotic():
    """forbidden / C(n²,4) の漸近。既知値から log-log 傾きを推定。"""
    forbidden = {4: 194, 5: 826, 6: 2491, 7: 6364, 8: 14564, 9: 29152, 10: 54441}
    rows = []
    for n, f in forbidden.items():
        total = math.comb(n * n, 4)
        dens = f / total
        rows.append({
            "n": n,
            "forbidden": f,
            "all_4sets": total,
            "density": dens,
            "density_times_n2": dens * n * n,
            "density_times_n3": dens * n ** 3,
        })
    # fit dens ~ c * n^{-alpha}
    import math as m
    xs = [m.log(r["n"]) for r in rows]
    ys = [m.log(r["density"]) for r in rows]
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = sum((x - mx) ** 2 for x in xs)
    slope = num / den
    return {
        "rows": rows,
        "loglog_slope_alpha": -slope,
        "interpretation": "density ~ c * n^{-alpha}; alpha≈2 means forbidden = Θ(n^4 / n^2) = Θ(n^2) wait density=C(n^2,4)~n^8/24, forbidden~n^8/24 * n^{-alpha}",
        "forbidden_growth_vs_n4": {
            n: forbidden[n] / n ** 4 for n in forbidden
        },
        "forbidden_growth_vs_n5": {
            n: forbidden[n] / n ** 5 for n in forbidden
        },
    }


def collinear_general_formula_n():
    """共線 4 点組の方向 (dx,dy) 一般式の骨格。"""
    return {
        "primitive_directions_needed_for_4points": "min box side for 4 collinear with step (dx,dy) is 3*|dx|+1 by 3*|dy|+1, so n >= 3*max(|dx|,|dy|)+1 roughly",
        "first_slope_beyond_axis_diag": {
            "slope_2_family": "n>=7 (step (1,2) or (2,1))",
            "slope_3_family": "n>=10 (step (1,3) or (3,1))",
        },
        "axis_formula": "2 * n * C(n,4)",
        "diag_formula": "2 * sum_{k=4..n} m(k) * C(k,4) where m(n)=1, m(k<n)=2",
    }


def winner_vs_maximal_sizes():
    """極大安全サイズの集合と勝敗の関係。"""
    # From CYCLE1 + CYCLE5
    data = {
        1: {"maximal_sizes": [1], "K": 1, "winner": "F"},
        2: {"maximal_sizes": [3], "K": 3, "winner": "F"},
        3: {"maximal_sizes": [5], "K": 5, "winner": "F"},
        4: {"maximal_sizes": [5, 6, 7], "K": 7, "winner": "S"},
        5: {"maximal_sizes": [5, 6, 7, 8, 9], "K": 9, "winner": "F"},
        6: {"maximal_sizes": [11], "K": 11, "winner": "F"},
        7: {"maximal_sizes": [14], "K": 14, "winner": "S"},
    }
    notes = []
    for n, d in data.items():
        sizes = d["maximal_sizes"]
        has_odd = any(s % 2 == 1 for s in sizes)
        has_even = any(s % 2 == 0 for s in sizes)
        notes.append({
            "n": n,
            "sizes": sizes,
            "winner": d["winner"],
            "has_odd_terminal": has_odd,
            "has_even_terminal": has_even,
            "winner_F_implies_odd_available": (d["winner"] == "F") == has_odd if d["winner"] == "F" else None,
            "locked_parity": not (has_odd and has_even),
        })
    return notes


def main():
    report = {
        "maxsafe": maxsafe_count_sequence(),
        "n5": five_by_five_structure(),
        "density": forbidden_density_asymptotic(),
        "collinear_formula": collinear_general_formula_n(),
        "winner_vs_maximal": winner_vs_maximal_sizes(),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    out = OUT / "exploration_report_8.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"Wrote {out}", file=__import__("sys").stderr)


if __name__ == "__main__":
    main()
