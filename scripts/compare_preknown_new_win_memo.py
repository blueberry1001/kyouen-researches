#!/usr/bin/env python3
"""P1: Directly test the relationship between memo-used within-parent percentile and:
1. preknown LOSS witnesses
2. newly discovered LOSS children
3. WIN children

Calculates within-parent normalized rank (rank / m) or percentile,
and performs statistical comparisons (medians, Mann-Whitney U tests).
"""

from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parents[1]

import sys
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from analyze_probe_holdout_preregistered import (
    corrected_key,
    load_children,
    load_exact,
    load_parents,
    load_probe,
)

PREKNOWN_DETAILS_CSV = REPO_ROOT / "results" / "10x10" / "exhaustive_preknown_loss_details.csv"
OUT_JSON = REPO_ROOT / "results" / "10x10" / "memo_preknown_vs_new_loss_vs_win.json"
OUT_CSV = REPO_ROOT / "results" / "10x10" / "memo_preknown_vs_new_loss_vs_win.csv"


def load_preknown_set() -> set[tuple[str, str]]:
    preknown = set()
    with PREKNOWN_DETAILS_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            preknown.add((r["parent"], r["literal_child"]))
    return preknown


def main():
    parents = load_parents()
    probes = load_probe()
    preknown_set = load_preknown_set()

    rows = []
    preknown_pcts = []
    new_loss_pcts = []
    win_pcts = []

    for p in parents:
        children = load_children(p)
        exact = load_exact(p)
        m = len(children)
        pmap = {(p, s): probes[(p, s)] for s in children}
        order = sorted(children, key=lambda s: corrected_key(p, s, pmap[(p, s)]))

        for rank_idx, s in enumerate(order, start=1):
            memo_val = int(probes[(p, s)]["memo"])
            visited_val = int(probes[(p, s)]["visited"])
            outcome = exact[s]
            is_preknown = (p, s) in preknown_set

            if outcome == "LOSS":
                category = "PREKNOWN_LOSS" if is_preknown else "NEW_LOSS"
            else:
                category = "WIN"

            # Normalized rank: rank / m (0 to 1, lower is earlier / smaller memo)
            norm_rank = rank_idx / m
            pct = (rank_idx - 0.5) / m

            if category == "PREKNOWN_LOSS":
                preknown_pcts.append(norm_rank)
            elif category == "NEW_LOSS":
                new_loss_pcts.append(norm_rank)
            else:
                win_pcts.append(norm_rank)

            rows.append({
                "parent": p,
                "child": s,
                "category": category,
                "memo": memo_val,
                "visited": visited_val,
                "rank": rank_idx,
                "m": m,
                "norm_rank": norm_rank,
                "percentile": pct,
                "exact_outcome": outcome,
                "is_preknown": is_preknown,
            })

    # Statistical comparisons
    # 1. Preknown LOSS vs New LOSS
    u_pre_vs_new, p_pre_vs_new = stats.mannwhitneyu(preknown_pcts, new_loss_pcts, alternative="two-sided")
    # 2. All LOSS vs WIN
    all_loss_pcts = preknown_pcts + new_loss_pcts
    u_loss_vs_win, p_loss_vs_win = stats.mannwhitneyu(all_loss_pcts, win_pcts, alternative="less")
    # 3. New LOSS vs WIN
    u_new_vs_win, p_new_vs_win = stats.mannwhitneyu(new_loss_pcts, win_pcts, alternative="less")
    # 4. Preknown LOSS vs WIN
    u_pre_vs_win, p_pre_vs_win = stats.mannwhitneyu(preknown_pcts, win_pcts, alternative="less")

    summary = {
        "sample_sizes": {
            "preknown_loss": len(preknown_pcts),
            "new_loss": len(new_loss_pcts),
            "all_loss": len(all_loss_pcts),
            "win": len(win_pcts),
            "total": len(rows),
        },
        "median_norm_rank": {
            "preknown_loss": statistics.median(preknown_pcts),
            "new_loss": statistics.median(new_loss_pcts),
            "all_loss": statistics.median(all_loss_pcts),
            "win": statistics.median(win_pcts),
        },
        "mean_norm_rank": {
            "preknown_loss": statistics.mean(preknown_pcts),
            "new_loss": statistics.mean(new_loss_pcts),
            "all_loss": statistics.mean(all_loss_pcts),
            "win": statistics.mean(win_pcts),
        },
        "mann_whitney_tests": {
            "preknown_vs_new_loss": {
                "u_statistic": float(u_pre_vs_new),
                "p_value_two_sided": float(p_pre_vs_new),
                "interpretation": "Whether preknown LOSS witnesses had significantly different memo rank from newly discovered LOSS children",
            },
            "all_loss_vs_win": {
                "u_statistic": float(u_loss_vs_win),
                "p_value_one_sided_less": float(p_loss_vs_win),
                "interpretation": "Whether ALL LOSS children have significantly lower memo rank than WIN children",
            },
            "new_loss_vs_win": {
                "u_statistic": float(u_new_vs_win),
                "p_value_one_sided_less": float(p_new_vs_win),
                "interpretation": "Whether NEWLY DISCOVERED LOSS children alone have significantly lower memo rank than WIN children",
            },
            "preknown_loss_vs_win": {
                "u_statistic": float(u_pre_vs_win),
                "p_value_one_sided_less": float(p_pre_vs_win),
                "interpretation": "Whether PREKNOWN LOSS witnesses have significantly lower memo rank than WIN children",
            },
        },
    }

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n--- P1: Memo Percentile Comparison Summary ---")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
