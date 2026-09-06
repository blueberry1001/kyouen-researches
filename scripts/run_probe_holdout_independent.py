#!/usr/bin/env python3
"""Run the preregistered 10x10 holdout probes with a fresh Solver per child.

This script deliberately does not read exact child outcomes and does not rank
children.  It only collects the preregistered 1M-probe statistics.  Keeping
collection separate from outcome analysis makes the order/memo audit simple:
every solver invocation receives exactly one state, so no transposition table
can leak from one candidate to another.

Parent membership comes only from the already-committed
results/10x10/holdout-parent-selection-preregistered.csv.  Existing child
batch files are used as immutable input; no child set is regenerated here.

Usage:
    python scripts/run_probe_holdout_independent.py --build
    python scripts/run_probe_holdout_independent.py --run
    python scripts/run_probe_holdout_independent.py --check

The run is resumable.  One CSV row is flushed after every completed child.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SELECTION = REPO_ROOT / "results" / "10x10" / "holdout-parent-selection-preregistered.csv"
CHILDREN_DIR = REPO_ROOT / "results" / "10x10" / "blind_probe_children"
OUT_DIR = REPO_ROOT / "results" / "10x10" / "blind-probe-holdout"
OUT_CSV = OUT_DIR / "independent_probe_1000000.csv"
SOLVER_SRC = REPO_ROOT / "scripts" / "probe_cert_solver.cpp"
SOLVER_BIN = REPO_ROOT / "tmp-kb" / "probe_holdout_native"

BUDGET = 1_000_000
SHRINK = 3
LOAD = 80

FIELDS = [
    "parent",
    "batch",
    "batch_position",
    "state",
    "probe_outcome",
    "visited",
    "maxdepth",
    "memo",
    "seconds",
]


def safe_parent(parent: str) -> str:
    return parent.replace(",", "_")


def load_parents() -> list[str]:
    if not SELECTION.exists():
        raise FileNotFoundError(SELECTION)
    with SELECTION.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    parents = [r["parent"].strip() for r in rows]
    if not parents or len(parents) != len(set(parents)):
        raise RuntimeError("holdout selection is empty or contains duplicate parents")
    return parents


def batch_index(path: Path) -> int:
    return int(path.stem.rsplit("batch", 1)[1])


def load_tasks() -> list[tuple[str, int, int, str]]:
    tasks: list[tuple[str, int, int, str]] = []
    seen_states: set[tuple[str, str]] = set()
    for parent in load_parents():
        files = sorted(
            CHILDREN_DIR.glob(f"children_{safe_parent(parent)}_batch*.txt"),
            key=batch_index,
        )
        if not files:
            raise RuntimeError(f"no child batch files for preregistered parent {parent}")
        for path in files:
            b = batch_index(path)
            states = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if not states:
                raise RuntimeError(f"empty child batch: {path}")
            for pos, state in enumerate(states):
                key = (parent, state.replace(",", "-"))
                if key in seen_states:
                    raise RuntimeError(f"duplicate child for {parent}: {state}")
                seen_states.add(key)
                tasks.append((parent, b, pos, state))
    return tasks


def build() -> None:
    SOLVER_BIN.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["g++", "-O2", "-std=c++20", "-o", str(SOLVER_BIN), str(SOLVER_SRC)]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True, capture_output=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        raise SystemExit(proc.returncode)
    print(f"built {SOLVER_BIN.relative_to(REPO_ROOT)}")


def completed_keys() -> set[tuple[str, str]]:
    if not OUT_CSV.exists():
        return set()
    with OUT_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if rows and set(rows[0]) != set(FIELDS):
        raise RuntimeError(f"unexpected columns in {OUT_CSV}")
    keys = {(r["parent"], r["state"].replace(",", "-")) for r in rows}
    if len(keys) != len(rows):
        raise RuntimeError("output contains duplicate parent/state rows")
    return keys


def run_one(state: str) -> dict[str, str]:
    # A distinct process is the isolation boundary.  A one-line temporary input
    # additionally makes accidental in-process candidate reuse impossible.
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, dir=SOLVER_BIN.parent, encoding="utf-8") as tmp:
        tmp.write(state + "\n")
        tmp_path = Path(tmp.name)
    try:
        cmd = [str(SOLVER_BIN), str(tmp_path), str(SHRINK), str(LOAD), str(BUDGET), "0"]
        proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True, capture_output=True)
    finally:
        tmp_path.unlink(missing_ok=True)
    if proc.returncode != 0:
        raise RuntimeError(f"solver failed for {state}: rc={proc.returncode}\n{proc.stderr[-1000:]}")
    rows = list(csv.DictReader(proc.stdout.splitlines()))
    if len(rows) != 1:
        raise RuntimeError(f"expected exactly one solver row for {state}, got {len(rows)}")
    row = rows[0]
    required = {"state", "outcome", "visited", "maxdepth", "memo", "seconds"}
    missing = required - set(row)
    if missing:
        raise RuntimeError(f"solver row missing fields {sorted(missing)}")
    return row


def run() -> None:
    if not SOLVER_BIN.exists():
        raise RuntimeError(f"missing {SOLVER_BIN}; run --build first")
    tasks = load_tasks()
    done = completed_keys()
    remaining = [t for t in tasks if (t[0], t[3].replace(",", "-")) not in done]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_header = not OUT_CSV.exists() or OUT_CSV.stat().st_size == 0
    print(f"tasks={len(tasks)} done={len(done)} remaining={len(remaining)} budget={BUDGET}")
    with OUT_CSV.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header:
            writer.writeheader()
            f.flush()
        for n, (parent, batch, pos, state) in enumerate(remaining, 1):
            row = run_one(state)
            expected = state.replace(",", "-")
            actual = row["state"].replace(",", "-")
            if actual != expected:
                raise RuntimeError(f"solver state mismatch: expected {expected}, got {actual}")
            writer.writerow({
                "parent": parent,
                "batch": batch,
                "batch_position": pos,
                "state": row["state"],
                "probe_outcome": row["outcome"],
                "visited": row["visited"],
                "maxdepth": row["maxdepth"],
                "memo": row["memo"],
                "seconds": row["seconds"],
            })
            f.flush()
            print(f"[{n}/{len(remaining)}] {parent} {row['state']} outcome={row['outcome']} visited={row['visited']} memo={row['memo']}")


def check() -> None:
    tasks = load_tasks()
    done = completed_keys()
    task_keys = {(p, s.replace(",", "-")) for p, _b, _pos, s in tasks}
    extra = done - task_keys
    missing = task_keys - done
    if extra:
        raise RuntimeError(f"output has {len(extra)} rows outside the frozen holdout child set")
    print(f"parents={len(load_parents())} tasks={len(tasks)} completed={len(done)} missing={len(missing)}")
    if missing:
        raise SystemExit(1)


def main() -> None:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.build:
        build()
    elif args.run:
        run()
    else:
        check()


if __name__ == "__main__":
    main()
