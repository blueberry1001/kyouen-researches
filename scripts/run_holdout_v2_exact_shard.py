#!/usr/bin/env python3
"""Solve one deterministic shard of the frozen V2 child task set exactly."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from holdout_v2_common import load_tasks, task_set_digest, verify_selection  # noqa: E402
from run_probe_holdout_independent import (  # noqa: E402
    SOLVER_BIN,
    build as build_solver,
    require_fresh_solver,
    sha256_file,
    solver_source_digest,
)

OUT_DIR = REPO_ROOT / "results" / "10x10" / "blind-probe-holdout-v2"
SHRINK = 0
LOAD = 90
FIELDS = [
    "parent", "global_index", "batch", "batch_position", "state", "outcome",
    "visited", "maxdepth", "memo", "seconds",
]


def shard_paths(shards: int, shard_index: int) -> tuple[Path, Path, Path]:
    suffix = f"w{shard_index:02d}-of-{shards:02d}"
    return (
        OUT_DIR / f"exact_outcomes_{suffix}.csv",
        OUT_DIR / f"exact_outcomes_{suffix}.protocol.json",
        OUT_DIR / f"exact_failures_{suffix}.csv",
    )


def protocol(tasks: list[tuple[str, int, int, str]], shards: int, shard_index: int) -> dict[str, object]:
    require_fresh_solver()
    return {
        "format": 1,
        "design": "clean-holdout-v2-exact",
        "solver_binary_sha256": sha256_file(SOLVER_BIN),
        "solver_sources_sha256": solver_source_digest(),
        "shrink": SHRINK,
        "load": LOAD,
        "budget": 0,
        "full_task_count": len(tasks),
        "full_tasks_sha256": task_set_digest(tasks),
        "shards": shards,
        "shard_index": shard_index,
        "shard_task_count": sum(i % shards == shard_index for i in range(len(tasks))),
    }


def require_manifest(tasks: list[tuple[str, int, int, str]], shards: int, shard_index: int) -> Path:
    out, manifest, _fail = shard_paths(shards, shard_index)
    current = protocol(tasks, shards, shard_index)
    if manifest.exists():
        if json.loads(manifest.read_text(encoding="utf-8")) != current:
            raise RuntimeError(f"exact protocol mismatch: {manifest}")
    else:
        if out.exists() and out.stat().st_size:
            raise RuntimeError(f"exact CSV exists without protocol sidecar: {out}")
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def load_done(path: Path) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    keys = {(r["parent"], r["state"].replace("-", ",")) for r in rows}
    if len(keys) != len(rows):
        raise RuntimeError(f"duplicate exact rows in {path}")
    return keys


def run_one(state: str, timeout: float) -> dict[str, str]:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     dir=SOLVER_BIN.parent, encoding="utf-8") as tmp:
        tmp.write(state + "\n")
        tmp_path = Path(tmp.name)
    try:
        proc = subprocess.run(
            [str(SOLVER_BIN), str(tmp_path), str(SHRINK), str(LOAD), "0", "0"],
            cwd=REPO_ROOT, text=True, capture_output=True, timeout=timeout,
        )
    finally:
        tmp_path.unlink(missing_ok=True)
    if proc.returncode != 0:
        raise RuntimeError(f"solver failed for {state}: rc={proc.returncode}\n{proc.stderr[-1000:]}")
    rows = list(csv.DictReader(proc.stdout.splitlines()))
    if len(rows) != 1:
        raise RuntimeError(f"expected one exact row for {state}, got {len(rows)}")
    row = rows[0]
    if row["outcome"] not in {"WIN", "LOSS"}:
        raise RuntimeError(f"non-exact outcome for {state}: {row['outcome']}")
    return row


def record_failure(path: Path, global_index: int, parent: str, state: str, kind: str, message: str) -> None:
    new = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["global_index", "parent", "state", "kind", "message"])
        w.writerow([global_index, parent, state, kind, message[-1000:]])


def run(shards: int, shard_index: int, timeout: float) -> None:
    if shards <= 0 or not 0 <= shard_index < shards:
        raise RuntimeError("invalid shard specification")
    tasks = load_tasks()
    out = require_manifest(tasks, shards, shard_index)
    _out, _manifest, fail = shard_paths(shards, shard_index)
    done = load_done(out)
    selected = [(i, t) for i, t in enumerate(tasks) if i % shards == shard_index]
    remaining = [(i, t) for i, t in selected if (t[0], t[3]) not in done]
    write_header = not out.exists() or out.stat().st_size == 0
    print(f"full_tasks={len(tasks)} shard={shard_index}/{shards} tasks={len(selected)} remaining={len(remaining)}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with out.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header:
            w.writeheader(); f.flush()
        for n, (global_index, (parent, batch, pos, state)) in enumerate(remaining, 1):
            try:
                row = run_one(state, timeout)
            except subprocess.TimeoutExpired as exc:
                record_failure(fail, global_index, parent, state, "TIMEOUT", str(exc))
                raise
            except Exception as exc:
                record_failure(fail, global_index, parent, state, "FAIL", repr(exc))
                raise
            actual = row["state"].replace("-", ",")
            if actual != state:
                raise RuntimeError(f"solver state mismatch: {state} != {actual}")
            w.writerow({
                "parent": parent, "global_index": global_index, "batch": batch,
                "batch_position": pos, "state": state, "outcome": row["outcome"],
                "visited": row["visited"], "maxdepth": row["maxdepth"],
                "memo": row["memo"], "seconds": row["seconds"],
            })
            f.flush()
            print(f"[{n}/{len(remaining)}] i={global_index} {parent} {state} {row['outcome']} visited={row['visited']}")


def main() -> None:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--check", action="store_true")
    ap.add_argument("--shards", type=int, default=20)
    ap.add_argument("--shard-index", type=int, default=0)
    ap.add_argument("--timeout", type=float, default=5400.0)
    args = ap.parse_args()
    if args.build:
        verify_selection(); build_solver()
        print(f"V2 exact build OK tasks={len(load_tasks())} sha256={task_set_digest()}")
    elif args.run:
        run(args.shards, args.shard_index, args.timeout)
    else:
        verify_selection(); print(f"V2 exact task set OK tasks={len(load_tasks())} sha256={task_set_digest()}")


if __name__ == "__main__":
    main()
