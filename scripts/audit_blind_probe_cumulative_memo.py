#!/usr/bin/env python3
"""Audit whether the blind 3-stone memo rule is actually cumulative/order-confounded.

This is post-hoc diagnosis only. It does not alter the preregistered verdict.
It reads the already-frozen blind child ranking table and checks:
  * whether probe_memo is strictly increasing in solver-default order;
  * whether memo-desc fixed_rank is therefore exactly reverse default order;
  * whether marginal memo growth (delta_memo) contains a different signal.
"""
from __future__ import annotations

import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "results" / "10x10" / "blind-probe-rankings.csv"


def pearson(xs, ys):
    if len(xs) < 2:
        return float("nan")
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x-mx)*(y-my) for x,y in zip(xs,ys))
    dx = sum((x-mx)**2 for x in xs)
    dy = sum((y-my)**2 for y in ys)
    return num / math.sqrt(dx*dy) if dx and dy else float("nan")


def first_loss(rows):
    for i, r in enumerate(rows, 1):
        if r["outcome"] == "LOSS":
            return i
    return len(rows) + 1


def main():
    with PATH.open(newline="") as f:
        rows = [r for r in csv.DictReader(f) if int(r["stones"]) == 3 and r["probe_memo"]]

    groups = defaultdict(list)
    for r in rows:
        r = dict(r)
        for k in ("move_index", "fixed_rank", "solver_default_rank", "exact_visited", "probe_memo", "probe_maxdepth", "probe_budget"):
            r[k] = int(r[k])
        groups[r["parent"]].append(r)

    total = 0
    mono_parents = 0
    reverse_parents = 0
    all_deltas = []
    loss_deltas = []
    win_deltas = []
    delta_positions = []
    fixed_positions = []
    solver_positions = []

    print("parent,n,strict_memo_increase,exact_reverse_rank,memo_solver_rank_r,delta_first_loss,fixed_first_loss,solver_first_loss,delta_min,delta_median,delta_max")
    for parent in sorted(groups):
        g = sorted(groups[parent], key=lambda r: r["solver_default_rank"])
        n = len(g)
        total += n
        memos = [r["probe_memo"] for r in g]
        ranks = [r["solver_default_rank"] for r in g]
        strict = all(a < b for a,b in zip(memos, memos[1:]))
        rev = all(r["fixed_rank"] == n + 1 - r["solver_default_rank"] for r in g)
        mono_parents += strict
        reverse_parents += rev

        # First value is growth from an empty memo; subsequent values are marginal growth.
        deltas = [memos[0]] + [b-a for a,b in zip(memos, memos[1:])]
        for r, d in zip(g, deltas):
            all_deltas.append(d)
            (loss_deltas if r["outcome"] == "LOSS" else win_deltas).append(d)

        # Exploratory only: rank by marginal memo growth, descending, ties by default rank.
        delta_order = [r for _,r in sorted(zip(deltas,g), key=lambda x: (-x[0], x[1]["solver_default_rank"]))]
        dp = first_loss(delta_order)
        fp = first_loss(sorted(g, key=lambda r: r["fixed_rank"]))
        sp = first_loss(g)
        delta_positions.append(dp); fixed_positions.append(fp); solver_positions.append(sp)
        print(f"{parent},{n},{int(strict)},{int(rev)},{pearson(memos,ranks):.9f},{dp},{fp},{sp},{min(deltas)},{statistics.median(deltas):.1f},{max(deltas)}")

    print("---")
    print(f"parents={len(groups)} rows={total}")
    print(f"strictly_increasing_memo_parents={mono_parents}/{len(groups)}")
    print(f"exact_reverse_fixed_rank_parents={reverse_parents}/{len(groups)}")
    print(f"all_delta_memo_median={statistics.median(all_deltas):.1f}")
    if loss_deltas:
        print(f"loss_delta_memo_median={statistics.median(loss_deltas):.1f} n={len(loss_deltas)}")
    if win_deltas:
        print(f"win_delta_memo_median={statistics.median(win_deltas):.1f} n={len(win_deltas)}")
    print(f"delta_rule_first_loss_median={statistics.median(delta_positions):.1f}")
    print(f"frozen_fixed_first_loss_median={statistics.median(fixed_positions):.1f}")
    print(f"solver_default_first_loss_median={statistics.median(solver_positions):.1f}")

    if mono_parents == len(groups) and reverse_parents == len(groups):
        print("AUDIT_FINDING=CONFIRMED_ORDER_CONFOUND: memo-desc is exactly reverse solver-default order on every analyzed 3-stone parent")
    else:
        print("AUDIT_FINDING=PARTIAL_ORDER_CONFOUND")


if __name__ == "__main__":
    main()
