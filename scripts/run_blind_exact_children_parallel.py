#!/usr/bin/env python3
"""Run exact classification for each child of a parent in parallel.

This is much faster than batch-level exact when many children are independent,
because it utilises multiple cores and avoids the long sequential run.

Usage:
    python scripts/run_blind_exact_children_parallel.py <parent> <batch_index> [max_workers]

Output:
    results/10x10/blind_probe_children/exact_<parent>_batch<batch>.csv
"""
import csv
import io
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOLVER = REPO_ROOT / 'scripts' / 'probe_cert_solver'
CHILDREN_DIR = REPO_ROOT / 'results' / '10x10' / 'blind_probe_children'
SHRINK = 0
LOAD = 90


def safe_parent(parent: str) -> str:
    return parent.replace(',', '_')


def wsl_path(p: Path) -> str:
    p = p.resolve()
    parts = p.parts
    drive = parts[0].rstrip(':\\').lower()
    return f"/mnt/{drive}/" + "/".join(parts[1:]).replace('\\', '/')


def run_child(child_state: str) -> tuple[str, str, int, float]:
    """Run exact search on a single child state. Returns (state, stdout, rc, elapsed)."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(child_state + '\n')
        tmp = Path(f.name)
    try:
        cmd = [
            'wsl', 'bash', '-c',
            f"cd {wsl_path(REPO_ROOT)} && {wsl_path(SOLVER)} {wsl_path(tmp)} {SHRINK} {LOAD} 0 0"
        ]
        start = time.time()
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        elapsed = time.time() - start
        return child_state, proc.stdout.decode('utf-8', errors='replace'), proc.returncode, elapsed
    finally:
        tmp.unlink(missing_ok=True)


def main():
    if len(sys.argv) < 3:
        print("Usage: run_blind_exact_children_parallel.py <parent> <batch_index> [max_workers]")
        sys.exit(2)
    parent = sys.argv[1]
    batch_index = int(sys.argv[2])
    max_workers = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    safe = safe_parent(parent)

    batch_file = CHILDREN_DIR / f"children_{safe}_batch{batch_index}.txt"
    if not batch_file.exists():
        print(f"Batch file missing: {batch_file}")
        sys.exit(1)

    out_file = CHILDREN_DIR / f"exact_{safe}_batch{batch_index}.csv"
    err_file = CHILDREN_DIR / f"exact_{safe}_batch{batch_index}.err"

    children = [line.strip() for line in batch_file.read_text().splitlines() if line.strip()]
    print(f"{parent} batch {batch_index}: {len(children)} children, max_workers={max_workers}")

    header = None
    rows = []
    errors = []
    completed = 0
    overall_start = time.time()
    with ProcessPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(run_child, state): state for state in children}
        for fut in as_completed(futures):
            state, stdout, rc, elapsed = fut.result()
            completed += 1
            print(f"  [{completed}/{len(children)}] {state} rc={rc} elapsed={elapsed:.1f}s")
            if rc != 0:
                errors.append(f"{state} rc={rc}\n{stdout}")
                continue
            reader = csv.DictReader(io.StringIO(stdout))
            if header is None:
                header = reader.fieldnames
            for r in reader:
                rows.append(r)
    overall = time.time() - overall_start

    if header and rows:
        with out_file.open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=header)
            w.writeheader()
            w.writerows(rows)
        print(f"Wrote {out_file}")
    else:
        print("No output rows generated")

    with err_file.open('w') as f:
        f.write(f"overall_elapsed={overall:.1f}s\n")
        f.write(f"errors={len(errors)}\n")
        for e in errors:
            f.write(e)
            f.write('\n')
    print(f"Done in {overall:.1f}s")


if __name__ == '__main__':
    main()
