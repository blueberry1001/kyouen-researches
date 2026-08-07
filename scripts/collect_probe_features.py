#!/usr/bin/env python3
"""Collect probe features for 10x10 determined positions using WSL probe_cert_solver."""
import csv
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOLVER = REPO_ROOT / 'scripts' / 'probe_cert_solver'
STATE_FILE = REPO_ROOT / 'results' / '10x10' / 'eligible_states.txt'
META_FILE = REPO_ROOT / 'results' / '10x10' / 'eligible_states.csv'
OUT_FILE = REPO_ROOT / 'results' / '10x10' / 'probe-features.csv'

DEFAULT_BUDGETS = [10_000, 100_000, 1_000_000, 5_000_000, 10_000_000]


def wsl_path(p: Path) -> str:
    """Convert Windows path to WSL /mnt/... path."""
    p = p.resolve()
    parts = p.parts
    drive = parts[0].rstrip(':\\').lower()
    return f"/mnt/{drive}/" + "/".join(parts[1:]).replace('\\', '/')


def run_probe(states_path: Path, budget: int, shrink: int = 3, load: int = 80) -> list[dict]:
    """Run probe_cert_solver on WSL and return parsed CSV rows (data rows only)."""
    sp = wsl_path(states_path)
    cmd = [
        'wsl', 'bash', '-c',
        f"cd {wsl_path(REPO_ROOT)} && {wsl_path(SOLVER)} {sp} {shrink} {load} {budget} 0"
    ]
    start = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start
    if proc.returncode != 0:
        raise RuntimeError(f"probe_cert_solver failed for budget={budget}: {proc.stderr[:500]}")
    reader = csv.DictReader(proc.stdout.splitlines())
    rows = []
    for r in reader:
        r['probe_budget'] = budget
        r['probe_elapsed'] = elapsed
        rows.append(r)
    return rows


def states_to_run(states: list[str], done: set[tuple[str, int]], budget: int) -> list[str]:
    return [s for s in states if (s, budget) not in done]


def load_done(out_path: Path) -> set[tuple[str, int]]:
    """Load already-completed (state, budget) pairs."""
    done = set()
    if not out_path.exists():
        return done
    with open(out_path, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            done.add((r['state'], int(r['probe_budget'])))
    return done


def main():
    budgets = [int(x) for x in sys.argv[1].split(',')] if len(sys.argv) > 1 else DEFAULT_BUDGETS
    shrink = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    load = int(sys.argv[3]) if len(sys.argv) > 3 else 80

    with open(STATE_FILE, encoding='utf-8') as f:
        states = [line.strip() for line in f if line.strip()]

    done = load_done(OUT_FILE)
    print(f"Eligible states: {len(states)}, already done: {len(done)}, budgets: {budgets}")

    fieldnames = [
        'state', 'outcome', 'stones', 'final_visited', 'parent', 'classification_source',
        'probe_budget', 'probe_outcome', 'visited', 'maxdepth', 'memo', 'seconds',
        'memo_per_visited', 'visited_per_second',
    ] + [f'depth_visited_{i}' for i in range(20)] \
      + [f'memo_used_d{i}' for i in range(9, 22)] \
      + [f'memo_capacity_d{i}' for i in range(9, 22)] \
      + ['probe_elapsed']

    write_header = not OUT_FILE.exists() or OUT_FILE.stat().st_size == 0
    out_f = open(OUT_FILE, 'a', newline='', encoding='utf-8')
    writer = csv.DictWriter(out_f, fieldnames=fieldnames)
    if write_header:
        writer.writeheader()

    meta = {}
    if META_FILE.exists():
        with open(META_FILE, newline='', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                meta[r['state']] = r

    total = len(states) * len(budgets)
    completed = 0
    try:
        for budget in budgets:
            for state in states:
                key = (state, budget)
                if key in done:
                    completed += 1
                    continue
                single = REPO_ROOT / 'results' / '10x10' / '_probe_state.txt'
                with open(single, 'w', encoding='utf-8') as f:
                    f.write(state + '\n')
                rows = run_probe(single, budget, shrink, load)
                for r in rows:
                    r['state'] = r['state'].replace('-', ',')
                    m = meta.get(r['state'], {})
                    r['outcome'] = m.get('outcome', '')
                    r['stones'] = m.get('stones', '')
                    r['final_visited'] = m.get('visited', '')
                    r['parent'] = Path(m.get('source_file', '')).name
                    r['classification_source'] = m.get('classification_source', '')
                    r['probe_outcome'] = r.pop('outcome_probe', r.get('outcome', ''))
                    try:
                        r['memo_per_visited'] = float(r['memo']) / float(r['visited']) if float(r['visited']) else ''
                        r['visited_per_second'] = float(r['visited']) / float(r['seconds']) if float(r['seconds']) else ''
                    except (ValueError, TypeError):
                        r['memo_per_visited'] = ''
                        r['visited_per_second'] = ''
                    for fn in fieldnames:
                        r.setdefault(fn, '')
                    writer.writerow({fn: r[fn] for fn in fieldnames})
                out_f.flush()
                done.add(key)
                completed += 1
                if completed % 50 == 0:
                    print(f"Progress: {completed}/{total} ({100*completed/total:.1f}%)")
    finally:
        out_f.close()
    print(f"Done: {completed}/{total}. Output: {OUT_FILE}")


if __name__ == '__main__':
    main()
