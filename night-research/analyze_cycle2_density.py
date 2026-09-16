#!/usr/bin/env python3
"""Cross-size winning first-move density table (published + night-research)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Published complete counts from results/results.csv (winning_first_moves, n^2)
# 9 is incomplete; 10 from evidence-sample complete classification (all LOSS).
ROWS = [
    (1, 1, 1, "complete"),
    (2, 4, 4, "complete"),
    (3, 9, 9, "complete"),
    (4, 0, 16, "complete"),
    (5, 9, 25, "complete"),
    (6, 36, 36, "complete"),
    (7, 0, 49, "complete"),
    (8, 0, 64, "complete"),
    (9, None, 81, "partial"),  # filled below if CSV exists
    (10, 0, 100, "complete"),  # evidence-sample all LOSS
]

WINNER = {1: "F", 2: "F", 3: "F", 4: "S", 5: "F", 6: "F", 7: "S", 8: "S", 9: "F", 10: "S"}


def load_nine_partial() -> tuple[int, int, list[dict]]:
    path = ROOT / "first-moves-9x9.csv"
    rows: list[dict] = []
    if not path.exists():
        return 0, 0, rows
    import csv

    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    wins = sum(1 for r in rows if r.get("verdict") == "FIRST_WIN")
    losses = sum(1 for r in rows if r.get("verdict") == "FIRST_LOSS")
    # center known separately
    return wins, losses, rows


def main() -> None:
    nine_w, nine_l, nine_rows = load_nine_partial()
    # Absolute job classes (a,b) are D4 reps on the 9x9 board with center (4,4).
    # Map to center-relative (da,db)=(|a-4|,|b-4|) normalized so da>=db>=0.
    def center_rel(a: int, b: int) -> tuple[int, int]:
        da, db = abs(a - 4), abs(b - 4)
        return max(da, db), min(da, db)

    def orbit_size_9_correct(a: int, b: int) -> int:
        da, db = center_rel(a, b)
        if da == 0 and db == 0:
            return 1
        if da == db or db == 0:
            return 4
        return 8

    # Rebuild known cell-weighted win count for 9x9 partial
    # We only know orbit reps, not that all cells share verdict — they do by D4 symmetry.
    nine_cell_wins = 0
    nine_cell_known = 0
    # center
    nine_cell_wins += 1
    nine_cell_known += 1
    for row in nine_rows:
        a, b = int(row["a"]), int(row["b"])
        sz = orbit_size_9_correct(a, b)
        nine_cell_known += sz
        if row.get("verdict") == "FIRST_WIN":
            nine_cell_wins += sz

    table = []
    for n, wins, cells, status in ROWS:
        if n == 9:
            table.append(
                {
                    "n": n,
                    "winner": WINNER[n],
                    "winning_cells_known": nine_cell_wins,
                    "cells_known": nine_cell_known,
                    "cells_total": 81,
                    "density_lower": nine_cell_wins / 81,
                    "density_if_rest_loss": nine_cell_wins / 81,
                    "density_if_rest_win": (nine_cell_wins + (81 - nine_cell_known)) / 81,
                    "status": "partial",
                    "orbits_done": nine_w + nine_l + 1,  # +center
                    "orbits_total": 15,
                    "orbit_wins": nine_w + 1,
                    "orbit_losses": nine_l,
                }
            )
        else:
            table.append(
                {
                    "n": n,
                    "winner": WINNER[n],
                    "winning_first_moves": wins,
                    "cells": cells,
                    "density": wins / cells,
                    "status": status,
                }
            )

    out = {
        "table": table,
        "h_dense": {
            "statement": "Among F-win boards n<=10, only n=5 has any losing first move.",
            "known_F_win": [1, 2, 3, 5, 6, 9],
            "n5_density": 9 / 25,
            "others_complete_all_win": [1, 2, 3, 6],
            "n9_partial_orbit_losses": nine_l,
            "falsified": nine_l > 0,
            "note": "Exploratory; same data as discovery. Independent test = remaining 9x9 orbits.",
        },
        "h_abs_even_corners": {
            "statement": "Winning first moves on odd n are even (x+y) minus corners.",
            "status": "REJECTED on 9x9 absolute coords (4/8 disagreement among completed non-center orbits)",
            "artifact": "cycle2-5x5-vs-9x9-transfer.json",
        },
        "h_embed": {
            "statement": "Center-relative D4 orbit outcome transfers from 5x5 to 9x9.",
            "status": "open; (0,0) matches; five orbits pending",
            "five_pattern": {
                "(0,0)": "W",
                "(1,0)": "L",
                "(1,1)": "W",
                "(2,0)": "W",
                "(2,1)": "L",
                "(2,2)": "L",
            },
        },
    }
    dest = ROOT / "cycle2-density-table.json"
    dest.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"written": str(dest), "nine_cell_wins": nine_cell_wins, "nine_cell_known": nine_cell_known, "nine_l": nine_l}))
    for row in table:
        if row["n"] == 9:
            print(
                f"n=9  F  cells_known={row['cells_known']}/81  "
                f"win_cells={row['winning_cells_known']}  "
                f"density_bounds=[{row['density_lower']:.3f},{row['density_if_rest_win']:.3f}]"
            )
        else:
            print(f"n={row['n']}  {row['winner']}  {row['winning_first_moves']}/{row['cells']}  dens={row['density']:.3f}")


if __name__ == "__main__":
    main()
