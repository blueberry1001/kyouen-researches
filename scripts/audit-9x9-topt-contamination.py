#!/usr/bin/env python3
"""Cross-check: does E/O contamination of top_T predict LOSS on 9x9 factorial data?

Uses existing holdout/population columns only. No new solves.
"""
from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POP = ROOT / "artifacts" / "9x9-factorial-population.csv"
HOLD = ROOT / "artifacts" / "9x9-factorial-holdout.csv"
OUT = ROOT / "artifacts" / "9x9-topT-contamination-audit.json"


def load(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    # Inspect holdout columns first
    hold = load(HOLD)
    pop = load(POP)
    print("holdout cols:", list(hold[0].keys())[:30])
    print("pop cols:", list(pop[0].keys())[:30])
    print("holdout n", len(hold), "pop n", len(pop))

    # Find outcome-like columns
    h0 = hold[0]
    outcome_cols = [c for c in h0 if "out" in c.lower() or "win" in c.lower() or "loss" in c.lower()]
    print("outcome-like:", outcome_cols)

    report = {"holdout_n": len(hold), "pop_n": len(pop), "outcome_cols": outcome_cols}
    OUT.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
