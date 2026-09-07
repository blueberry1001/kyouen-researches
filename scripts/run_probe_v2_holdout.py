#!/usr/bin/env python3
"""Run 10x10 Clean Holdout V2 probes with one fresh Solver process per child.

Supports multiprocessing parallel workers for fast execution.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import multiprocessing as mp
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
V2_DIR = REPO_ROOT / "results" / "10x10" / "clean-holdout-v2"
TASK_CSV = V2_DIR / "exact_task_list.csv"
OUT_CSV = V2_DIR / "independent_probe_1000000.csv"
RUN_MANIFEST = V2_DIR / "independent_probe_1000000.protocol.json"

SOLVER_SRC = REPO_ROOT / "scripts" / "probe_cert_solver.cpp"
SOLVER_PARTS = REPO_ROOT / "scripts" / "probe_parts"
SOLVER_BIN = REPO_ROOT / "tmp-kb" / "probe_holdout_native"
SOLVER_STAMP = REPO_ROOT / "tmp-kb" / "probe_holdout_native.sources.sha256"

BUDGET = 1_000_000
SHRINK = 3
LOAD = 80

FIELDS = [
    "parent", "batch", "batch_position", "state", "probe_outcome",
    "visited", "maxdepth", "memo", "seconds",
]


def solver_source_digest() -> str:
    files = [SOLVER_SRC] + sorted(SOLVER_PARTS.glob("*.inc"))
    h = hashlib.sha256()
    for path in files:
        rel = path.relative_to(REPO_ROOT).as_posix().encode()
        data = path.read_bytes()
        h.update(len(rel).to_bytes(4, "big"))
        h.update(rel)
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    return h.hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def build_solver() -> None:
    SOLVER_BIN.parent.mkdir(parents=True, exist_ok=True)
    digest_before = solver_source_digest()
    cmd = ["g++", "-O2", "-std=c++20", "-o", str(SOLVER_BIN), str(SOLVER_SRC)]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True, capture_output=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        raise SystemExit(proc.returncode)
    digest_after = solver_source_digest()
    if digest_after != digest_before:
        SOLVER_BIN.unlink(missing_ok=True)
        raise RuntimeError("solver sources changed during compilation")
    SOLVER_STAMP.write_text(digest_after + "\n", encoding="ascii")
    print(f"Built {SOLVER_BIN.relative_to(REPO_ROOT)} sources_sha256={digest_after}")


def require_fresh_solver() -> None:
    if not SOLVER_BIN.exists() or not SOLVER_STAMP.exists():
        build_solver()
    recorded = SOLVER_STAMP.read_text(encoding="ascii").strip()
    current = solver_source_digest()
    if recorded != current:
        build_solver()


def run_single_probe(task: dict[str, str]) -> dict[str, str]:
    state = task["state"]
    with tempfile.NamedTemporaryFile(
        "w", suffix=".txt", delete=False, dir=SOLVER_BIN.parent, encoding="utf-8"
    ) as tmp:
        tmp.write(state + "\n")
        tmp_path = Path(tmp.name)
    try:
        cmd = [str(SOLVER_BIN), str(tmp_path), str(SHRINK), str(LOAD), str(BUDGET), "0"]
        proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True, capture_output=True)
    finally:
        tmp_path.unlink(missing_ok=True)

    if proc.returncode != 0:
        raise RuntimeError(f"probe failed for {state}: rc={proc.returncode}\n{proc.stderr[-500:]}")

    rows = list(csv.DictReader(proc.stdout.splitlines()))
    if len(rows) != 1:
        raise RuntimeError(f"expected 1 row for {state}, got {len(rows)}")
    row = rows[0]
    return {
        "parent": task["parent"],
        "batch": task["batch"],
        "batch_position": task["batch_position"],
        "state": state,
        "probe_outcome": row["outcome"],
        "visited": row["visited"],
        "maxdepth": row["maxdepth"],
        "memo": row["memo"],
        "seconds": row["seconds"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--build", action="store_true")
    args = parser.parse_args()

    if args.build:
        build_solver()
        return

    require_fresh_solver()

    with TASK_CSV.open(newline="", encoding="utf-8") as f:
        tasks = list(csv.DictReader(f))

    # Protocol manifest
    manifest = {
        "format": 2,
        "solver_binary_sha256": sha256_file(SOLVER_BIN),
        "solver_sources_sha256": solver_source_digest(),
        "budget": BUDGET,
        "shrink": SHRINK,
        "load": LOAD,
        "holdout_task_count": len(tasks),
        "holdout_tasks_sha256": hashlib.sha256(TASK_CSV.read_bytes()).hexdigest(),
    }
    RUN_MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Load already completed
    completed = set()
    existing_rows = []
    if OUT_CSV.exists():
        with OUT_CSV.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                completed.add((r["parent"], r["state"]))
                existing_rows.append(r)

    pending = [t for t in tasks if (t["parent"], t["state"]) not in completed]
    print(f"Total tasks: {len(tasks)}, Completed: {len(completed)}, Pending: {len(pending)}")

    if not pending:
        print("All probes already complete!")
        return

    t0 = time.time()
    out_file = OUT_CSV.open("a" if completed else "w", newline="", encoding="utf-8")
    writer = csv.DictWriter(out_file, fieldnames=FIELDS)
    if not completed:
        writer.writeheader()

    done_count = len(completed)
    with mp.Pool(processes=args.workers) as pool:
        for res in pool.imap_unordered(run_single_probe, pending, chunksize=4):
            writer.writerow(res)
            out_file.flush()
            done_count += 1
            if done_count % 50 == 0 or done_count == len(tasks):
                elapsed = time.time() - t0
                speed = (done_count - len(completed)) / elapsed if elapsed > 0 else 0
                print(f"[{done_count}/{len(tasks)}] elapsed={elapsed:.1f}s ({speed:.2f} tasks/sec)")

    out_file.close()
    print("Probe run finished successfully.")


if __name__ == "__main__":
    main()
