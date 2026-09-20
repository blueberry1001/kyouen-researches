#!/usr/bin/env python3
"""Run a single probe budget batch for blind validation.

Usage: python scripts/run_blind_probe_batch.py <parent> <batch_index> <stones>

Stones determines fixed rule budget:
  3 -> memo 1M descending
  4 -> memo 10k ascending
  5 -> maxdepth 10k descending
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
    if len(sys.argv) != 4:
        print("Usage: run_blind_probe_batch.py <parent> <batch_index> <stones>")
        sys.exit(2)
    parent = sys.argv[1]
    batch_index = int(sys.argv[2])
    stones = int(sys.argv[3])
    budget = FIXED_BUDGETS[stones]

    safe_parent = parent.replace(',', '_')
    in_file = CHILDREN_DIR / f"children_{safe_parent}_batch{batch_index}.txt"
    if not in_file.exists():
        print(f"Input file missing: {in_file}")
        sys.exit(1)

    out_file = OUT_DIR / f"probe_{safe_parent}_batch{batch_index}_{budget}.csv"
    err_file = OUT_DIR / f"probe_{safe_parent}_batch{batch_index}_{budget}.err"

    ranking_generated_at = time.strftime('%Y-%m-%dT%H:%M:%S%z')
    cmd = [
        'wsl', 'bash', '-c',
        f"cd {wsl_path(REPO_ROOT)} && {wsl_path(SOLVER)} {wsl_path(in_file)} {SHRINK} {LOAD} {budget} 0"
    ]
    start = time.time()
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    elapsed = time.time() - start
    out_file.write_bytes(proc.stdout)
    err_file.write_bytes(proc.stderr)
    print(f"{parent} batch {batch_index} budget {budget}: rc={proc.returncode} elapsed={elapsed:.1f}s")
    print(f"  out={out_file} err={err_file}")


if __name__ == '__main__':
    main()
