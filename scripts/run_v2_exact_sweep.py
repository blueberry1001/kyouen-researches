#!/usr/bin/env python3
"""Parallel exact sweep over the frozen V2 clean holdout task list.

Usage: python scripts/run_v2_exact_sweep.py <workers> [--timeout S]
"""

from __future__ import annotations

import csv
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "results" / "10x10" / "clean-holdout-v2"
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


def worker_loop(arg: tuple[list[tuple[str, str, str, str, int]], float]) -> list[tuple[str, str]]:
    assigned_tasks, timeout = arg
    results = []
    for itm in assigned_tasks:
        status, msg = run_task(itm, timeout)
        print(f"[w{itm[4]}] {status} {msg}", flush=True)
        if status == "TIMEOUT":
            with TIMEOUT_CSV.open("a", newline="", encoding="utf-8") as tf:
                tf.write(f"{itm[0]},{itm[3]}\n")
        results.append((status, msg))
    return results


def main() -> None:
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    timeout = 3600.0
    if "--timeout" in sys.argv:
        timeout = float(sys.argv[sys.argv.index("--timeout") + 1])

    with TASK_LIST.open(newline="", encoding="utf-8") as f:
        tasks = list(csv.DictReader(f))

    print(f"tasks={len(tasks)} workers={workers} timeout={timeout}s")

    per_worker_tasks: list[list[tuple[str, str, str, str, int]]] = [[] for _ in range(workers)]
    for i, t in enumerate(tasks):
        w = i % workers
        per_worker_tasks[w].append((t["parent"], t["batch"], t["batch_position"], t["state"], w))

    work_items: list[tuple[str, str, str, str, int]] = []
    total_done = 0
    for w in range(workers):
        done = load_done(w)
        total_done += len(done)
        for item in per_worker_tasks[w]:
            key = (item[0], item[3].replace(",", "-"))
            if key not in done:
                work_items.append(item)

    print(f"already_done={total_done} remaining={len(work_items)}")
    if not work_items:
        print("all tasks complete")
        return

    worker_chunks = [[] for _ in range(workers)]
    for itm in work_items:
        worker_chunks[itm[4]].append(itm)

    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(worker_loop, (chunk, timeout)) for chunk in worker_chunks if chunk]
        for f in as_completed(futures):
            f.result()

    print(f"Sweep complete in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
