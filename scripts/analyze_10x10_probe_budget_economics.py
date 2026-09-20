#!/usr/bin/env python3
"""Analyze rank efficiency and optimistic break-even probe budgets for 10x10.

This is an exploratory/post-hoc resource-planning analysis. It combines:
- V1 fresh-memo holdout budget-stability ranks (10k/100k/1M), and
- V2 P6 measured 1M probe-all + exact-to-first-LOSS wall-clock costs.

The projected 10k/100k V2 cost ratios are deliberately optimistic screens:
they assume probe time scales linearly with visited budget AND that the same
1M memo-first LOSS candidate remains first at the lower budget. They are not
measured lower-budget solver costs and must not be reported as such.
"""

from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V1_STABILITY = ROOT / "results/10x10/blind-probe-holdout/budget_stability_analysis.csv"
V1_NULL = ROOT / "results/10x10/blind-probe-holdout/preregistered_exact_random_null.json"
V2_COST = ROOT / "results/10x10/clean-holdout-v2/p6_first_loss_cost.csv"


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    v1 = load_csv(V1_STABILITY)
    v2 = load_csv(V2_COST)
    null = json.loads(V1_NULL.read_text(encoding="utf-8"))
    random_sum = float(null["random_expected_sum_first_loss_rank"])
    rank_1m_sum = sum(int(r["first_loss_rank_1M"]) for r in v1)
    full_gain = random_sum - rank_1m_sum

    rank_summary: dict[str, object] = {}
    for label, field, budget in (
        ("10k", "first_loss_rank_10k", 10_000),
        ("100k", "first_loss_rank_100k", 100_000),
        ("1M", "first_loss_rank_1M", 1_000_000),
    ):
        ranks = [int(r[field]) for r in v1]
        rank_summary[label] = {
            "budget_per_child": budget,
            "sum_first_loss_rank": sum(ranks),
            "mean_first_loss_rank": statistics.mean(ranks),
            "median_first_loss_rank": statistics.median(ranks),
            "max_first_loss_rank": max(ranks),
            "fraction_of_1M_rank_sum_gain_vs_random": (random_sum - sum(ranks)) / full_gain,
        }

    break_even_rows: list[dict[str, object]] = []
    for r in v2:
        probe_1m = float(r["probe_cost_s"])
        file_exact = float(r["exact_cost_to_first_loss_file_order_s"])
        memo_exact = float(r["exact_cost_to_first_loss_memo_order_s"])
        saved_exact = file_exact - memo_exact
        break_even = 1_000_000.0 * saved_exact / probe_1m if saved_exact > 0 else 0.0
        row: dict[str, object] = {
            "parent": r["parent"],
            "exact_savings_if_1M_memo_first_candidate_preserved_s": saved_exact,
            "optimistic_break_even_visited_per_child": break_even,
        }
        for label, frac in (("10k", 0.01), ("100k", 0.1)):
            projected_total = probe_1m * frac + memo_exact
            row[f"optimistic_{label}_total_cost_ratio"] = projected_total / file_exact
        break_even_rows.append(row)

    break_evens = [float(r["optimistic_break_even_visited_per_child"]) for r in break_even_rows]
    ratios_10k = [float(r["optimistic_10k_total_cost_ratio"]) for r in break_even_rows]
    ratios_100k = [float(r["optimistic_100k_total_cost_ratio"]) for r in break_even_rows]

    out = {
        "status": "exploratory_posthoc_resource_planning",
        "v1_rank_efficiency": {
            "random_expected_rank_sum": random_sum,
            "budgets": rank_summary,
            "incremental_rank_sum_improvement_10k_to_100k": int(rank_summary["10k"]["sum_first_loss_rank"]) - int(rank_summary["100k"]["sum_first_loss_rank"]),
            "probe_budget_multiplier_10k_to_100k": 10,
        },
        "v2_optimistic_break_even_screen": {
            "assumptions": [
                "probe wall time scales linearly with visited budget",
                "the 1M memo-first LOSS candidate remains first at the lower budget",
            ],
            "median_break_even_visited_per_child": statistics.median(break_evens),
            "parents_where_optimistic_10k_ratio_lt_1": sum(x < 1 for x in ratios_10k),
            "parents_where_optimistic_100k_ratio_lt_1": sum(x < 1 for x in ratios_100k),
            "median_optimistic_10k_ratio": statistics.median(ratios_10k),
            "median_optimistic_100k_ratio": statistics.median(ratios_100k),
            "per_parent": break_even_rows,
        },
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
