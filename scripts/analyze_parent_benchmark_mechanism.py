#!/usr/bin/env python3
"""Decompose the V2 parent benchmark failure into root-choice vs cross-child effects.

This analysis uses only already-completed benchmark rows.  It does not rerun the
solver or change any preregistered endpoint.
"""
from __future__ import annotations

import csv
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "results" / "10x10" / "parent-benchmark"
SUMMARY = DIR / "parent_benchmark_results.csv"
RAW = DIR / "parent_benchmark_raw.csv"


def gmean(xs: list[float]) -> float:
    return math.exp(sum(math.log(x) for x in xs) / len(xs))


def main() -> None:
    with SUMMARY.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    with RAW.open(newline="", encoding="utf-8") as f:
        raw = list(csv.DictReader(f))

    by_run = {(r["parent"], r["strategy"]): r for r in raw}
    same_one = []
    multi = []
    for r in rows:
        a = int(r["A_entered"])
        b = int(r["B_entered"])
        rr = float(r["exact_only_visited_ratio"])
        rec = (r["parent"], rr, a, b)
        (same_one if a == b == 1 else multi).append(rec)

    ratios = [x[1] for x in same_one]
    changed_first = 0
    for parent, *_ in same_one:
        a = by_run[(parent, "A")]
        b = by_run[(parent, "B")]
        if (a["root_first_lo"], a["root_first_hi"]) != (b["root_first_lo"], b["root_first_hi"]):
            changed_first += 1

    print("== parent benchmark mechanism decomposition ==")
    print(f"parents_total={len(rows)}")
    print(f"both_enter_exactly_one={len(same_one)}")
    print(f"other_root-entry_patterns={len(multi)}")
    print(f"both-one_changed_first_child={changed_first}/{len(same_one)}")
    print(f"both-one_exact_ratio_median={statistics.median(ratios):.4f}")
    print(f"both-one_exact_ratio_gmean={gmean(ratios):.4f}")
    print(f"both-one_improved={sum(x < 1 for x in ratios)}/{len(ratios)}")
    print(f"both-one_worse={sum(x > 1 for x in ratios)}/{len(ratios)}")
    print("\nparent,exact_ratio,A_entered,B_entered")
    for rec in sorted(same_one + multi):
        print(f"{rec[0]},{rec[1]:.4f},{rec[2]},{rec[3]}")

    print("\nInterpretation:")
    print("When A and B each enter only one root child, no earlier root child can")
    print("have polluted the shared memo.  Any cost difference is therefore due to")
    print("choosing a different first child (plus its internal proof path), not")
    print("cross-root-child memo interference.  Treat multi-entry parents separately.")


if __name__ == "__main__":
    main()
