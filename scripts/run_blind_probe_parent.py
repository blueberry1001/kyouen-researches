#!/usr/bin/env python3
"""Run all probe batches for a single blind-validation parent.

Usage: python scripts/run_blind_probe_parent.py <parent> <stones>
"""
import csv
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOLVER = REPO_ROOT / 'scripts' / 'probe_cert_solver'
CHILDREN_DIR = REPO_ROOT / 'results' / '10x10' / 'blind_probe_children'
OUT_DIR = CHILDREN_DIR

FIXED_BUDGETS = {3: 1_000_000, 4: 10_000, 5: 10_000}
SHRINK = 3
LOAD = 80


def wsl_path(p: Path) -> str:
    p = p.resolve()
    parts = p.parts
    drive = parts[0].rstrip(':\\').lower()
    return f"/mnt/{drive}/" + "/".join(parts[1:]).replace('\\', '/')


def main():
    if len(sys.argv) != 3:
        print("Usage: run_blind_probe_parent.py <parent> <stones>")
        sys.exit(2)
    parent = sys.argv[1]
    stones = int(sys.argv[2])
    budget = FIXED_BUDGETS[stones]
    safe_parent = parent.replace(',', '_')

    batch_files = sorted(CHILDREN_DIR.glob(f"children_{safe_parent}_batch*.txt"))
    if not batch_files:
        print(f"No children batch files for {parent}")
        sys.exit(1)

    results = []
    for batch_file in batch_files:
        batch_index = int(batch_file.stem.split('batch')[-1])
        out_file = OUT_DIR / f"probe_{safe_parent}_batch{batch_index}_{budget}.csv"
        err_file = OUT_DIR / f"probe_{safe_parent}_batch{batch_index}_{budget}.err"

        cmd = [
            'wsl', 'bash', '-c',
            f"cd {wsl_path(REPO_ROOT)} && {wsl_path(SOLVER)} {wsl_path(batch_file)} {SHRINK} {LOAD} {budget} 0"
        ]
        start = time.time()
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        elapsed = time.time() - start
        out_file.write_bytes(proc.stdout)
        err_file.write_bytes(proc.stderr)
        results.append({
            'parent': parent,
            'batch': batch_index,
            'budget': budget,
            'rc': proc.returncode,
            'elapsed': elapsed,
        })
        print(f"{parent} batch {batch_index}: rc={proc.returncode} elapsed={elapsed:.1f}s")

    summary_file = OUT_DIR / f"probe_summary_{safe_parent}_{budget}.json"
    import json
    summary_file.write_text(json.dumps(results, indent=2))
    print(f"Summary: {summary_file}")


if __name__ == '__main__':
    main()
