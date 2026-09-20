#!/usr/bin/env python3
"""Exploratory P7: exact-search node cost until the first LOSS child in V2."""

from __future__ import annotations

import csv
import json
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from analyze_probe_holdout_v2 import (  # noqa: E402
    corrected_key,
    load_unique_rows,
    memo_desc_key,
    verify_coverage,
)
from holdout_v2_common import legal_children, load_parents  # noqa: E402

OUT_DIR = REPO_ROOT / "results" / "10x10" / "blind-probe-holdout-v2"
OUT_CSV = OUT_DIR / "exploratory_exact_node_efficiency.csv"
OUT_JSON = OUT_DIR / "exploratory_exact_node_efficiency_summary.json"


def node_cost_until_loss(order: list[str], exact_rows: dict[str, dict[str, str]]) -> int:
    total = 0
    for state in order:
        row = exact_rows[state]
        total += int(row["visited"])
        if row["outcome"].strip().upper() == "LOSS":
            return total
    raise RuntimeError("order contains no LOSS child")


def random_expected_node_cost(children: list[str], exact_rows: dict[str, dict[str, str]]) -> float:
    losses = [s for s in children if exact_rows[s]["outcome"].strip().upper() == "LOSS"]
    wins = [s for s in children if exact_rows[s]["outcome"].strip().upper() == "WIN"]
    if not losses:
        raise RuntimeError("no LOSS child")
    # In a uniformly random permutation, exactly one LOSS is paid: each LOSS
    # is equally likely to be the earliest LOSS. A WIN is paid iff it precedes
    # all L losses, which has probability 1/(L+1).
    loss_term = statistics.fmean(int(exact_rows[s]["visited"]) for s in losses)
    win_term = sum(int(exact_rows[s]["visited"]) for s in wins) / (len(losses) + 1)
    return loss_term + win_term


def main() -> None:
    probes = load_unique_rows("independent_probe_1000000_w*-of-*.csv", "probe_outcome")
    exact_all = load_unique_rows("exact_outcomes_w*-of-*.csv", "outcome")
    verify_coverage(probes, exact_all)
    rows: list[dict[str, object]] = []
    for parent in load_parents():
        children = legal_children(parent)
        pmap = {s: probes[(parent, s)] for s in children}
        exact = {s: exact_all[(parent, s)] for s in children}
        corrected = sorted(children, key=lambda s: corrected_key(parent, s, pmap[s]))
        memo_desc = sorted(children, key=lambda s: memo_desc_key(parent, s, pmap[s]))
        default = list(children)
        reverse = list(reversed(children))
        random_e = random_expected_node_cost(children, exact)
        c = node_cost_until_loss(corrected, exact)
        rows.append({
            "parent": parent,
            "corrected_nodes_to_first_loss": c,
            "memo_desc_nodes_to_first_loss": node_cost_until_loss(memo_desc, exact),
            "default_nodes_to_first_loss": node_cost_until_loss(default, exact),
            "reverse_nodes_to_first_loss": node_cost_until_loss(reverse, exact),
            "random_expected_nodes_to_first_loss": random_e,
            "corrected_over_random_expected": c / random_e,
        })
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    ratios = [float(r["corrected_over_random_expected"]) for r in rows]
    summary = {
        "parents": len(rows),
        "mean_corrected_over_random_expected": statistics.fmean(ratios),
        "median_corrected_over_random_expected": statistics.median(ratios),
        "parents_below_random_expected": sum(x < 1.0 for x in ratios),
        "parents_above_random_expected": sum(x > 1.0 for x in ratios),
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
