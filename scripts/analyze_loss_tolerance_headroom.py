#!/usr/bin/env python3
"""Quantify oracle headroom from relaxing minimum legal-move count among known LOSS children.

This is deliberately a ceiling analysis, not a deployable ordering rule: for each parent and
tolerance k, it allows an oracle to choose the cheapest exact LOSS among children whose
legal_move_count <= (minimum legal_move_count among LOSS children) + k.

The input dataset contains LOSS children only. Therefore band sizes below are LOSS-only and
must not be interpreted as the number of root children a real solver would need to inspect.
"""

from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from pathlib import Path

DATA = Path("results/10x10/parent-benchmark/loss_proof_cost_dataset.csv")
KS = (0, 1, 2, 3, 4, 5, 6, 8, 10, 13)
EPS = 1e-12


def median(xs):
    return statistics.median(xs) if xs else float("nan")


def main() -> None:
    by_parent = defaultdict(list)
    with DATA.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["exact_visited"] = int(row["exact_visited"])
            row["legal_move_count"] = int(row["legal_move_count"])
            row["native_rank"] = int(row["native_rank"])
            row["move_id"] = int(row["move_id"])
            by_parent[row["parent"]].append(row)

    parent_info = {}
    for parent, rows in by_parent.items():
        min_legal = min(r["legal_move_count"] for r in rows)
        global_row = min(rows, key=lambda r: (r["exact_visited"], r["move_id"]))
        native_row = min(rows, key=lambda r: (r["native_rank"], r["move_id"]))
        global_cost = global_row["exact_visited"]
        native_cost = native_row["exact_visited"]
        parent_info[parent] = {
            "rows": rows,
            "min_legal": min_legal,
            "global_row": global_row,
            "native_row": native_row,
            "global_cost": global_cost,
            "native_cost": native_cost,
            "native_ratio": native_cost / global_cost,
            "global_gap": global_row["legal_move_count"] - min_legal,
        }

    print("legal_move_count tolerance-band oracle headroom")
    print(f"parents={len(parent_info)}")
    print("NOTE: band_size is LOSS-only; real solver candidate burden can be larger because WIN children are absent.")
    print()
    print("k,oracle_covered,median_band_oracle/global,median_loss_band_size,max_loss_band_size,"
          "native_regret_parents_improvable,median_regret_fraction_removable")

    for k in KS:
        ratios = []
        sizes = []
        covered = 0
        removable = []
        improvable = 0
        for info in parent_info.values():
            threshold = info["min_legal"] + k
            band = [r for r in info["rows"] if r["legal_move_count"] <= threshold]
            band_cost = min(r["exact_visited"] for r in band)
            ratio = band_cost / info["global_cost"]
            ratios.append(ratio)
            sizes.append(len(band))
            if info["global_gap"] <= k:
                covered += 1

            regret = info["native_cost"] - info["global_cost"]
            if regret > 0:
                gain = info["native_cost"] - band_cost
                frac = max(0.0, min(1.0, gain / regret))
                removable.append(frac)
                if gain > 0:
                    improvable += 1

        print(
            f"{k},{covered}/{len(parent_info)},{median(ratios):.6f},"
            f"{median(sizes):.1f},{max(sizes)},{improvable}/{len(removable)},"
            f"{median(removable):.6f}"
        )

    print("\nparent oracle legal-count gaps")
    print("parent,min_legal,global_move,global_gap,native_move,native_ratio")
    for parent in sorted(parent_info):
        info = parent_info[parent]
        print(
            f"{parent},{info['min_legal']},{info['global_row']['move_id']},"
            f"{info['global_gap']},{info['native_row']['move_id']},{info['native_ratio']:.6f}"
        )


if __name__ == "__main__":
    main()
