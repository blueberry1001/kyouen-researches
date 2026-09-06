#!/usr/bin/env python3
"""Parallel exact sweep over the frozen holdout task list.

Usage: python scripts/run_holdout_exact_sweep.py <workers> [--timeout S]

- Stride-splits the frozen task list across <workers> processes.
- Each worker runs tasks sequentially with scripts/run_holdout_exact_one.py
  (frozen binary, shrink 0 / load 90, unbounded).
- Per-worker CSV: results/10x10/blind-probe-holdout/exact_outcomes_w<N>.csv.
- Resume-safe: skips (parent, state) already in the worker CSV.
- Per-task timeout (default 3600s); timeouts recorded in exact_timeouts.csv.
- Untracked outputs (never committed until merged by merge_holdout_exact.py).
"""

from __future__ import annotations

import csv
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "results" / "10x10" / "blind-probe-holdout"
TASK_LIST = OUT_DIR / "exact_task_list.csv"
TIMEOUT_CSV = OUT_DIR / "exact_timeouts.csv"


def load_done(worker: int) -> set[tuple[str, str]]:
    p = OUT_DIR / f"exact_outcomes_w{worker}.csv"
    if not p.exists():
        return set()
    with p.open(newline="", encoding="utf-8") as f:
        return {(r["parent"], r["state"].replace(",", "-")) for r in csv.DictReader(f)}


def run_task(task: tuple[str, str, str, str, int], timeout: float) -> tuple[str, str]:
    parent, batch, pos, state, worker = task
    out = OUT_DIR / f"exact_outcomes_w{worker}.csv"
    cmd = [sys.executable, "scripts/run_holdout_exact_one.py",
           parent, batch, pos, state, str(out)]
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True,
                              capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return ("TIMEOUT", f"{parent} {state} after {timeout}s")
    dt = time.time() - t0
    if proc.returncode != 0:
        return ("FAIL", f"{parent} {state} rc={proc.returncode} {proc.stderr[-300:]}")
    line = (proc.stdout or "").strip().splitlines()
    return ("OK", f"{parent} {state} {line[-1] if line else ''} [{dt:.0f}s]")


def main() -> None:
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    timeout = float(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else 3600.0
    if "--timeout" in sys.argv:
        timeout = float(sys.argv[sys.argv.index("--timeout") + 1])
    with TASK_LIST.open(newline="", encoding="utf-8") as f:
        tasks = list(csv.DictReader(f))
    print(f"tasks={len(tasks)} workers={workers} timeout={timeout}s")
    jobs: list[tuple[str, str, str, str, int]] = []
    for i, t in enumerate(tasks):
        w = i % workers
        if (t["parent"], t["state"].replace(",", "-")) in load_done(w):
            continue
        jobs.append((t["parent"], t["batch"], t["pos"], t["state"], w))
    print(f"remaining={len(jobs)}")
    if not jobs:
        return
    done = 0
    fails: list[str] = []
    timeouts: list[str] = []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(run_task, j, timeout): j for j in jobs}
        for fut in as_completed(futs):
            status, msg = fut.result()
            done += 1
            print(f"[{done}/{len(jobs)}] {status} {msg} elapsed={(time.time() - t0) / 60:.0f}m")
            if status == "FAIL":
                fails.append(msg)
            elif status == "TIMEOUT":
                timeouts.append(msg)
    print(f"sweep done: ok={done - len(fails) - len(timeouts)} fail={len(fails)} timeout={len(timeouts)}")
    if timeouts:
        new = not TIMEOUT_CSV.exists()
        with TIMEOUT_CSV.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["event"])
            for m in timeouts:
                w.writerow([m])
    if fails:
        (OUT_DIR / "exact_failures.log").write_text("\n".join(fails) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
