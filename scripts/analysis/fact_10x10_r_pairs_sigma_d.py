#!/usr/bin/env python3
"""R の 28 二石ペアについて Σd と既知勝敗を突合する。"""
from __future__ import annotations

import csv
import itertools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORBITS = ROOT / "research" / "exploration" / "fact_10x10_two_stone_orbits.json"

# From docs: 5 immediate WIN; F-E claims 2 LOSS: {90,61}, {61,66}
# 90,91 is WIN (THREE_STONE_SUBSETS.md)
KNOWN = {
    frozenset((2, 91)): "WIN",
    frozenset((73, 91)): "WIN",
    frozenset((90, 2)): "WIN",
    frozenset((90, 73)): "WIN",
    frozenset((90, 91)): "WIN",
    frozenset((90, 61)): "LOSS",
    frozenset((61, 66)): "LOSS",
    frozenset((73, 66)): "WIN",  # F-E: 3rd smallest Σd is WIN {73,66}
}

R = [90, 61, 2, 73, 69, 66, 13, 91]


def xy(p: int):
    return (p % 10, p // 10)


def pid(x: int, y: int) -> int:
    return y * 10 + x


def d4_images(x: int, y: int):
    n = 9
    return (
        (x, y),
        (n - x, y),
        (x, n - y),
        (n - x, n - y),
        (y, x),
        (n - y, x),
        (y, n - x),
        (n - y, n - x),
    )


def canon_pair(p: int, q: int) -> int:
    x1, y1 = xy(p)
    x2, y2 = xy(q)
    best = None
    for a in d4_images(x1, y1):
        for b in d4_images(x2, y2):
            ia, ib = pid(*a), pid(*b)
            if ia == ib:
                continue
            key = (min(ia, ib) << 8) | max(ia, ib)
            if best is None or key < best:
                best = key
    return best


def main() -> None:
    data = json.loads(ORBITS.read_text(encoding="utf-8"))
    orbit_by_key = {o["orbit_key"]: o for o in data["orbits"]}
    rows = []
    for a, b in itertools.combinations(R, 2):
        key = canon_pair(a, b)
        o = orbit_by_key[key]
        label = KNOWN.get(frozenset((a, b)), "?")
        rows.append(
            {
                "pair": f"{a},{b}",
                "sum_d": o["sum_d"],
                "quads_containing_pair": o["quads_containing_pair"],
                "d_p": o["d_p"],
                "d_q": o["d_q"],
                "orbit_key": key,
                "outcome": label,
            }
        )
    rows.sort(key=lambda r: r["sum_d"])
    print(f"{'pair':12s} {'sum_d':6s} {'quads':5s} outcome")
    for i, r in enumerate(rows, 1):
        print(f"{i:2d} {r['pair']:12s} {r['sum_d']:6d} {r['quads_containing_pair']:5d} {r['outcome']}")

    # Rank of LOSS pairs
    loss_ranks = [i for i, r in enumerate(rows, 1) if r["outcome"] == "LOSS"]
    win_known = [r for r in rows if r["outcome"] == "WIN"]
    print("LOSS ranks by sum_d ascending:", loss_ranks)
    print("WIN known sum_d range:", min(r["sum_d"] for r in win_known), max(r["sum_d"] for r in win_known))
    lower_win = [r for r in win_known if r["sum_d"] < min(x["sum_d"] for x in rows if x["outcome"] == "LOSS")]
    print("WIN pairs with sum_d below every LOSS pair:")
    for r in lower_win:
        print(" ", r)

    out = ROOT / "research" / "exploration" / "fact_10x10_r_pairs_sigma_d.json"
    out.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    main()
