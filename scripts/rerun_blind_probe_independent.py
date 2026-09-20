#!/usr/bin/env python3
"""Correct the historical 3-stone blind probe by using a fresh solver per child.

The historical b5172a4 run reused one Solver across a 20-child batch, so the
reported memo feature was cumulative and exactly confounded with input order.
This rerun keeps the same eight batch-0 parents and exact labels but launches a
fresh process for every child. It therefore measures child-local probe state.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RANKINGS = ROOT / "results" / "10x10" / "blind-probe-rankings.csv"
PARENTS = ["2,9,33", "4,9,33", "9,12,33", "9,19,33", "9,23,33", "0,31,36", "0,36,43", "0,36,44"]
BUDGET = 1_000_000
SHRINK = 3
LOAD = 80


def parse_solver_csv(text: str) -> dict[str, str]:
    rows = list(csv.DictReader(text.splitlines()))
    if len(rows) != 1:
        raise RuntimeError(f"expected one solver row, got {len(rows)}")
    return rows[0]


def run_one(solver: Path, row: dict[str, str]) -> dict[str, object]:
    state = row["child_state"].replace("-", ",")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(state + "\n")
        name = f.name
    try:
        p = subprocess.run(
            [str(solver), name, str(SHRINK), str(LOAD), str(BUDGET), "0"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        )
    finally:
        os.unlink(name)
    s = parse_solver_csv(p.stdout)
    return {
        "parent": row["parent"],
        "child_state": row["child_state"],
        "move_index": int(row["move_index"]),
        "exact_outcome": row["outcome"],
        "exact_visited": int(row["exact_visited"]),
        "probe_outcome": s["outcome"],
        "probe_visited": int(s["visited"]),
        "probe_maxdepth": int(s["maxdepth"]),
        "probe_memo": int(s["memo"]),
    }


def first_loss(rows: list[dict[str, object]], key) -> int:
    ordered = sorted(rows, key=key)
    for i, r in enumerate(ordered, 1):
        if r["exact_outcome"] == "LOSS":
            return i
    return len(rows) + 1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--solver", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--raw", type=Path, default=ROOT / "results/10x10/blind-probe-independent-raw.csv")
    ap.add_argument("--summary", type=Path, default=ROOT / "results/10x10/blind-probe-independent-summary.json")
    args = ap.parse_args()

    with RANKINGS.open(newline="", encoding="utf-8") as f:
        source = [r for r in csv.DictReader(f) if int(r["stones"]) == 3 and r["parent"] in PARENTS]
    if len(source) != 160:
        raise RuntimeError(f"expected 160 frozen rows, got {len(source)}")

    out: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(run_one, args.solver, r) for r in source]
        for fut in as_completed(futs):
            out.append(fut.result())

    out.sort(key=lambda r: (PARENTS.index(str(r["parent"])), int(r["move_index"])))
    args.raw.parent.mkdir(parents=True, exist_ok=True)
    fields = ["parent", "child_state", "move_index", "exact_outcome", "exact_visited", "probe_outcome", "probe_visited", "probe_maxdepth", "probe_memo"]
    with args.raw.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(out)

    by_parent: dict[str, list[dict[str, object]]] = {p: [] for p in PARENTS}
    for r in out: by_parent[str(r["parent"])].append(r)

    parent_rows = []
    for parent, rs in by_parent.items():
        losses = sum(r["exact_outcome"] == "LOSS" for r in rs)
        if not losses:
            continue
        memo_desc = first_loss(rs, lambda r: (-int(r["probe_memo"]), int(r["move_index"])))
        visited_desc = first_loss(rs, lambda r: (-int(r["probe_visited"]), int(r["move_index"])))
        maxdepth_desc = first_loss(rs, lambda r: (-int(r["probe_maxdepth"]), int(r["move_index"])))
        solver = first_loss(rs, lambda r: int(r["move_index"]))
        reverse = first_loss(rs, lambda r: -int(r["move_index"]))
        parent_rows.append({
            "parent": parent, "loss_count": losses,
            "memo_desc_first_loss": memo_desc,
            "visited_desc_first_loss": visited_desc,
            "maxdepth_desc_first_loss": maxdepth_desc,
            "solver_first_loss": solver,
            "reverse_first_loss": reverse,
        })

    def med(k: str) -> float:
        return statistics.median(float(r[k]) for r in parent_rows)

    summary = {
        "design": "fresh process / fresh Solver per child; same 160 frozen batch0 children and historical exact labels",
        "parents_with_loss": len(parent_rows),
        "parents": parent_rows,
        "medians": {
            "memo_desc": med("memo_desc_first_loss"),
            "visited_desc": med("visited_desc_first_loss"),
            "maxdepth_desc": med("maxdepth_desc_first_loss"),
            "solver": med("solver_first_loss"),
            "reverse": med("reverse_first_loss"),
            "historical_random": 6.0,
        },
    }
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
