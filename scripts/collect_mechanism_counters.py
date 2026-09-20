#!/usr/bin/env python3
"""Collect full solver counters for a stratified sample of LOSS and WIN children.

Uses the original 11 holdout parents where exact outcomes are known.
Captures depth-visited and memo-by-depth counters from the solver's CSV output.
"""

from __future__ import annotations

import csv
import multiprocessing as mp
import random
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_CSV = REPO_ROOT / "results" / "10x10" / "mechanism_counters_sample.csv"

SOLVER_BIN = REPO_ROOT / "tmp-kb" / "probe_holdout_native"
BUDGET = 1_000_000
SHRINK = 3
LOAD = 80
SEED = 20260907


def run_probe(state: str) -> dict[str, str]:
    with tempfile.NamedTemporaryFile(
        "w", suffix=".txt", delete=False, dir=SOLVER_BIN.parent, encoding="utf-8"
    ) as tmp:
        tmp.write(state + "\n")
        tmp_path = Path(tmp.name)
    try:
        cmd = [str(SOLVER_BIN), str(tmp_path), str(SHRINK), str(LOAD), str(BUDGET), "0"]
        proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True, capture_output=True)
    finally:
        tmp_path.unlink(missing_ok=True)

    if proc.returncode != 0:
        raise RuntimeError(f"probe failed for {state}: rc={proc.returncode}")

    lines = [l for l in proc.stdout.splitlines() if l.strip()]
    # Find the header line and data line
    header_idx = None
    for i, l in enumerate(lines):
        if l.startswith("state,outcome,visited"):
            header_idx = i
            break
    if header_idx is None or header_idx + 1 >= len(lines):
        raise RuntimeError(f"unexpected solver output for {state}")

    reader = csv.DictReader(lines[header_idx:header_idx + 2])
    rows = list(reader)
    if len(rows) != 1:
        raise RuntimeError(f"expected 1 data row for {state}, got {len(rows)}")
    return rows[0]


def load_original_tasks_with_outcomes() -> list[dict[str, str]]:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from analyze_probe_holdout_preregistered import load_parents, load_children, load_exact

    tasks = []
    for p in load_parents():
        children = load_children(p)
        exact = load_exact(p)
        for c in children:
            tasks.append({
                "parent": p,
                "state": c,
                "outcome": exact[c],
            })
    return tasks


def main():
    tasks = load_original_tasks_with_outcomes()
    loss_tasks = [t for t in tasks if t["outcome"] == "LOSS"]
    win_tasks = [t for t in tasks if t["outcome"] == "WIN"]
    print(f"Original holdout: {len(loss_tasks)} LOSS, {len(win_tasks)} WIN")

    rng = random.Random(SEED)
    sample_size = min(100, len(loss_tasks), len(win_tasks))
    sampled_loss = rng.sample(loss_tasks, sample_size)
    sampled_win = rng.sample(win_tasks, sample_size)
    sample = sampled_loss + sampled_win
    rng.shuffle(sample)

    print(f"Running {len(sample)} fresh 1M probes ({sample_size} LOSS + {sample_size} WIN)...")

def collect_task(t: dict[str, str]) -> dict[str, str]:
    row = run_probe(t["state"])
    row["true_outcome"] = t["outcome"]
    row["parent"] = t["parent"]
    return row


def main():
    tasks = load_original_tasks_with_outcomes()
    loss_tasks = [t for t in tasks if t["outcome"] == "LOSS"]
    win_tasks = [t for t in tasks if t["outcome"] == "WIN"]
    print(f"Original holdout: {len(loss_tasks)} LOSS, {len(win_tasks)} WIN")

    rng = random.Random(SEED)
    sample_size = min(100, len(loss_tasks), len(win_tasks))
    sampled_loss = rng.sample(loss_tasks, sample_size)
    sampled_win = rng.sample(win_tasks, sample_size)
    sample = sampled_loss + sampled_win
    rng.shuffle(sample)

    print(f"Running {len(sample)} fresh 1M probes ({sample_size} LOSS + {sample_size} WIN)...")

    fieldnames = None
    rows_out = []

    with mp.Pool(processes=6) as pool:
        for res in pool.imap_unordered(collect_task, sample, chunksize=2):
            if fieldnames is None:
                fieldnames = list(res.keys())
            rows_out.append(res)
            if len(rows_out) % 20 == 0:
                print(f"  completed {len(rows_out)}/{len(sample)}")

    # Ensure deterministic column order
    preferred = ["parent", "state", "true_outcome", "outcome", "visited", "maxdepth", "memo", "seconds"]
    extra = [k for k in fieldnames if k not in preferred]
    final_fields = preferred + sorted(extra)

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=final_fields)
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"Wrote {len(rows_out)} rows to {OUT_CSV}")


if __name__ == "__main__":
    main()
