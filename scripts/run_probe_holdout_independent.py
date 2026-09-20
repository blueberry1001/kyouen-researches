#!/usr/bin/env python3
"""Run preregistered 10x10 holdout probes with one fresh Solver process per child.

The collector never reads exact outcomes. It also refuses to run a stale
solver binary: --build records a digest of probe_cert_solver.cpp plus all
probe_parts/*.inc dependencies, and --run requires that digest to still match.

For resumability without train/evaluation-condition drift, the first --run
also freezes a protocol manifest beside the output CSV. The manifest binds the
exact solver binary bytes, solver-source digest, budget, shrink, load, and the
complete ordered holdout task set. Any later --run must match it exactly before
rows can be appended.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SELECTION = REPO_ROOT / "results" / "10x10" / "holdout-parent-selection-preregistered.csv"
CHILDREN_DIR = REPO_ROOT / "results" / "10x10" / "blind_probe_children"
OUT_DIR = REPO_ROOT / "results" / "10x10" / "blind-probe-holdout"
OUT_CSV = OUT_DIR / "independent_probe_1000000.csv"
RUN_MANIFEST = OUT_DIR / "independent_probe_1000000.protocol.json"
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
            states = [x.strip() for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
            if not states:
                raise RuntimeError(f"empty child batch: {path}")
            for pos, state in enumerate(states):
                key = (parent, state.replace(",", "-"))
                if key in seen_states:
                    raise RuntimeError(f"duplicate child for {parent}: {state}")
                seen_states.add(key)
                tasks.append((parent, b, pos, state))
    return tasks


def task_set_digest(tasks: list[tuple[str, int, int, str]]) -> str:
    """Digest the complete ordered task sequence without ambiguous separators."""
    h = hashlib.sha256()
    for task in tasks:
        data = json.dumps(task, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    return h.hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def solver_source_digest() -> str:
    """Digest every source file that can affect the compiled probe solver."""
    files = [SOLVER_SRC] + sorted(SOLVER_PARTS.glob("*.inc"))
    if len(files) == 1:
        raise RuntimeError(f"no solver include parts found under {SOLVER_PARTS}")
    h = hashlib.sha256()
    for path in files:
        if not path.is_file():
            raise FileNotFoundError(path)
        rel = path.relative_to(REPO_ROOT).as_posix().encode()
        data = path.read_bytes()
        h.update(len(rel).to_bytes(4, "big"))
        h.update(rel)
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    return h.hexdigest()


def require_fresh_solver() -> None:
    if not SOLVER_BIN.exists():
        raise RuntimeError(f"missing {SOLVER_BIN}; run --build first")
    if not SOLVER_STAMP.exists():
        raise RuntimeError(
            f"missing solver source stamp {SOLVER_STAMP}; run --build first "
            "(an untracked/stale binary is not accepted for the holdout)"
        )
    recorded = SOLVER_STAMP.read_text(encoding="ascii").strip()
    current = solver_source_digest()
    if recorded != current:
        raise RuntimeError(
            "probe solver sources changed since the binary was built; "
            "run --build again before collecting holdout rows"
        )


def current_protocol_manifest(tasks: list[tuple[str, int, int, str]]) -> dict[str, object]:
    require_fresh_solver()
    return {
        "format": 2,
        "solver_binary_sha256": sha256_file(SOLVER_BIN),
        "solver_sources_sha256": solver_source_digest(),
        "budget": BUDGET,
        "shrink": SHRINK,
        "load": LOAD,
        "holdout_task_count": len(tasks),
        "holdout_tasks_sha256": task_set_digest(tasks),
    }


def require_or_create_protocol_manifest(tasks: list[tuple[str, int, int, str]]) -> None:
    """Freeze exact run conditions and task sequence before appending any row."""
    current = current_protocol_manifest(tasks)
    if RUN_MANIFEST.exists():
        recorded = json.loads(RUN_MANIFEST.read_text(encoding="utf-8"))
        if recorded != current:
            raise RuntimeError(
                "holdout protocol or task set differs from the run already recorded in "
                f"{RUN_MANIFEST}; refusing to mix rows from different conditions/task sets"
            )
        return

    # A CSV without its provenance sidecar is ambiguous and must never be
    # silently adopted as part of this preregistered run.
    if OUT_CSV.exists() and OUT_CSV.stat().st_size > 0:
        raise RuntimeError(
            f"{OUT_CSV} exists but {RUN_MANIFEST} does not; refusing to append "
            "because existing row provenance cannot be established"
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RUN_MANIFEST.write_text(
        json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def build() -> None:
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
        raise RuntimeError("solver sources changed during compilation; build discarded")
    SOLVER_STAMP.write_text(digest_after + "\n", encoding="ascii")
    print(f"built {SOLVER_BIN.relative_to(REPO_ROOT)} sources_sha256={digest_after}")


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
    # Read the complete task sequence once, then bind that exact in-memory
    # sequence into the manifest before any result row can be appended.
    tasks = load_tasks()
    require_or_create_protocol_manifest(tasks)
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
            print(
                f"[{n}/{len(remaining)}] {parent} {row['state']} "
                f"outcome={row['outcome']} visited={row['visited']} memo={row['memo']}"
            )


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
