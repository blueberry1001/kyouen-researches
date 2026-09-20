#!/usr/bin/env python3
"""Run exact classification for a list of blind-validation parents in parallel.

Usage:
    python scripts/run_blind_exact_all.py <stones> <start> <end> [max_parallel]

Reads parents from results/10x10/blind-probe-parent-selection.csv,
selects those with the given stones between start (inclusive) and end (exclusive),
and runs exact classification on batch 0 (or all batches if --all-batches).

Example:
    python scripts/run_blind_exact_all.py 3 0 6 2
"""
import csv
import subprocess
import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

REPO_ROOT = Path(__file__).resolve().parents[1]
SELECTION_FILE = REPO_ROOT / 'results' / '10x10' / 'blind-probe-parent-selection.csv'
CHILDREN_DIR = REPO_ROOT / 'results' / '10x10' / 'blind_probe_children'


def safe_parent(parent: str) -> str:
    return parent.replace(',', '_')


def exact_exists(parent: str, batch: int = 0) -> bool:
    safe = safe_parent(parent)
    return (CHILDREN_DIR / f'exact_{safe}_batch{batch}.csv').exists()


def run_one(parent: str, batch: int) -> tuple[str, int, int]:
    cmd = [sys.executable, str(REPO_ROOT / 'scripts' / 'run_blind_exact_batch.py'), parent, str(batch)]
    proc = subprocess.run(cmd)
    return parent, batch, proc.returncode


def main():
    if len(sys.argv) < 4:
        print("Usage: run_blind_exact_all.py <stones> <start> <end> [max_parallel] [--all-batches]")
        sys.exit(2)
    stones = int(sys.argv[1])
    start = int(sys.argv[2])
    end = int(sys.argv[3])
    max_parallel = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else 1
    all_batches = '--all-batches' in sys.argv

    with SELECTION_FILE.open(newline='') as f:
        rows = list(csv.DictReader(f))
    parents = [r['parent'] for r in rows if int(r['stones']) == stones]
    selected = parents[start:end]

    tasks = []
    for p in selected:
        if all_batches:
            safe = safe_parent(p)
            batch_files = sorted(CHILDREN_DIR.glob(f'children_{safe}_batch*.txt'))
            batches = [int(bp.stem.split('_batch')[-1]) for bp in batch_files]
        else:
            batches = [0]
        for b in batches:
            if exact_exists(p, b):
                print(f"Skip existing exact: {p} batch {b}")
                continue
            tasks.append((p, b))

    if not tasks:
        print("No tasks to run.")
        return

    print(f"Running {len(tasks)} exact tasks with max_parallel={max_parallel}")
    completed = 0
    with ProcessPoolExecutor(max_workers=max_parallel) as ex:
        futures = {ex.submit(run_one, p, b): (p, b) for p, b in tasks}
        for fut in as_completed(futures):
            p, b, rc = fut.result()
            completed += 1
            print(f"[{completed}/{len(tasks)}] exact {p} batch {b}: rc={rc}")


if __name__ == '__main__':
    main()
