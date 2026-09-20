#!/usr/bin/env python3
"""Analyze full solver counters for LOSS vs WIN children (P5 mechanism instrumentation).

Compares depth-visited distributions, memo usage by depth, maxdepth, and total visited
between true LOSS and true WIN children.
"""

from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parents[1]
IN_CSV = REPO_ROOT / "results" / "10x10" / "mechanism_counters_sample.csv"
OUT_JSON = REPO_ROOT / "results" / "10x10" / "mechanism_analysis.json"


def load_rows() -> list[dict[str, str]]:
    with IN_CSV.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def compare_groups(loss_vals: list[float], win_vals: list[float], name: str) -> dict:
    u, p = stats.mannwhitneyu(loss_vals, win_vals, alternative="two-sided")
    return {
        "metric": name,
        "loss_median": statistics.median(loss_vals),
        "loss_mean": statistics.mean(loss_vals),
        "win_median": statistics.median(win_vals),
        "win_mean": statistics.mean(win_vals),
        "mann_whitney_u": float(u),
        "p_value": float(p),
    }


def main():
    rows = load_rows()
    loss_rows = [r for r in rows if r["true_outcome"] == "LOSS"]
    win_rows = [r for r in rows if r["true_outcome"] == "WIN"]
    print(f"LOSS sample: {len(loss_rows)}, WIN sample: {len(win_rows)}")

    results = []

    # Basic totals
    for metric in ["visited", "maxdepth", "memo", "seconds"]:
        loss_vals = [float(r[metric]) for r in loss_rows]
        win_vals = [float(r[metric]) for r in win_rows]
        results.append(compare_groups(loss_vals, win_vals, metric))

    # Depth-visited distribution shape
    depth_cols = [c for c in rows[0].keys() if c.startswith("depth_visited_")]
    memo_cols = [c for c in rows[0].keys() if c.startswith("memo_used_d")]

    # Sum of early-depth visits (depth 9-12) vs late-depth visits (13-17)
    early_depth_cols = [c for c in depth_cols if int(c.split("_")[-1]) <= 12]
    late_depth_cols = [c for c in depth_cols if int(c.split("_")[-1]) >= 13]

    loss_early = [sum(float(r[c]) for c in early_depth_cols) for r in loss_rows]
    win_early = [sum(float(r[c]) for c in early_depth_cols) for r in win_rows]
    results.append(compare_groups(loss_early, win_early, "early_depth_visits_sum_9_12"))

    loss_late = [sum(float(r[c]) for c in late_depth_cols) for r in loss_rows]
    win_late = [sum(float(r[c]) for c in late_depth_cols) for r in win_rows]
    results.append(compare_groups(loss_late, win_late, "late_depth_visits_sum_13_17"))

    # Memo usage concentration: early vs late memo entries
    early_memo_cols = [c for c in memo_cols if 9 <= int(c.split("d")[-1]) <= 12]
    late_memo_cols = [c for c in memo_cols if 13 <= int(c.split("d")[-1]) <= 17]

    loss_early_memo = [sum(float(r[c]) for c in early_memo_cols) for r in loss_rows]
    win_early_memo = [sum(float(r[c]) for c in early_memo_cols) for r in win_rows]
    results.append(compare_groups(loss_early_memo, win_early_memo, "early_memo_entries_sum_9_12"))

    loss_late_memo = [sum(float(r[c]) for c in late_memo_cols) for r in loss_rows]
    win_late_memo = [sum(float(r[c]) for c in late_memo_cols) for r in win_rows]
    results.append(compare_groups(loss_late_memo, win_late_memo, "late_memo_entries_sum_13_17"))

    # Memo utilization ratio: memo / visited
    loss_memo_ratio = [float(r["memo"]) / float(r["visited"]) for r in loss_rows]
    win_memo_ratio = [float(r["memo"]) / float(r["visited"]) for r in win_rows]
    results.append(compare_groups(loss_memo_ratio, win_memo_ratio, "memo_to_visited_ratio"))

    summary = {
        "sample_sizes": {"LOSS": len(loss_rows), "WIN": len(win_rows)},
        "comparisons": results,
    }

    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
