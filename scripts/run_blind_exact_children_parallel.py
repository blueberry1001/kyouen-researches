#!/usr/bin/env python3
"""Run exact classification for each child of a parent in parallel, with resume.

Usage:
    python scripts/run_blind_exact_children_parallel.py <parent> <batch_index|all> [max_workers]

Examples:
    python scripts/run_blind_exact_children_parallel.py 2,9,33 1 4
    python scripts/run_blind_exact_children_parallel.py 2,9,33 all 4

Output:
    results/10x10/blind_probe_children/exact_<parent>_batch<batch>.csv

The output CSV is updated atomically after every successfully solved child. Existing
rows are reused on restart, so an interrupted long run resumes from the remaining
children instead of discarding completed work.
"""
import csv
import io
import os
import re
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


def run_child(child_state: str) -> tuple[str, str, str, int, float]:
    """Run exact search on one child.

    Returns (requested_state, stdout, stderr, returncode, elapsed_seconds).
    """
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
        return (
            child_state,
            proc.stdout.decode('utf-8', errors='replace'),
            proc.stderr.decode('utf-8', errors='replace'),
            proc.returncode,
            elapsed,
        )
    finally:
        tmp.unlink(missing_ok=True)


def load_existing(out_file: Path) -> tuple[list[str] | None, dict[str, dict[str, str]]]:
    if not out_file.exists() or out_file.stat().st_size == 0:
        return None, {}
    with out_file.open(newline='') as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        if not header or 'state' not in header:
            raise RuntimeError(f"Existing output has no state column: {out_file}")
        rows: dict[str, dict[str, str]] = {}
        for row in reader:
            state = row.get('state', '').strip()
            if not state:
                raise RuntimeError(f"Existing output contains an empty state: {out_file}")
            if state in rows:
                raise RuntimeError(f"Existing output contains duplicate state {state}: {out_file}")
            rows[state] = row
    return header, rows


def write_atomic(
    out_file: Path,
    header: list[str],
    rows_by_state: dict[str, dict[str, str]],
    child_order: list[str],
) -> None:
    """Write known rows in original child-file order, atomically."""
    out_file.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=out_file.name + '.', suffix='.tmp', dir=out_file.parent
    )
    try:
        with os.fdopen(fd, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writeheader()
            for state in child_order:
                row = rows_by_state.get(state)
                if row is not None:
                    writer.writerow(row)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, out_file)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def parse_single_row(requested_state: str, stdout: str) -> tuple[list[str], dict[str, str]]:
    reader = csv.DictReader(io.StringIO(stdout))
    header = reader.fieldnames
    if not header or 'state' not in header:
        raise RuntimeError(f"Solver output for {requested_state} has no state column")
    rows = list(reader)
    if len(rows) != 1:
        raise RuntimeError(
            f"Solver output for {requested_state} has {len(rows)} data rows; expected exactly 1"
        )
    row = rows[0]
    returned_state = row.get('state', '').strip()
    if returned_state != requested_state:
        raise RuntimeError(
            f"Solver returned state {returned_state!r} for requested {requested_state!r}"
        )
    return header, row


def batch_indices(parent: str, spec: str) -> list[int]:
    if spec != 'all':
        return [int(spec)]
    safe = safe_parent(parent)
    pattern = re.compile(rf"^children_{re.escape(safe)}_batch(\d+)\.txt$")
    found = []
    for path in CHILDREN_DIR.glob(f"children_{safe}_batch*.txt"):
        match = pattern.match(path.name)
        if match:
            found.append(int(match.group(1)))
    if not found:
        raise RuntimeError(f"No batch files found for parent {parent}")
    return sorted(set(found))


def run_batch(parent: str, batch_index: int, max_workers: int) -> tuple[int, int]:
    safe = safe_parent(parent)
    batch_file = CHILDREN_DIR / f"children_{safe}_batch{batch_index}.txt"
    if not batch_file.exists():
        raise RuntimeError(f"Batch file missing: {batch_file}")

    out_file = CHILDREN_DIR / f"exact_{safe}_batch{batch_index}.csv"
    err_file = CHILDREN_DIR / f"exact_{safe}_batch{batch_index}.err"

    children = [line.strip() for line in batch_file.read_text().splitlines() if line.strip()]
    if len(children) != len(set(children)):
        raise RuntimeError(f"Duplicate child states in {batch_file}")

    header, rows_by_state = load_existing(out_file)
    unexpected = sorted(set(rows_by_state) - set(children))
    if unexpected:
        raise RuntimeError(
            f"Existing output contains states not present in {batch_file}: {unexpected[:5]}"
        )

    missing = [state for state in children if state not in rows_by_state]
    print(
        f"{parent} batch {batch_index}: total={len(children)} "
        f"already_done={len(rows_by_state)} remaining={len(missing)} max_workers={max_workers}"
    )

    if not missing:
        print(f"Already complete: {out_file}")
        return len(children), len(children)

    errors: list[str] = []
    completed_now = 0
    overall_start = time.time()

    with ProcessPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(run_child, state): state for state in missing}
        for fut in as_completed(futures):
            requested_state = futures[fut]
            try:
                state, stdout, stderr, rc, elapsed = fut.result()
            except Exception as exc:
                errors.append(f"{requested_state} worker_exception={exc!r}\n")
                print(f"  ERROR {requested_state}: worker exception {exc!r}")
                continue

            if state != requested_state:
                errors.append(
                    f"{requested_state} worker_state_mismatch returned={state!r}\n"
                )
                print(f"  ERROR {requested_state}: worker state mismatch")
                continue

            if rc != 0:
                errors.append(
                    f"{state} rc={rc} elapsed={elapsed:.1f}s\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}\n"
                )
                print(f"  ERROR {state}: rc={rc} elapsed={elapsed:.1f}s")
                continue

            try:
                child_header, row = parse_single_row(state, stdout)
                if header is None:
                    header = child_header
                elif child_header != header:
                    raise RuntimeError(
                        f"CSV header mismatch for {state}: {child_header!r} != {header!r}"
                    )
                rows_by_state[state] = row
                write_atomic(out_file, header, rows_by_state, children)
            except Exception as exc:
                errors.append(
                    f"{state} validation_error={exc!r}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}\n"
                )
                print(f"  ERROR {state}: validation failed: {exc}")
                continue

            completed_now += 1
            print(
                f"  [{len(rows_by_state)}/{len(children)}] {state} "
                f"rc=0 elapsed={elapsed:.1f}s checkpointed"
            )

    overall = time.time() - overall_start
    with err_file.open('w') as f:
        f.write(f"overall_elapsed={overall:.1f}s\n")
        f.write(f"completed_before={len(children) - len(missing)}\n")
        f.write(f"completed_now={completed_now}\n")
        f.write(f"completed_total={len(rows_by_state)}\n")
        f.write(f"expected_total={len(children)}\n")
        f.write(f"errors={len(errors)}\n")
        for error in errors:
            f.write(error)
            if not error.endswith('\n'):
                f.write('\n')

    print(
        f"Batch {batch_index} done in {overall:.1f}s: "
        f"{len(rows_by_state)}/{len(children)} complete, errors={len(errors)}"
    )
    return len(rows_by_state), len(children)


def main() -> None:
    if len(sys.argv) < 3:
        print(
            "Usage: run_blind_exact_children_parallel.py "
            "<parent> <batch_index|all> [max_workers]"
        )
        sys.exit(2)

    parent = sys.argv[1]
    batch_spec = sys.argv[2]
    max_workers = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    if max_workers < 1:
        raise ValueError("max_workers must be >= 1")

    indices = batch_indices(parent, batch_spec)
    grand_done = 0
    grand_total = 0
    incomplete = []

    for batch_index in indices:
        done, total = run_batch(parent, batch_index, max_workers)
        grand_done += done
        grand_total += total
        if done != total:
            incomplete.append(batch_index)

    print(
        f"Parent {parent}: {grand_done}/{grand_total} child solves present "
        f"across {len(indices)} batch(es)"
    )
    if incomplete:
        print(f"Incomplete batches: {','.join(map(str, incomplete))}")
        sys.exit(1)


if __name__ == '__main__':
    main()
