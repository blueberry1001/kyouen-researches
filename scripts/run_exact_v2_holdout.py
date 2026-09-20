#!/usr/bin/env python3
"""Run exact solve on 10x10 Clean Holdout V2 children.

Parameters: shrink=0, load=90, budget=0 (unbounded).
Supports multiprocessing parallel workers and safe resume.
"""

from __future__ import annotations

import argparse
import csv
import multiprocessing as mp
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
V2_DIR = REPO_ROOT / "results" / "10x10" / "clean-holdout-v2"
TASK_CSV = V2_DIR / "exact_task_list.csv"
OUT_CSV = V2_DIR / "exact_outcomes.csv"

SOLVER_BIN = REPO_ROOT / "tmp-kb" / "probe_holdout_native"
SHRINK = "0"
LOAD = "90"
BUDGET = "0"

FIELDS = [
    "parent", "batch", "batch_position", "state", "outcome",
    "visited", "maxdepth", "memo", "seconds",
]


def solve_one(task: dict[str, str]) -> dict[str, str]:
    state = task["state"]
    with tempfile.NamedTemporaryFile(
        "w", suffix=".txt", delete=False, dir=SOLVER_BIN.parent, encoding="utf-8"
    ) as tmp:
        tmp.write(state + "\n")
        tmp_path = Path(tmp.name)
    try:
        cmd = [str(SOLVER_BIN), str(tmp_path), SHRINK, LOAD, BUDGET, "0"]
        t0 = time.time()
        proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True, capture_output=True)
        dur = time.time() - t0
    finally:
        tmp_path.unlink(missing_ok=True)

    if proc.returncode != 0:
        raise RuntimeError(f"exact solve failed for {state}: rc={proc.returncode}\n{proc.stderr[-500:]}")

    rows = list(csv.DictReader(proc.stdout.splitlines()))
    if len(rows) != 1:
        raise RuntimeError(f"expected 1 row for {state}, got {len(rows)}")
    row = rows[0]
    return {
        "parent": task["parent"],
        "batch": task["batch"],
        "batch_position": task["batch_position"],
        "state": state,
        "outcome": row["outcome"],
        "visited": row["visited"],
        "maxdepth": row["maxdepth"],
        "memo": row["memo"],
        "seconds": row["seconds"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=14)
    args = parser.parse_args()

    if not SOLVER_BIN.exists():
        raise RuntimeError(f"missing {SOLVER_BIN}")

    with TASK_CSV.open(newline="", encoding="utf-8") as f:
        tasks = list(csv.DictReader(f))

    completed = set()
    if OUT_CSV.exists():
        with OUT_CSV.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                completed.add((r["parent"], r["state"]))

    pending = [t for t in tasks if (t["parent"], t["state"]) not in completed]
    print(f"Total tasks: {len(tasks)}, Completed: {len(completed)}, Pending: {len(pending)}")

    if not pending:
        print("All exact solves already complete!")
        return

    t0 = time.time()
    out_file = OUT_CSV.open("a" if completed else "w", newline="", encoding="utf-8")
    writer = csv.DictWriter(out_file, fieldnames=FIELDS)
    if not completed:
        writer.writeheader()

    done_count = len(completed)
    with mp.Pool(processes=args.workers) as pool:
        for res in pool.imap_unordered(solve_one, pending, chunksize=1):
            writer.writerow(res)
            out_file.flush()
            done_count += 1
            if done_count % 10 == 0 or done_count == len(tasks):
                elapsed = time.time() - t0
                speed = (done_count - len(completed)) / elapsed if elapsed > 0 else 0
                print(f"[{done_count}/{len(tasks)}] {res['parent']} {res['state']} -> {res['outcome']} ({res['seconds']}s) total_elapsed={elapsed:.1f}s ({speed:.2f} tasks/s)")

    out_file.close()
    print("Exact solve finished successfully.")


if __name__ == "__main__":
    main()
