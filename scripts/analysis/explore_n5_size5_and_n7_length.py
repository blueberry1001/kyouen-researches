#!/usr/bin/env python3
"""探索11: 5×5 サイズ5極大4個の記述、禁止数 n=11,12、勝ち初手後の終局。"""
from __future__ import annotations

import json
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from explore_maximal_spectrum import Hypergraph, det4_pts

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "exploration"


def list_small_maximal(n=5, size=5):
    hg = Hypergraph(n)
    found = []

    def rec(chosen: frozenset, start: int):
        if len(chosen) == size:
            if not hg.legal_moves(chosen):
                found.append(tuple(sorted(chosen)))
            return
        if size - len(chosen) > hg.V - start:
            return
        for p in range(start, hg.V):
            if hg.is_safe_with(chosen, p):
                rec(chosen | {p}, p + 1)

    rec(frozenset(), 0)
    # describe each
    rows = []
    for s in found:
        coords = [((i % n, i // n)) for i in s]
        rows.append({"ids": list(s), "xy": coords})
    return {"n": n, "size": size, "count": len(found), "sets": rows}


def forbidden_counts(n):
    hg = Hypergraph(n)
    return {"n": n, "forbidden": hg.n_bad}


def winning_reply_structure_n5():
    """5×5 の勝ち初手 9 点を埋め込む 1 石後の、後手の勝ち返し数を再確認。"""
    # From CYCLE4: WIN first moves → 0 winning replies for opponent
    # This script just lists the 9 cells and their D4 orbits.
    wins = [(2, 0), (1, 1), (3, 1), (0, 2), (2, 2), (4, 2), (1, 3), (3, 3), (2, 4)]
    return {
        "winning_cells": wins,
        "as_ids": [y * 5 + x for x, y in wins],
        "orbits": {
            "center": [(2, 2)],
            "edge_centers": [(2, 0), (0, 2), (4, 2), (2, 4)],
            "interior_diagonal": [(1, 1), (3, 1), (1, 3), (3, 3)],
        },
    }


def main():
    report = {}
    print("=== 5×5 サイズ5極大 4 個 ===", flush=True)
    report["n5_size5"] = list_small_maximal(5, 5)
    for s in report["n5_size5"]["sets"]:
        print(f"  {s['xy']}", flush=True)

    print("\n=== 禁止 4 点組数 n=11,12 (密度延長) ===", flush=True)
    dens = {}
    for n in (11, 12):
        r = forbidden_counts(n)
        import math
        total = math.comb(n * n, 4)
        dens[n] = {
            **r,
            "density": r["forbidden"] / total,
            "density_times_n2": r["forbidden"] / total * n * n,
        }
        print(f"  n={n}: forbidden={r['forbidden']} dens*n^2={dens[n]['density_times_n2']:.3f}", flush=True)
    report["density_ext"] = dens

    report["n5_first_moves"] = winning_reply_structure_n5()
    out = OUT / "exploration_report_11.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
