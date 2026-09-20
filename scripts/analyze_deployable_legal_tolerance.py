#!/usr/bin/env python3
"""Audit legal-move-count tolerance bands using a deployable threshold.

Unlike analyze_loss_tolerance_headroom.py, this script defines the threshold from
*all legal root children*, which is available to the solver at runtime.  The older
ceiling analysis used the minimum only among LOSS children; that quantity is an
oracle signal and can make a small tolerance look safer/more useful than it is.

The LOSS dataset is still used for exact outcomes/costs, while all-child legal
counts are recomputed directly from the game geometry.
"""

from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from itertools import combinations
from pathlib import Path

DATA = Path("results/10x10/parent-benchmark/loss_proof_cost_dataset.csv")
N = 10
KS = (0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 13)


def median(xs):
    return statistics.median(xs) if xs else float("nan")


def det3(m):
    return (
        m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
        - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
        + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
    )


def forbidden4(ids):
    """True iff four grid points are concyclic or collinear."""
    pts = [(v % N, v // N) for v in ids]
    xd, yd = pts[3]
    qd = xd * xd + yd * yd
    m = []
    for x, y in pts[:3]:
        m.append([x * x + y * y - qd, x - xd, y - yd])
    return det3(m) == 0


def legal_after(state, move):
    if move in state:
        return False
    return all(not forbidden4((*triple, move)) for triple in combinations(state, 3))


def child_legal_count(child):
    occupied = set(child)
    return sum(
        1
        for move in range(N * N)
        if move not in occupied and legal_after(child, move)
    )


def all_root_children(parent):
    rows = []
    for move in range(N * N):
        if move in parent or not legal_after(parent, move):
            continue
        child = tuple(sorted((*parent, move)))
        rows.append((move, child_legal_count(child)))
    return rows


def main():
    by_parent = defaultdict(list)
    with DATA.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["exact_visited"] = int(row["exact_visited"])
            row["legal_move_count"] = int(row["legal_move_count"])
            row["native_rank"] = int(row["native_rank"])
            row["move_id"] = int(row["move_id"])
            by_parent[row["parent"]].append(row)

    info = {}
    for parent_s, loss_rows in by_parent.items():
        parent = tuple(map(int, parent_s.split(",")))
        all_rows = all_root_children(parent)
        all_min = min(x[1] for x in all_rows)
        loss_min = min(r["legal_move_count"] for r in loss_rows)
        global_row = min(loss_rows, key=lambda r: (r["exact_visited"], r["move_id"]))
        native_row = min(loss_rows, key=lambda r: (r["native_rank"], r["move_id"]))
        info[parent_s] = {
            "loss_rows": loss_rows,
            "all_rows": all_rows,
            "all_min": all_min,
            "loss_min": loss_min,
            "global_row": global_row,
            "native_row": native_row,
        }

    print("deployable legal_move_count tolerance audit")
    print(f"parents={len(info)}")
    print("threshold := minimum legal_move_count among ALL legal root children + k")
    print()
    print("parent,all_min,loss_min,first_loss_gap,global_move,global_gap_from_all_min,"
          "global_gap_from_loss_min,native_move")
    for parent in sorted(info):
        x = info[parent]
        g = x["global_row"]
        print(
            f"{parent},{x['all_min']},{x['loss_min']},{x['loss_min'] - x['all_min']},"
            f"{g['move_id']},{g['legal_move_count'] - x['all_min']},"
            f"{g['legal_move_count'] - x['loss_min']},{x['native_row']['move_id']}"
        )

    print()
    print("k,parents_with_loss,oracle_covered,median_all_band,max_all_band,"
          "median_win_clutter,max_win_clutter,native_regret_parents_improvable")
    regret_parents = [
        p for p, x in info.items()
        if x["native_row"]["exact_visited"] > x["global_row"]["exact_visited"]
    ]
    for k in KS:
        with_loss = 0
        covered = 0
        all_sizes = []
        win_clutter = []
        improvable = 0
        for parent, x in info.items():
            threshold = x["all_min"] + k
            all_band = [r for r in x["all_rows"] if r[1] <= threshold]
            loss_band = [r for r in x["loss_rows"] if r["legal_move_count"] <= threshold]
            all_sizes.append(len(all_band))
            win_clutter.append(len(all_band) - len(loss_band))
            if loss_band:
                with_loss += 1
            if x["global_row"]["legal_move_count"] <= threshold:
                covered += 1
            if parent in regret_parents and loss_band:
                best = min(r["exact_visited"] for r in loss_band)
                if best < x["native_row"]["exact_visited"]:
                    improvable += 1
        print(
            f"{k},{with_loss}/{len(info)},{covered}/{len(info)},"
            f"{median(all_sizes):.1f},{max(all_sizes)},"
            f"{median(win_clutter):.1f},{max(win_clutter)},"
            f"{improvable}/{len(regret_parents)}"
        )


if __name__ == "__main__":
    main()
