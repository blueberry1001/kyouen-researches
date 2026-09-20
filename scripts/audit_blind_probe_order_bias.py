#!/usr/bin/env python3
"""Audit blind 10x10 probe rankings for candidate-order contamination.

The blind 3-stone rule ranks `memo` descending.  The probe solver emits
`solver.memo_used()` from one Solver instance shared by all states in an input
batch, so this script checks whether the resulting ranking is merely the
reverse of the solver-default input order.

It is deliberately read-only: it does not rewrite any historical result.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RANKINGS = ROOT / "results" / "10x10" / "blind-probe-rankings.csv"


def main() -> None:
    with RANKINGS.open(newline="") as f:
        rows = list(csv.DictReader(f))

    by_parent: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        if int(r["stones"]) == 3:
            by_parent[r["parent"]].append(r)

    total_rows = 0
    exact_reverse_rows = 0
    all_monotone = True
    loss_parents = 0
    fixed_first_losses: list[int] = []
    solver_first_losses: list[int] = []

    print("parent,n,memo_strictly_increasing,fixed_exact_reverse,first_loss_fixed,first_loss_solver")
    for parent, rs in by_parent.items():
        rs.sort(key=lambda r: int(r["solver_default_rank"]))
        n = len(rs)
        memos = [int(r["probe_memo"]) for r in rs]
        monotone = all(a < b for a, b in zip(memos, memos[1:]))
        reverse = all(int(r["fixed_rank"]) == n + 1 - int(r["solver_default_rank"]) for r in rs)
        total_rows += n
        exact_reverse_rows += sum(
            int(r["fixed_rank"]) == n + 1 - int(r["solver_default_rank"]) for r in rs
        )
        all_monotone &= monotone

        losses = [r for r in rs if r["outcome"] == "LOSS"]
        if losses:
            loss_parents += 1
            fixed_first = min(int(r["fixed_rank"]) for r in losses)
            solver_first = min(int(r["solver_default_rank"]) for r in losses)
            fixed_first_losses.append(fixed_first)
            solver_first_losses.append(solver_first)
        else:
            fixed_first = n + 1
            solver_first = n + 1

        print(f"{parent},{n},{monotone},{reverse},{fixed_first},{solver_first}")

    def median(xs: list[int]) -> float | None:
        if not xs:
            return None
        ys = sorted(xs)
        m = len(ys) // 2
        return float(ys[m]) if len(ys) % 2 else (ys[m - 1] + ys[m]) / 2

    print()
    print(f"parents={len(by_parent)}")
    print(f"loss_parents={loss_parents}")
    print(f"rows={total_rows}")
    print(f"memo_strictly_increasing_all_parents={all_monotone}")
    print(f"fixed_exact_reverse_rows={exact_reverse_rows}/{total_rows}")
    print(f"fixed_first_loss_median={median(fixed_first_losses)}")
    print(f"solver_first_loss_median={median(solver_first_losses)}")

    if exact_reverse_rows == total_rows:
        print("CONCLUSION: historical 3-stone fixed ranking is exactly reverse solver-default order on this dataset.")
    else:
        print("CONCLUSION: ranking is order-contaminated but not exactly reverse on every row; inspect exceptions.")


if __name__ == "__main__":
    main()
