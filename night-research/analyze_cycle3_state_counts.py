#!/usr/bin/env python3
"""Cycle 3 no-solve: state-count structure by D4 orbit on 9x9 first moves."""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "night-research" / "first-moves-9x9.csv"


def orbit_of(a: int, b: int) -> tuple[int, int]:
    ca, cb = abs(a - 4), abs(b - 4)
    return (max(ca, cb), min(ca, cb))


def main() -> None:
    rows = list(csv.DictReader(CSV_PATH.open(newline="")))
    print("abs  center_rel  verdict  states  seconds  M/s")
    for r in rows:
        a, b = int(r["a"]), int(r["b"])
        o = orbit_of(a, b)
        states = int(r["states"])
        sec = float(r["seconds"])
        print(
            f"({a},{b})  {o}  {r['verdict']}  {states:,}  {sec:.1f}  "
            f"{states / sec / 1e6:.3f}"
        )

    by_orbit: dict[tuple[int, int], list[int]] = defaultdict(list)
    for r in rows:
        a, b = int(r["a"]), int(r["b"])
        by_orbit[orbit_of(a, b)].append(int(r["states"]))

    print()
    print("orbit  n  mean_states  min  max  spread")
    for o, xs in sorted(by_orbit.items()):
        spread = max(xs) - min(xs)
        print(
            f"{o}  {len(xs)}  {sum(xs) / len(xs):,.0f}  "
            f"{min(xs):,}  {max(xs):,}  {spread:,}"
        )

    # Winning-first-move density bounds
    n_win = sum(1 for r in rows if r["verdict"] == "FIRST_WIN")
    n_loss = sum(1 for r in rows if r["verdict"] != "FIRST_WIN")
    # Cell weights: orbit size on 9x9 for each completed class
    # (a,b) absolute with a<=b<=4 covers the fundamental domain.
    weights = {
        (0, 0): 4,  # corners
        (0, 1): 8,
        (0, 2): 8,
        (0, 3): 8,
        (0, 4): 4,
        (1, 1): 4,
        (1, 2): 8,
        (1, 3): 8,
        (1, 4): 4,
        (2, 2): 4,
        (2, 3): 8,
        (2, 4): 4,
        (3, 3): 4,
        (3, 4): 4,
        (4, 4): 1,
    }
    known_cells = 0
    win_cells = 0
    for r in rows:
        key = (int(r["a"]), int(r["b"]))
        w = weights.get(key, 0)
        known_cells += w
        if r["verdict"] == "FIRST_WIN":
            win_cells += w
    # center
    known_cells += 1
    win_cells += 1
    total = 81
    print()
    print(f"cell-weighted known={known_cells}/81 win={win_cells} loss={known_cells - win_cells}")
    if known_cells:
        print(
            f"density in [{win_cells / total:.3f}, "
            f"{(win_cells + (total - known_cells)) / total:.3f}]"
        )


if __name__ == "__main__":
    main()
