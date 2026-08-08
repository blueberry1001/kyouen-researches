#!/usr/bin/env python3
"""Run exact classification on one children batch for blind validation.

Usage: python scripts/run_blind_exact_batch.py <parent> <batch_index>

Uses shrink=0, load=90 for full exact search.
"""
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOLVER = REPO_ROOT / 'scripts' / 'probe_cert_solver'
CHILDREN_DIR = REPO_ROOT / 'results' / '10x10' / 'blind_probe_children'
OUT_DIR = CHILDREN_DIR

SHRINK = 0
LOAD = 90


def wsl_path(p: Path) -> str:
    p = p.resolve()
    parts = p.parts
    drive = parts[0].rstrip(':\\').lower()
    return f"/mnt/{drive}/" + "/".join(parts[1:]).replace('\\', '/')


def main():
    if len(sys.argv) != 3:
        print("Usage: run_blind_exact_batch.py <parent> <batch_index>")
        sys.exit(2)
    parent = sys.argv[1]
    batch_index = int(sys.argv[2])
    safe_parent = parent.replace(',', '_')

    in_file = CHILDREN_DIR / f"children_{safe_parent}_batch{batch_index}.txt"
    if not in_file.exists():
        print(f"Input file missing: {in_file}")
        sys.exit(1)

    out_file = OUT_DIR / f"exact_{safe_parent}_batch{batch_index}.csv"
    err_file = OUT_DIR / f"exact_{safe_parent}_batch{batch_index}.err"

    cmd = [
        'wsl', 'bash', '-c',
        f"cd {wsl_path(REPO_ROOT)} && {wsl_path(SOLVER)} {wsl_path(in_file)} {SHRINK} {LOAD} 0 0"
    ]
    start = time.time()
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    elapsed = time.time() - start
    out_file.write_bytes(proc.stdout)
    err_file.write_bytes(proc.stderr)
    print(f"{parent} batch {batch_index}: rc={proc.returncode} elapsed={elapsed:.1f}s")
    print(f"  out={out_file} err={err_file}")


if __name__ == '__main__':
    main()
