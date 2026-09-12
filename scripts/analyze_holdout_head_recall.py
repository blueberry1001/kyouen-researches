#!/usr/bin/env python3
"""Post-hoc audit of head recall for the frozen 10x10 probe holdout.

This does not alter the preregistered endpoint.  It asks a solver-oriented
question using only already-frozen outcome summaries: how small a memo-ascending
shortlist would have contained at least one exact LOSS for every parent?

The resulting K is exploratory and must be frozen before any new holdout if it
is used as a future endpoint.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "results/10x10/blind-probe-holdout/preregistered_parent_results.csv"


def random_top_k_hit_probability(m: int, l: int, k: int) -> float:
    """P(at least one of l LOSS children occurs in first k random positions)."""
    if k <= 0:
        return 0.0
    if k >= m or m - l < k:
        return 1.0
    return 1.0 - math.comb(m - l, k) / math.comb(m, k)


def main() -> None:
    with INPUT.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    corrected = [int(r["corrected_first_loss"]) for r in rows]
    default = [int(r["default_first_loss"]) for r in rows]
    k = max(corrected)

    corrected_hits = sum(rank <= k for rank in corrected)
    default_hits = sum(rank <= k for rank in default)

    per_parent_random = [
        random_top_k_hit_probability(int(r["m"]), int(r["loss_children"]), k)
        for r in rows
    ]
    joint_random = math.prod(per_parent_random)

    print(f"parents={len(rows)}")
    print(f"exploratory_min_K_for_full_corrected_coverage={k}")
    print(f"corrected_top{k}_coverage={corrected_hits}/{len(rows)}")
    print(f"solver_default_top{k}_coverage={default_hits}/{len(rows)}")
    print(f"random_joint_probability_all_parents_hit_top{k}={joint_random:.12g}")

    # For a parent with exactly two LOSS children, AUC plus the first LOSS rank
    # determines the second LOSS rank exactly (assuming the ranking used by the
    # AUC has no score ties affecting average ranks).  This exposes the shape of
    # the only non-rank-1 parent without reopening the raw outcome labels.
    for r in rows:
        l = int(r["loss_children"])
        if l != 2:
            continue
        m = int(r["m"])
        w = m - l
        auc = float(r["corrected_auc"])
        first = int(r["corrected_first_loss"])
        rank_sum = l * w * (1.0 - auc) + l * (l + 1) / 2.0
        rounded = round(rank_sum)
        if abs(rank_sum - rounded) < 1e-8:
            second = int(rounded) - first
            print(
                f"two_loss_parent={r['parent']} first_loss_rank={first} "
                f"second_loss_rank={second} auc={auc:.6f}"
            )
        else:
            print(
                f"two_loss_parent={r['parent']} rank_sum={rank_sum:.6f} "
                "(score ties prevent exact rank reconstruction)"
            )

    print("note=K is selected post-hoc from this holdout; freeze K=6 before any independent validation")


if __name__ == "__main__":
    main()
