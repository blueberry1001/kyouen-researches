#!/usr/bin/env python3
"""Run exact classification for a targeted list of (parent, child_state) pairs.

Usage:
    python scripts/run_blind_exact_targeted.py <tasks.csv> [max_workers] [timeout_seconds]

Input CSV columns:
    parent,state

Output:
    Appends to results/10x10/blind_probe_children/exact_<parent>_batch<N>.csv
    Skips states already present in any exact CSV for the parent.
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


def find_batch(parent: str, state: str) -> int:
    """Find which batch file contains the given child state."""
    safe = safe_parent(parent)
    for bp in sorted(CHILDREN_DIR.glob(f'children_{safe}_batch*.txt')):
        with bp.open() as f:
            for line in f:
                if line.strip() == state:
                    stem = bp.stem
                    return int(stem.split('_batch')[-1])
    raise ValueError(f"State {state} not found in any batch for parent {parent}")


def load_existing_exact(parent: str) -> set[str]:
    """Load set of state strings already classified for parent."""
    safe = safe_parent(parent)
    found = set()
    for ep in CHILDREN_DIR.glob(f'exact_{safe}_batch*.csv'):
        with ep.open(newline='') as f:
            for r in csv.DictReader(f):
                found.add(r['state'])
    return found


def run_child(state: str, timeout: float | None = None) -> tuple[str, str, int, float]:
    """Run exact search on a single child state. Returns (state, stdout, rc, elapsed)."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(state + '\n')
        tmp = Path(f.name)
    try:
        cmd = [
            'wsl', 'bash', '-c',
            f"cd {wsl_path(REPO_ROOT)} && {wsl_path(SOLVER)} {wsl_path(tmp)} {SHRINK} {LOAD} 0 0"
        ]
        start = time.time()
        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
            rc = proc.returncode
        except subprocess.TimeoutExpired as e:
            rc = 124
            proc = e
        elapsed = time.time() - start
        stdout = proc.stdout.decode('utf-8', errors='replace') if proc.stdout else ''
        return state, stdout, rc, elapsed
    finally:
        tmp.unlink(missing_ok=True)


def append_exact_row(parent: str, batch: int, row: dict):
    """Append a result row to the appropriate exact batch CSV."""
    safe = safe_parent(parent)
    out_file = CHILDREN_DIR / f'exact_{safe}_batch{batch}.csv'
    fieldnames = ['state', 'outcome', 'visited', 'maxdepth', 'memo', 'seconds']
    exists = out_file.exists() and out_file.stat().st_size > 0
    with out_file.open('a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            w.writeheader()
        w.writerow(row)


def main():
    if len(sys.argv) < 2:
        print("Usage: run_blind_exact_targeted.py <tasks.csv> [max_workers] [timeout_seconds]")
        sys.exit(2)
    tasks_path = Path(sys.argv[1])
    max_workers = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    timeout = int(sys.argv[3]) if len(sys.argv) > 3 else 600

    # Read tasks
    tasks = []
    with tasks_path.open(newline='') as f:
        for r in csv.DictReader(f):
            parent = r['parent'].strip()
            state = r['state'].strip()
            tasks.append((parent, state))

    # Deduplicate and skip already classified
    existing_by_parent = {}
    skipped = 0
    filtered_tasks = []
    for parent, state in tasks:
        if parent not in existing_by_parent:
            existing_by_parent[parent] = load_existing_exact(parent)
        if state in existing_by_parent[parent]:
            skipped += 1
            continue
        filtered_tasks.append((parent, state))

    print(f"Tasks: {len(tasks)}, skipped (already exact): {skipped}, to run: {len(filtered_tasks)}")
    if not filtered_tasks:
        print("Nothing to run.")
        return

    # Resolve batch for each task
    task_info = []
    for parent, state in filtered_tasks:
        try:
            batch = find_batch(parent, state)
            task_info.append((parent, state, batch))
        except ValueError as e:
            print(f"WARNING: {e}")

    errors = []
    timeouts = []
    completed = 0
    overall_start = time.time()

    with ProcessPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(run_child, state, timeout): (parent, state, batch) for parent, state, batch in task_info}
        for fut in as_completed(futures):
            parent, state, batch = futures[fut]
            state_out, stdout, rc, elapsed = fut.result()
            completed += 1
            print(f"  [{completed}/{len(task_info)}] {parent} {state} rc={rc} elapsed={elapsed:.1f}s")
            if rc == 0:
                reader = csv.DictReader(io.StringIO(stdout))
                rows = list(reader)
                if rows:
                    append_exact_row(parent, batch, rows[0])
                else:
                    errors.append(f"{parent} {state}: no output rows")
            elif rc == -124 or rc == 124:
                timeouts.append((parent, state, batch, elapsed))
            else:
                errors.append(f"{parent} {state}: rc={rc}\n{stdout[:500]}")

    overall = time.time() - overall_start
    print(f"Done in {overall:.1f}s. Completed: {completed}, errors: {len(errors)}, timeouts: {len(timeouts)}")

    if timeouts:
        timeout_csv = CHILDREN_DIR / f'timeouts_{tasks_path.stem}.csv'
        with timeout_csv.open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=['parent', 'state', 'batch', 'elapsed'])
            w.writeheader()
            for parent, state, batch, elapsed in timeouts:
                w.writerow({'parent': parent, 'state': state, 'batch': batch, 'elapsed': elapsed})
        print(f"Wrote timeouts to {timeout_csv}")

    if errors:
        err_file = CHILDREN_DIR / f'errors_{tasks_path.stem}.txt'
        with err_file.open('w') as f:
            for e in errors:
                f.write(e)
                f.write('\n')
        print(f"Wrote errors to {err_file}")


if __name__ == '__main__':
    main()
