#!/usr/bin/env python3
"""Run exact classification for a range of selected parents using child-level parallelism.

Usage:
    python scripts/run_blind_exact_parents.py <stones> <start> <end> [max_workers]

Selects parents from results/10x10/blind-probe-parent-selection.csv with the given
stones, then classifies batch 0 of each parent using parallel child exact search.
"""
import csv
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SELECTION_FILE = REPO_ROOT / 'results' / '10x10' / 'blind-probe-parent-selection.csv'
CHILDREN_DIR = REPO_ROOT / 'results' / '10x10' / 'blind_probe_children'


def safe_parent(parent: str) -> str:
    return parent.replace(',', '_')


def main():
    if len(sys.argv) < 4:
        print("Usage: run_blind_exact_parents.py <stones> <start> <end> [max_workers]")
        sys.exit(2)
    stones = int(sys.argv[1])
    start = int(sys.argv[2])
    end = int(sys.argv[3])
    max_workers = int(sys.argv[4]) if len(sys.argv) > 4 else 4

    with SELECTION_FILE.open(newline='') as f:
        rows = list(csv.DictReader(f))
    parents = [r['parent'] for r in rows if int(r['stones']) == stones]
    selected = parents[start:end]

    for parent in selected:
        safe = safe_parent(parent)
        out_file = CHILDREN_DIR / f"exact_{safe}_batch0.csv"
        if out_file.exists():
            print(f"Skip existing: {parent}")
            continue
        print(f"Running exact for {parent} ...")
        cmd = [sys.executable, str(REPO_ROOT / 'scripts' / 'run_blind_exact_children_parallel.py'), parent, '0', str(max_workers)]
        proc = subprocess.run(cmd)
        print(f"{parent}: rc={proc.returncode}")


if __name__ == '__main__':
    main()
