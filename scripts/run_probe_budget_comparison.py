#!/usr/bin/env python3
"""Run 10k and 100k probes on the original 11 holdout parents for budget stability analysis.

Uses the frozen task list from results/10x10/blind-probe-holdout/exact_task_list.csv.
"""

from __future__ import annotations

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
HOLDOUT_DIR = REPO_ROOT / "results" / "10x10" / "blind-probe-holdout"
TASK_CSV = HOLDOUT_DIR / "exact_task_list.csv"

SOLVER_SRC = REPO_ROOT / "scripts" / "probe_cert_solver.cpp"
SOLVER_PARTS = REPO_ROOT / "scripts" / "probe_parts"
SOLVER_BIN = REPO_ROOT / "tmp-kb" / "probe_holdout_native"
SOLVER_STAMP = REPO_ROOT / "tmp-kb" / "probe_holdout_native.sources.sha256"

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


def require_fresh_solver() -> None:
    if not SOLVER_BIN.exists() or not SOLVER_STAMP.exists():
        raise RuntimeError("solver not built; run run_probe_v2_holdout.py --build")
    recorded = SOLVER_STAMP.read_text(encoding="ascii").strip()
    current = solver_source_digest()
    if recorded != current:
        raise RuntimeError("solver sources changed")


def run_single_probe(args: tuple[dict[str, str], int]) -> dict[str, str]:
    task, budget = args
    state = task["state"]
    with tempfile.NamedTemporaryFile(
        "w", suffix=".txt", delete=False, dir=SOLVER_BIN.parent, encoding="utf-8"
    ) as tmp:
        tmp.write(state + "\n")
        tmp_path = Path(tmp.name)
    try:
        cmd = [str(SOLVER_BIN), str(tmp_path), str(SHRINK), str(LOAD), str(budget), "0"]
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
        "batch_position": task["pos"],
        "state": state,
        "probe_outcome": row["outcome"],
        "visited": row["visited"],
        "maxdepth": row["maxdepth"],
        "memo": row["memo"],
        "seconds": row["seconds"],
    }


def run_budget(budget: int, workers: int) -> None:
    require_fresh_solver()
    out_csv = HOLDOUT_DIR / f"independent_probe_{budget}.csv"
    manifest_path = HOLDOUT_DIR / f"independent_probe_{budget}.protocol.json"

    with TASK_CSV.open(newline="", encoding="utf-8") as f:
        tasks = list(csv.DictReader(f))

    manifest = {
        "format": 2,
        "solver_binary_sha256": sha256_file(SOLVER_BIN),
        "solver_sources_sha256": solver_source_digest(),
        "budget": budget,
        "shrink": SHRINK,
        "load": LOAD,
        "holdout_task_count": len(tasks),
        "holdout_tasks_sha256": hashlib.sha256(TASK_CSV.read_bytes()).hexdigest(),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    completed = set()
    if out_csv.exists():
        with out_csv.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                completed.add((r["parent"], r["state"]))

    pending = [t for t in tasks if (t["parent"], t["state"]) not in completed]
    print(f"Budget {budget}: total={len(tasks)}, completed={len(completed)}, pending={len(pending)}")
    if not pending:
        return

    t0 = time.time()
    out_file = out_csv.open("a" if completed else "w", newline="", encoding="utf-8")
    writer = csv.DictWriter(out_file, fieldnames=FIELDS)
    if not completed:
        writer.writeheader()

    done_count = len(completed)
    args_list = [(t, budget) for t in pending]
    with mp.Pool(processes=workers) as pool:
        for res in pool.imap_unordered(run_single_probe, args_list, chunksize=4):
            writer.writerow(res)
            out_file.flush()
            done_count += 1
            if done_count % 50 == 0 or done_count == len(tasks):
                elapsed = time.time() - t0
                speed = (done_count - len(completed)) / elapsed if elapsed > 0 else 0
                print(f"  [{done_count}/{len(tasks)}] elapsed={elapsed:.1f}s ({speed:.2f} tasks/sec)")

    out_file.close()
    print(f"Budget {budget} finished.")


def main():
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    for budget in [10_000, 100_000]:
        run_budget(budget, workers)


if __name__ == "__main__":
    main()
