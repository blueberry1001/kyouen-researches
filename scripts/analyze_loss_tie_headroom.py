#!/usr/bin/env python3
"""Quantify the maximum possible gain from tie-breaking legal_move_count.

This analysis deliberately keeps legal_move_count as the primary key.  For each
parent it compares the native first LOSS with an oracle that may choose only
among LOSS children having the minimum legal_move_count.  That oracle is an
upper bound on every possible tie-breaker (n_cols included) that does not
change the primary legal_move_count ordering.
"""

from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from pathlib import Path

DATA = Path("results/10x10/parent-benchmark/loss_proof_cost_dataset.csv")


def median(xs):
    return statistics.median(xs) if xs else float("nan")


def main() -> None:
    groups = defaultdict(list)
    with DATA.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["legal_move_count"] = int(row["legal_move_count"])
            row["exact_visited"] = int(row["exact_visited"])
            row["native_rank"] = int(row["native_rank"])
            row["move_id"] = int(row["move_id"])
            groups[row["parent"]].append(row)

    records = []
    for parent, rows in sorted(groups.items()):
        global_oracle = min(rows, key=lambda r: (r["exact_visited"], r["move_id"]))
        native = min(rows, key=lambda r: (r["native_rank"], r["move_id"]))
        min_legal = min(r["legal_move_count"] for r in rows)
        bucket = [r for r in rows if r["legal_move_count"] == min_legal]
        tie_oracle = min(bucket, key=lambda r: (r["exact_visited"], r["move_id"]))

        # If this fails, native_rank is not the legal_move_count-primary order we
        # think it is, and the interpretation below would be invalid.
        assert native["legal_move_count"] == min_legal, (
            parent,
            native["legal_move_count"],
            min_legal,
        )

        g = global_oracle["exact_visited"]
        n = native["exact_visited"]
        t = tie_oracle["exact_visited"]
        removable = 0.0 if n == g else (n - t) / (n - g)
        records.append(
            {
                "parent": parent,
                "n_loss": len(rows),
                "min_legal": min_legal,
                "bucket_size": len(bucket),
                "native_move": native["move_id"],
                "tie_oracle_move": tie_oracle["move_id"],
                "global_oracle_move": global_oracle["move_id"],
                "native_ratio": n / g,
                "tie_oracle_ratio": t / g,
                "oracle_in_bucket": global_oracle["legal_move_count"] == min_legal,
                "oracle_legal_gap": global_oracle["legal_move_count"] - min_legal,
                "removable_regret": removable,
            }
        )

    native_ratios = [r["native_ratio"] for r in records]
    tie_ratios = [r["tie_oracle_ratio"] for r in records]
    regret_cases = [r for r in records if r["native_ratio"] > 1.0]

    print("legal_move_count tie-break headroom")
    print(f"parents={len(records)}")
    print(f"native/global-oracle median={median(native_ratios):.6f}")
    print(f"perfect-tie/global-oracle median={median(tie_ratios):.6f}")
    print(
        "parents with tie opportunity="
        f"{sum(r['bucket_size'] > 1 for r in records)}/{len(records)}"
    )
    print(
        "global oracle already in min-legal bucket="
        f"{sum(r['oracle_in_bucket'] for r in records)}/{len(records)}"
    )
    print(
        "parents where perfect tie improves native="
        f"{sum(r['tie_oracle_ratio'] < r['native_ratio'] for r in records)}/{len(records)}"
    )
    if regret_cases:
        print(
            "median fraction of native regret removable by perfect tie "
            "(parents with native regret)="
            f"{median([r['removable_regret'] for r in regret_cases]):.6f}"
        )

    print("\nparent details")
    print(
        "parent,n_loss,min_legal,bucket,native_move,tie_move,global_move,"
        "native_ratio,tie_ratio,oracle_in_bucket,oracle_legal_gap,removable_regret"
    )
    for r in records:
        print(
            f"{r['parent']},{r['n_loss']},{r['min_legal']},{r['bucket_size']},"
            f"{r['native_move']},{r['tie_oracle_move']},{r['global_oracle_move']},"
            f"{r['native_ratio']:.6f},{r['tie_oracle_ratio']:.6f},"
            f"{int(r['oracle_in_bucket'])},{r['oracle_legal_gap']},"
            f"{r['removable_regret']:.6f}"
        )


if __name__ == "__main__":
    main()
