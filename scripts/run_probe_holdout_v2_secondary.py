#!/usr/bin/env python3
"""Post-primary 10k/100k fresh-solver probes for V2 rank stability."""

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
from holdout_v2_common import load_tasks, task_set_digest  # noqa: E402
from run_probe_holdout_independent import SOLVER_BIN, require_fresh_solver, sha256_file, solver_source_digest  # noqa: E402

PRIMARY_SUMMARY = REPO_ROOT / "results" / "10x10" / "blind-probe-holdout-v2" / "preregistered_v2_summary.json"
OUT_DIR = REPO_ROOT / "results" / "10x10" / "blind-probe-holdout-v2" / "secondary"
SHRINK = 3
LOAD = 80
FIELDS = ["parent", "global_index", "state", "probe_outcome", "visited", "maxdepth", "memo", "seconds"]


def paths(budget: int, shards: int, shard: int) -> tuple[Path, Path]:
    stem = f"independent_probe_{budget}_w{shard:02d}-of-{shards:02d}"
    return OUT_DIR / f"{stem}.csv", OUT_DIR / f"{stem}.protocol.json"


def run_one(state: str, budget: int) -> dict[str, str]:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     dir=SOLVER_BIN.parent, encoding="utf-8") as tmp:
        tmp.write(state + "\n"); tmp_path = Path(tmp.name)
    try:
        proc = subprocess.run([str(SOLVER_BIN), str(tmp_path), str(SHRINK), str(LOAD), str(budget), "0"],
                              cwd=REPO_ROOT, text=True, capture_output=True)
    finally:
        tmp_path.unlink(missing_ok=True)
    if proc.returncode != 0:
        raise RuntimeError(f"solver failed for {state}: {proc.stderr[-1000:]}")
    rows = list(csv.DictReader(proc.stdout.splitlines()))
    if len(rows) != 1 or rows[0]["outcome"] not in {"LOSS", "PROBE", "WIN"}:
        raise RuntimeError(f"bad solver output for {state}")
    return rows[0]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, required=True, choices=[10_000, 100_000])
    ap.add_argument("--shards", type=int, default=4)
    ap.add_argument("--shard-index", type=int, default=0)
    args = ap.parse_args()
    if not PRIMARY_SUMMARY.exists():
        raise SystemExit("secondary budgets are locked until preregistered_v2_summary.json exists")
    require_fresh_solver()
    tasks = load_tasks()
    if not 0 <= args.shard_index < args.shards:
        raise SystemExit("invalid shard")
    out, manifest = paths(args.budget, args.shards, args.shard_index)
    current = {
        "format": 1, "design": "V2 post-primary budget stability",
        "budget": args.budget, "shrink": SHRINK, "load": LOAD,
        "solver_binary_sha256": sha256_file(SOLVER_BIN),
        "solver_sources_sha256": solver_source_digest(),
        "full_task_count": len(tasks), "full_tasks_sha256": task_set_digest(tasks),
        "shards": args.shards, "shard_index": args.shard_index,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if manifest.exists():
        if json.loads(manifest.read_text(encoding="utf-8")) != current:
            raise SystemExit("secondary protocol mismatch")
    else:
        if out.exists() and out.stat().st_size:
            raise SystemExit("secondary CSV exists without manifest")
        manifest.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    done: set[tuple[str, str]] = set()
    if out.exists():
        with out.open(newline="", encoding="utf-8") as f:
            done = {(r["parent"], r["state"].replace("-", ",")) for r in csv.DictReader(f)}
    selected = [(i, t) for i, t in enumerate(tasks) if i % args.shards == args.shard_index]
    write_header = not out.exists() or out.stat().st_size == 0
    with out.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header: w.writeheader(); f.flush()
        for i, (parent, _batch, _pos, state) in selected:
            if (parent, state) in done: continue
            row = run_one(state, args.budget)
            w.writerow({"parent": parent, "global_index": i, "state": state,
                        "probe_outcome": row["outcome"], "visited": row["visited"],
                        "maxdepth": row["maxdepth"], "memo": row["memo"], "seconds": row["seconds"]})
            f.flush(); print(i, parent, state, row["outcome"], row["memo"])


if __name__ == "__main__":
    main()
