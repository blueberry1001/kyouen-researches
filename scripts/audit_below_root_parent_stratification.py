#!/usr/bin/env python3
"""Reject below-root diagnostic CSVs that cannot support Amendment 2 ordering-waste claims.

The pooled child-outcome counters are descriptive only.  A valid
avoidable_ordering_work_share requires parent-outcome stratified work counters.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

REQUIRED = {
    "win_parent_work_into_win_child",
    "win_parent_work_into_loss_child",
    "loss_parent_work_into_win_child",
    "win_parent_calls_into_win_child",
    "win_parent_calls_into_loss_child",
    "loss_parent_calls_into_win_child",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", type=Path)
    args = ap.parse_args()

    with args.csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = set(reader.fieldnames or ())
        rows = list(reader)

    missing = sorted(REQUIRED - fields)
    if missing:
        print("INVALID_FOR_ORDERING_WASTE: missing parent-outcome-stratified columns:")
        for name in missing:
            print(f"  - {name}")
        print(
            "Pooled work_into_win_child/(work_into_win_child+work_into_loss_child) "
            "must not be interpreted as avoidable ordering work."
        )
        return 2

    errors: list[str] = []
    checked = 0
    for i, row in enumerate(rows, start=2):
        if row.get("depth") == "TOTAL":
            continue
        checked += 1
        pooled_win = int(row["work_into_win_child"])
        pooled_loss = int(row["work_into_loss_child"])
        win_win = int(row["win_parent_work_into_win_child"])
        win_loss = int(row["win_parent_work_into_loss_child"])
        loss_win = int(row["loss_parent_work_into_win_child"])
        if pooled_win != win_win + loss_win:
            errors.append(
                f"line {i}: work_into_win_child={pooled_win} != "
                f"win_parent_work_into_win_child+loss_parent_work_into_win_child="
                f"{win_win + loss_win}"
            )
        if pooled_loss != win_loss:
            errors.append(
                f"line {i}: work_into_loss_child={pooled_loss} != "
                f"win_parent_work_into_loss_child={win_loss}"
            )

    if errors:
        print("INVALID_COUNTER_IDENTITIES")
        for error in errors[:20]:
            print(error)
        if len(errors) > 20:
            print(f"... and {len(errors) - 20} more")
        return 3

    print(f"PASS: {checked} depth rows support parent-stratified ordering-waste analysis")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
