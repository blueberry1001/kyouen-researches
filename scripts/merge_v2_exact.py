#!/usr/bin/env python3
"""Merge per-worker exact solve CSVs into exact_outcomes.csv for Clean Holdout V2."""

from __future__ import annotations

import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
V2_DIR = REPO_ROOT / "results" / "10x10" / "clean-holdout-v2"
TASK_CSV = V2_DIR / "exact_task_list.csv"
OUT_CSV = V2_DIR / "exact_outcomes.csv"

FIELDS = [
    "parent", "batch", "batch_position", "state", "outcome",
    "visited", "maxdepth", "memo", "seconds",
]


def main():
    with TASK_CSV.open(newline="", encoding="utf-8") as f:
        tasks = list(csv.DictReader(f))

    worker_files = sorted(V2_DIR.glob("exact_outcomes_w*.csv"))
    print(f"Found {len(worker_files)} worker files: {[f.name for f in worker_files]}")

    results = {}
    for wf in worker_files:
        with wf.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                key = (r["parent"], r["state"].replace(",", "-"))
                results[key] = r

    print(f"Total tasks in manifest: {len(tasks)}")
    print(f"Total solved results found: {len(results)}")

    # Order exactly as in TASK_CSV
    rows_out = []
    missing = []
    for t in tasks:
        key = (t["parent"], t["state"].replace(",", "-"))
        if key in results:
            rows_out.append(results[key])
        else:
            missing.append(key)

    if missing:
        print(f"WARNING: {len(missing)} tasks still missing!")
        print("First 5 missing:", missing[:5])
        return

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows_out)

    outcomes = {}
    for r in rows_out:
        outcomes[r["outcome"]] = outcomes.get(r["outcome"], 0) + 1

    print(f"Successfully merged {len(rows_out)} tasks to {OUT_CSV}")
    print("Exact outcome distribution:", outcomes)


if __name__ == "__main__":
    main()
