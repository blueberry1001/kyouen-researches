#!/usr/bin/env python3
"""Run the frozen 10x10 holdout-v2 1M probes without reading outcomes.

The parent sample and child-enumeration rule were frozen before this runner.
This script regenerates tasks.csv with the pinned freezer, verifies its exact
SHA-256, binds solver bytes/sources + task bytes + probe parameters in a
protocol manifest, and then runs every child in a fresh solver process.

Exact child outcomes are never read.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "results" / "10x10" / "fresh-parent-holdout-v2"
TASKS = V2 / "tasks.csv"
TASK_MANIFEST = V2 / "tasks.manifest.json"
OUT = V2 / "probe_1000000.csv"
PROTOCOL = V2 / "probe_1000000.protocol.json"
FREEZER = ROOT / "scripts" / "freeze_10x10_holdout_v2_tasks.py"
SOLVER_SRC = ROOT / "scripts" / "probe_cert_solver.cpp"
SOLVER_PARTS = ROOT / "scripts" / "probe_parts"
SOLVER_BIN = ROOT / "tmp-kb" / "probe_holdout_native"
SOLVER_STAMP = ROOT / "tmp-kb" / "probe_holdout_native.sources.sha256"

EXPECTED_TASKS = 2292
EXPECTED_TASKS_SHA256 = "907dc011eb64640ca3722039b0ebcfc0b604e7ad37bb3e7576c9253c607233e1"
BUDGET = 1_000_000
SHRINK = 3
LOAD = 80
FIELDS = ["selection_index", "parent", "move", "state", "probe_outcome", "visited", "maxdepth", "memo", "seconds"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def solver_source_digest() -> str:
    files = [SOLVER_SRC] + sorted(SOLVER_PARTS.glob("*.inc"))
    if len(files) == 1:
        raise RuntimeError(f"no solver include parts under {SOLVER_PARTS}")
    h = hashlib.sha256()
    for path in files:
        rel = path.relative_to(ROOT).as_posix().encode()
        data = path.read_bytes()
        h.update(len(rel).to_bytes(4, "big")); h.update(rel)
        h.update(len(data).to_bytes(8, "big")); h.update(data)
    return h.hexdigest()


def require_fresh_solver() -> None:
    if not SOLVER_BIN.exists() or not SOLVER_STAMP.exists():
        raise RuntimeError("missing stamped probe solver; build scripts/run_probe_holdout_independent.py --build first")
    if SOLVER_STAMP.read_text(encoding="ascii").strip() != solver_source_digest():
        raise RuntimeError("probe solver sources changed since build; rebuild before collecting V2 probes")


def freeze_and_verify_tasks() -> list[dict[str, str]]:
    proc = subprocess.run([sys.executable, str(FREEZER)], cwd=ROOT, text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"task freezer failed:\n{proc.stdout}\n{proc.stderr}")
    if not TASKS.exists() or not TASK_MANIFEST.exists():
        raise RuntimeError("task freezer did not create both tasks.csv and tasks.manifest.json")
    if sha256_file(TASKS) != EXPECTED_TASKS_SHA256:
        raise RuntimeError("V2 task bytes differ from preregistered digest")
    with TASKS.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != EXPECTED_TASKS:
        raise RuntimeError(f"expected {EXPECTED_TASKS} tasks, got {len(rows)}")
    keys = {(r["parent"], r["state"]) for r in rows}
    if len(keys) != len(rows):
        raise RuntimeError("duplicate parent/state in frozen V2 task set")
    return rows


def current_protocol() -> dict[str, object]:
    require_fresh_solver()
    return {
        "format": 1,
        "budget": BUDGET,
        "shrink": SHRINK,
        "load": LOAD,
        "task_count": EXPECTED_TASKS,
        "tasks_sha256": sha256_file(TASKS),
        "task_manifest_sha256": sha256_file(TASK_MANIFEST),
        "solver_binary_sha256": sha256_file(SOLVER_BIN),
        "solver_sources_sha256": solver_source_digest(),
        "fresh_solver_process_per_child": True,
        "exact_outcome_data_read": False,
    }


def require_or_create_protocol() -> None:
    cur = current_protocol()
    if PROTOCOL.exists():
        old = json.loads(PROTOCOL.read_text(encoding="utf-8"))
        if old != cur:
            raise RuntimeError("V2 probe protocol drift; refusing to mix runs")
    else:
        if OUT.exists() and OUT.stat().st_size:
            raise RuntimeError("probe CSV exists without protocol manifest")
        PROTOCOL.write_text(json.dumps(cur, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_one(task: dict[str, str]) -> dict[str, str]:
    state = task["state"]
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, dir=SOLVER_BIN.parent, encoding="utf-8") as tf:
        tf.write(state + "\n")
        temp = Path(tf.name)
    try:
        cmd = [str(SOLVER_BIN), str(temp), str(SHRINK), str(LOAD), str(BUDGET), "0"]
        p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    finally:
        temp.unlink(missing_ok=True)
    if p.returncode != 0:
        raise RuntimeError(f"solver failed for {state}: rc={p.returncode} {p.stderr[-500:]}")
    rows = list(csv.DictReader(p.stdout.splitlines()))
    if len(rows) != 1:
        raise RuntimeError(f"expected one solver row for {state}, got {len(rows)}")
    r = rows[0]
    if r["state"].replace("-", ",") != state:
        raise RuntimeError(f"state mismatch for {state}: {r['state']}")
    return {
        "selection_index": task["selection_index"], "parent": task["parent"], "move": task["move"], "state": state,
        "probe_outcome": r["outcome"], "visited": r["visited"], "maxdepth": r["maxdepth"], "memo": r["memo"], "seconds": r["seconds"],
    }


def completed() -> dict[tuple[str, str], dict[str, str]]:
    if not OUT.exists():
        return {}
    with OUT.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    ans = {(r["parent"], r["state"]): r for r in rows}
    if len(ans) != len(rows):
        raise RuntimeError("duplicate rows in V2 probe output")
    return ans


def run(workers: int) -> None:
    tasks = freeze_and_verify_tasks()
    require_or_create_protocol()
    done = completed()
    todo = [t for t in tasks if (t["parent"], t["state"]) not in done]
    print(f"tasks={len(tasks)} done={len(done)} remaining={len(todo)} workers={workers}")
    if not todo:
        return
    write_header = not OUT.exists() or OUT.stat().st_size == 0
    with OUT.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header:
            w.writeheader(); f.flush()
        with ProcessPoolExecutor(max_workers=workers) as ex:
            for i, row in enumerate(ex.map(run_one, todo), 1):
                w.writerow(row); f.flush()
                print(f"[{i}/{len(todo)}] {row['parent']} {row['state']} {row['probe_outcome']} memo={row['memo']}")


def check() -> None:
    tasks = freeze_and_verify_tasks()
    done = completed()
    expected = {(r["parent"], r["state"]) for r in tasks}
    actual = set(done)
    if actual - expected:
        raise RuntimeError(f"{len(actual - expected)} output rows are outside frozen V2 tasks")
    print(f"tasks={len(expected)} completed={len(actual)} missing={len(expected-actual)}")
    if expected != actual:
        raise SystemExit(1)


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--run", action="store_true")
    g.add_argument("--check", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    if a.workers < 1:
        raise SystemExit("--workers must be >=1")
    if a.run:
        run(a.workers)
    else:
        check()


if __name__ == "__main__":
    main()
