#!/usr/bin/env python3
"""Summarize preregistered below-root instrumentation raw rows.

Recursive subtree visited deltas are intentionally interpreted only within the
same parent depth; they are never summed across depths.  Unique work location is
reported from expanded/total visited, matching amendment 1.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def ratio(a: int, b: int) -> float | None:
    return a / b if b else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", type=Path)
    ap.add_argument("--min-mass", type=float, default=0.01,
                    help="show depth rows carrying at least this fraction of unique visited work")
    args = ap.parse_args()

    with args.csv.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    by_state: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        by_state[r["state"]].append(r)

    report: dict[str, object] = {"parents": {}}
    for state, rs in by_state.items():
        depth_rows = [r for r in rs if r["depth"] != "TOTAL"]
        total = next(r for r in rs if r["depth"] == "TOTAL")
        visited = int(total["visited"])
        active = []
        for r in depth_rows:
            expanded = int(r["expanded"])
            if not expanded:
                continue
            unique_mass = ratio(expanded, visited) or 0.0
            work_win = int(r["work_into_win_child"])
            work_loss = int(r["work_into_loss_child"])
            calls_win = int(r["calls_into_win_child"])
            calls_loss = int(r["calls_into_loss_child"])
            win_nodes = int(r["win_nodes"])
            entry_get = int(r["entry_get"])
            entry_hits = int(r["entry_hit_loss"]) + int(r["entry_hit_win"])
            child_get = int(r["child_get"])
            child_hits = int(r["child_hit_loss"]) + int(r["child_hit_win"])
            rec_calls = calls_win + calls_loss
            late_hits = int(r["late_entry_hit_win"]) + int(r["late_entry_hit_loss"])
            item = {
                "depth": int(r["depth"]),
                "expanded": expanded,
                "unique_visited_fraction": unique_mass,
                "failed_win_fraction": ratio(work_win, work_win + work_loss),
                "mean_win_cutoff_index": ratio(int(r["cutoff_index_sum"]), win_nodes),
                "late_entry_hit_fraction": ratio(late_hits, rec_calls),
                "entry_hit_rate": ratio(entry_hits, entry_get),
                "child_prefetch_hit_rate": ratio(child_hits, child_get),
                "win_nodes": win_nodes,
                "loss_nodes": int(r["loss_nodes"]),
                "recursive_calls": rec_calls,
            }
            if unique_mass >= args.min_mass:
                active.append(item)
        report["parents"][state] = {
            "outcome": total["outcome"],
            "visited": visited,
            "maxdepth": int(total["maxdepth"]),
            "memo": int(total["memo"]),
            "depths_at_or_above_min_mass": active,
        }

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
