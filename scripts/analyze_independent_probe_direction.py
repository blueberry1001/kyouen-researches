#!/usr/bin/env python3
"""Post-hoc direction analysis for the corrected independent 3-stone blind probe.

This script is intentionally *exploratory*: the ascending memo direction was
chosen only after the fresh-process rerun showed that memo-descending failed.
It must not be used to claim confirmatory success on the same seven parents.

It computes, without Monte Carlo:
- first-LOSS rank for ascending/descending probe features and fixed baselines;
- parent-wise LOSS-vs-WIN pairwise AUC (lower score predicts LOSS);
- the exact conditional null distribution of the sum of first-LOSS ranks,
  conditioning on each parent's candidate count and LOSS count.
"""
from __future__ import annotations

import argparse
import csv
import json
from fractions import Fraction
from math import comb
from pathlib import Path
from statistics import median
from typing import Callable


def first_loss(rows: list[dict[str, str]], key: Callable[[dict[str, str]], object]) -> int:
    ordered = sorted(rows, key=key)
    for i, row in enumerate(ordered, 1):
        if row["exact_outcome"] == "LOSS":
            return i
    return len(rows) + 1


def pairwise_auc_lower_loss(rows: list[dict[str, str]], field: str) -> float | None:
    losses = [int(r[field]) for r in rows if r["exact_outcome"] == "LOSS"]
    wins = [int(r[field]) for r in rows if r["exact_outcome"] == "WIN"]
    if not losses or not wins:
        return None
    score = 0.0
    total = 0
    for loss in losses:
        for win in wins:
            total += 1
            if loss < win:
                score += 1.0
            elif loss == win:
                score += 0.5
    return score / total


def first_rank_distribution(n: int, m: int) -> dict[int, Fraction]:
    """Exact distribution for the minimum LOSS rank under a random ordering."""
    if not (1 <= m <= n):
        raise ValueError((n, m))
    denominator = comb(n, m)
    return {
        rank: Fraction(comb(n - rank, m - 1), denominator)
        for rank in range(1, n - m + 2)
    }


def sum_rank_distribution(parent_shapes: list[tuple[int, int]]) -> dict[int, Fraction]:
    dist: dict[int, Fraction] = {0: Fraction(1, 1)}
    for n, m in parent_shapes:
        one = first_rank_distribution(n, m)
        nxt: dict[int, Fraction] = {}
        for subtotal, p0 in dist.items():
            for rank, p1 in one.items():
                nxt[subtotal + rank] = nxt.get(subtotal + rank, Fraction(0, 1)) + p0 * p1
        dist = nxt
    return dist


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("raw", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    with args.raw.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise RuntimeError("empty input")

    by_parent: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_parent.setdefault(row["parent"], []).append(row)
    for rs in by_parent.values():
        rs.sort(key=lambda r: int(r["move_index"]))

    rules: dict[str, Callable[[dict[str, str]], object]] = {
        "memo_desc": lambda r: (-int(r["probe_memo"]), int(r["move_index"])),
        "memo_asc": lambda r: (int(r["probe_memo"]), int(r["move_index"])),
        "maxdepth_desc": lambda r: (-int(r["probe_maxdepth"]), int(r["move_index"])),
        "maxdepth_asc": lambda r: (int(r["probe_maxdepth"]), int(r["move_index"])),
        "visited_desc": lambda r: (-int(r["probe_visited"]), int(r["move_index"])),
        "visited_asc": lambda r: (int(r["probe_visited"]), int(r["move_index"])),
        "solver": lambda r: int(r["move_index"]),
        "reverse": lambda r: -int(r["move_index"]),
    }

    parent_rows: list[dict[str, object]] = []
    shapes: list[tuple[int, int]] = []
    for parent, rs in by_parent.items():
        m = sum(r["exact_outcome"] == "LOSS" for r in rs)
        if m == 0:
            continue
        n = len(rs)
        shapes.append((n, m))
        item: dict[str, object] = {"parent": parent, "candidate_count": n, "loss_count": m}
        for name, key in rules.items():
            item[f"{name}_first_loss"] = first_loss(rs, key)
        item["memo_lower_loss_auc"] = pairwise_auc_lower_loss(rs, "probe_memo")
        item["maxdepth_lower_loss_auc"] = pairwise_auc_lower_loss(rs, "probe_maxdepth")
        item["visited_lower_loss_auc"] = pairwise_auc_lower_loss(rs, "probe_visited")
        item["probe_visited_unique"] = len({int(r["probe_visited"]) for r in rs})
        parent_rows.append(item)

    null = sum_rank_distribution(shapes)
    rule_summary: dict[str, object] = {}
    for name in rules:
        vals = [int(r[f"{name}_first_loss"]) for r in parent_rows]
        observed = sum(vals)
        lower = sum(p for rank_sum, p in null.items() if rank_sum <= observed)
        upper = sum(p for rank_sum, p in null.items() if rank_sum >= observed)
        rule_summary[name] = {
            "median_first_loss": float(median(vals)),
            "rank_sum": observed,
            "exact_random_lower_tail": float(lower),
            "exact_random_upper_tail": float(upper),
        }

    resolved = [
        {
            "parent": r["parent"],
            "child_state": r["child_state"],
            "probe_outcome": r["probe_outcome"],
            "probe_visited": int(r["probe_visited"]),
            "exact_outcome": r["exact_outcome"],
        }
        for r in rows
        if r["probe_outcome"] != "PROBE"
    ]

    output = {
        "status": "exploratory_posthoc_direction_only",
        "caution": "memo_asc was selected after observing memo_desc failure; use a fresh sealed holdout for confirmation",
        "row_count": len(rows),
        "parents_with_loss": len(parent_rows),
        "probe_visited_counts": {
            str(v): sum(int(r["probe_visited"]) == v for r in rows)
            for v in sorted({int(r["probe_visited"]) for r in rows})
        },
        "resolved_within_probe_budget": resolved,
        "parents": parent_rows,
        "rules": rule_summary,
        "memo_lower_loss_auc_median": float(median(
            float(r["memo_lower_loss_auc"]) for r in parent_rows
            if r["memo_lower_loss_auc"] is not None
        )),
    }

    text = json.dumps(output, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
