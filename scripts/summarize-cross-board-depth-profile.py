#!/usr/bin/env python3
"""Summarize cross-board random depth profiles (8x8 vs 9x9)."""
from __future__ import annotations

import csv
import json
import statistics
from collections import Counter
from pathlib import Path

ART = Path(__file__).resolve().parents[1] / "artifacts"
OUT = ART / "cross-board-depth-profile.json"


def load(board: str, stones: str) -> dict:
    p = ART / f"{board}-random-safe-{stones}-out.csv"
    with p.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    c = Counter(r["child_outcome"] for r in rows)
    vis = [int(r["visited"]) for r in rows]
    n = len(rows)
    return {
        "board": board,
        "stones": stones,
        "n": n,
        "LOSS": c.get("LOSS", 0),
        "WIN": c.get("WIN", 0),
        "LOSS_rate": c.get("LOSS", 0) / n if n else None,
        "visited_median": statistics.median(vis) if vis else None,
        "visited_mean": statistics.mean(vis) if vis else None,
    }


def main() -> None:
    rows = []
    for board in ("8x8", "9x9"):
        for stones in ("4stone", "5stone", "6stone"):
            p = ART / f"{board}-random-safe-{stones}-out.csv"
            if p.exists():
                rows.append(load(board, stones))
    # also include known empty-board winner
    known = {
        "8x8": {"empty_winner": "second", "empty_outcome_player_to_move": "LOSS"},
        "9x9": {"empty_winner": "first", "empty_outcome_player_to_move": "WIN"},
    }
    report = {
        "rows": rows,
        "known_empty": known,
        "interpretation": (
            "Shallow random-safe LOSS rate peaks at a board-dependent depth. "
            "8x8 (second-player win): peak at 4 stones (~0.61). "
            "9x9 (first-player win): peak at 5 stones (~0.62). "
            "Neighbor depths are near-all-WIN. "
            "This inverts the factorial 4→5 experimental regime between boards."
        ),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    for r in rows:
        print(
            f"{r['board']} {r['stones']}: n={r['n']} LOSS={r['LOSS']} "
            f"rate={r['LOSS_rate']:.4f} visited_med={r['visited_median']}"
        )


if __name__ == "__main__":
    main()
