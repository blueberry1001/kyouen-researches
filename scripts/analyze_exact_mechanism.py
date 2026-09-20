#!/usr/bin/env python3
"""P5 mechanism analysis: compare full exact-solve counters between LOSS and WIN children.

Reads all existing exact_*.csv files in results/10x10/blind_probe_children/.
"""

from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parents[1]
EXACT_DIR = REPO_ROOT / "results" / "10x10" / "blind_probe_children"
OUT_JSON = REPO_ROOT / "results" / "10x10" / "exact_mechanism_analysis.json"


def load_all_exact_rows() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    all_rows = []
    full_rows = []
    for p in sorted(EXACT_DIR.glob("exact_*.csv")):
        with p.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            header = reader.fieldnames or []
            file_rows = list(reader)
            all_rows.extend(file_rows)
            if "depth_visited_9" in header:
                full_rows.extend(file_rows)
    return all_rows, full_rows


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
    rows, full_rows = load_all_exact_rows()
    loss_rows = [r for r in rows if r["outcome"] == "LOSS"]
    win_rows = [r for r in rows if r["outcome"] == "WIN"]
    loss_full = [r for r in full_rows if r["outcome"] == "LOSS"]
    win_full = [r for r in full_rows if r["outcome"] == "WIN"]
    print(f"Exact outcomes: {len(loss_rows)} LOSS, {len(win_rows)} WIN, total {len(rows)}")
    print(f"Full-counter subset: {len(loss_full)} LOSS, {len(win_full)} WIN, total {len(full_rows)}")

    results = []

    # Basic totals
    for metric in ["visited", "maxdepth", "memo", "seconds"]:
        loss_vals = [float(r[metric]) for r in loss_rows]
        win_vals = [float(r[metric]) for r in win_rows]
        results.append(compare_groups(loss_vals, win_vals, metric))

    depth_cols = [c for c in full_rows[0].keys() if c.startswith("depth_visited_")] if full_rows else []
    memo_cols = [c for c in full_rows[0].keys() if c.startswith("memo_used_d")] if full_rows else []

    # Distribution by depth bins
    early_depth_cols = [c for c in depth_cols if 9 <= int(c.split("_")[-1]) <= 12]
    mid_depth_cols = [c for c in depth_cols if 13 <= int(c.split("_")[-1]) <= 15]
    late_depth_cols = [c for c in depth_cols if 16 <= int(c.split("_")[-1]) <= 19]

    for label, cols in [("early_depth_9_12", early_depth_cols),
                        ("mid_depth_13_15", mid_depth_cols),
                        ("late_depth_16_19", late_depth_cols)]:
        loss_vals = [sum(float(r[c]) for c in cols) for r in loss_full]
        win_vals = [sum(float(r[c]) for c in cols) for r in win_full]
        results.append(compare_groups(loss_vals, win_vals, label))

    early_memo_cols = [c for c in memo_cols if 9 <= int(c.split("d")[-1]) <= 12]
    mid_memo_cols = [c for c in memo_cols if 13 <= int(c.split("d")[-1]) <= 15]
    late_memo_cols = [c for c in memo_cols if 16 <= int(c.split("d")[-1]) <= 19]

    for label, cols in [("early_memo_9_12", early_memo_cols),
                        ("mid_memo_13_15", mid_memo_cols),
                        ("late_memo_16_19", late_memo_cols)]:
        loss_vals = [sum(float(r[c]) for c in cols) for r in loss_full]
        win_vals = [sum(float(r[c]) for c in cols) for r in win_full]
        results.append(compare_groups(loss_vals, win_vals, label))

    # Ratios
    loss_memo_ratio = [float(r["memo"]) / float(r["visited"]) for r in loss_rows]
    win_memo_ratio = [float(r["memo"]) / float(r["visited"]) for r in win_rows]
    results.append(compare_groups(loss_memo_ratio, win_memo_ratio, "memo_to_visited_ratio"))

    # Relative depth distribution shape (fraction of visits at each depth bin)
    for label, cols in [("rel_early_depth_9_12", early_depth_cols),
                        ("rel_mid_depth_13_15", mid_depth_cols),
                        ("rel_late_depth_16_19", late_depth_cols)]:
        loss_vals = [sum(float(r[c]) for c in cols) / float(r["visited"]) for r in loss_full]
        win_vals = [sum(float(r[c]) for c in cols) / float(r["visited"]) for r in win_full]
        results.append(compare_groups(loss_vals, win_vals, label))

    # Maxdepth proportion reaching depth 18 (if available)
    if "depth_visited_18" in rows[0]:
        loss_d18 = [float(r["depth_visited_18"]) / float(r["visited"]) for r in loss_rows]
        win_d18 = [float(r["depth_visited_18"]) / float(r["visited"]) for r in win_rows]
        results.append(compare_groups(loss_d18, win_d18, "fraction_of_visits_at_depth_18"))

    summary = {
        "sample_sizes": {"LOSS": len(loss_rows), "WIN": len(win_rows), "total": len(rows)},
        "comparisons": results,
    }

    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
