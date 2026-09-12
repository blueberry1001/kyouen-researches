#!/usr/bin/env python3
"""Generic fresh-process probe/exact runner for Staged Probe V3.

One solver process per child. No memo sharing across children.
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
V3_DIR = REPO_ROOT / "results" / "10x10" / "staged-v3-holdout"
TASK_CSV = V3_DIR / "exact_task_list.csv"

SOLVER_SRC = REPO_ROOT / "scripts" / "probe_cert_solver.cpp"
SOLVER_PARTS = REPO_ROOT / "scripts" / "probe_parts"
SOLVER_BIN = REPO_ROOT / "tmp-kb" / "probe_holdout_native"
SOLVER_STAMP = REPO_ROOT / "tmp-kb" / "probe_holdout_native.sources.sha256"

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


def task_set_digest(tasks: list[dict[str, str]]) -> str:
    h = hashlib.sha256()
    for t in tasks:
        data = json.dumps(
            [t["parent"], int(t["batch"]), int(t["batch_position"]), t["state"]],
            separators=(",", ":"),
        ).encode("utf-8")
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    return h.hexdigest()


def load_tasks() -> list[dict[str, str]]:
    with TASK_CSV.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def current_protocol(tasks: list[dict[str, str]], budget: int, shrink: int, load: int, tag: str) -> dict[str, object]:
    if not SOLVER_BIN.exists() or not SOLVER_STAMP.exists():
        raise RuntimeError(f"missing solver binary/stamp at {SOLVER_BIN}")
    recorded = SOLVER_STAMP.read_text(encoding="ascii").strip()
    current = solver_source_digest()
    if recorded != current:
        raise RuntimeError("solver sources changed since stamp; refusing to run")
    return {
        "format": 3,
        "tag": tag,
        "budget": budget,
        "shrink": shrink,
        "load": load,
        "solver_binary_sha256": sha256_file(SOLVER_BIN),
        "solver_sources_sha256": current,
        "holdout_task_count": len(tasks),
        "task_set_sha256": task_set_digest(tasks),
        "tie_break": "probe LOSS first; unresolved memo_used ascending; probe WIN last; 4th-move board index ascending",
        "fresh_process_per_child": True,
        "memo_sharing": "forbidden",
        "output_schema": FIELDS,
    }


def require_or_create_protocol(manifest_path: Path, out_csv: Path, protocol: dict[str, object]) -> None:
    if manifest_path.exists():
        recorded = json.loads(manifest_path.read_text(encoding="utf-8"))
        if recorded != protocol:
            raise RuntimeError(f"protocol differs from frozen manifest {manifest_path}")
        return
    if out_csv.exists() and out_csv.stat().st_size > 0:
        raise RuntimeError(f"{out_csv} exists without manifest; refusing to append")
    manifest_path.write_text(json.dumps(protocol, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_one(args_tuple: tuple[dict[str, str], int, int, int, str, Path]) -> dict[str, str]:
    task, shrink, load, budget, tmp_dir_s, _repo = args_tuple
    state = task["state"]
    tmp_dir = Path(tmp_dir_s)
    t_start = time.time()
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, dir=tmp_dir, encoding="utf-8") as tmp:
        tmp.write(state + "\n")
        tmp_path = Path(tmp.name)
    try:
        cmd = [str(SOLVER_BIN), str(tmp_path), str(shrink), str(load), str(budget), "0"]
        proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True, capture_output=True)
    finally:
        tmp_path.unlink(missing_ok=True)
    wall = time.time() - t_start
    if proc.returncode != 0:
        raise RuntimeError(f"solver failed for {state}: rc={proc.returncode}\n{(proc.stderr or '')[-500:]}")
    rows = list(csv.DictReader(proc.stdout.splitlines()))
    if len(rows) != 1:
        raise RuntimeError(f"expected 1 row for {state}, got {len(rows)}\n{(proc.stdout or '')[-500:]}")
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
        "_wall": f"{wall:.6f}",
    }


def filter_tasks(tasks: list[dict[str, str]], only_states_file: Path | None) -> list[dict[str, str]]:
    if only_states_file is None:
        return tasks
    keep = set()
    with only_states_file.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = r.get("state") or r.get("child") or r.get("canonical_state")
            if not key:
                raise RuntimeError(f"no state column in {only_states_file}")
            keep.add(key.strip())
            # also accept hyphen form
            keep.add("-".join(str(int(x)) for x in key.replace(",", "-").split("-") if x != ""))
    out = []
    for t in tasks:
        s = t["state"]
        s_hyphen = "-".join(str(int(x)) for x in s.split(","))
        if s in keep or s_hyphen in keep:
            out.append(t)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--budget", type=int, required=True)
    parser.add_argument("--shrink", type=int, default=3)
    parser.add_argument("--load", type=int, default=80)
    parser.add_argument("--tag", type=str, required=True, help="output basename tag, e.g. independent_probe_10000")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--only-states", type=Path, default=None, help="CSV with state column to restrict tasks")
    args = parser.parse_args()

    tasks = load_tasks()
    if args.only_states is not None:
        tasks = filter_tasks(tasks, args.only_states)
    if not tasks:
        raise RuntimeError("no tasks selected")

    out_csv = V3_DIR / f"{args.tag}.csv"
    manifest_path = V3_DIR / f"{args.tag}.protocol.json"
    protocol = current_protocol(tasks, args.budget, args.shrink, args.load, args.tag)
    require_or_create_protocol(manifest_path, out_csv, protocol)

    completed: set[tuple[str, str]] = set()
    if out_csv.exists():
        with out_csv.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                key = (r["parent"], r["state"])
                if key in completed:
                    raise RuntimeError(f"duplicate row: {key}")
                completed.add(key)
    pending = [t for t in tasks if (t["parent"], t["state"]) not in completed]
    print(f"tag={args.tag} budget={args.budget} total={len(tasks)} completed={len(completed)} pending={len(pending)}")
    if not pending:
        print("Already complete.")
        return

    tmp_dir = REPO_ROOT / "tmp-kb"
    t0 = time.time()
    out_file = out_csv.open("a" if completed else "w", newline="", encoding="utf-8")
    writer = csv.DictWriter(out_file, fieldnames=FIELDS)
    if not completed:
        writer.writeheader()
        out_file.flush()

    done = len(completed)
    base = done
    worker_args = [(t, args.shrink, args.load, args.budget, str(tmp_dir), str(REPO_ROOT)) for t in pending]
    with mp.Pool(processes=args.workers) as pool:
        for res in pool.imap_unordered(run_one, worker_args, chunksize=8):
            row = {k: res[k] for k in FIELDS}
            writer.writerow(row)
            out_file.flush()
            done += 1
            if done % 50 == 0 or done == len(tasks):
                elapsed = time.time() - t0
                speed = (done - base) / elapsed if elapsed > 0 else 0
                print(f"[{done}/{len(tasks)}] elapsed={elapsed:.1f}s ({speed:.2f} tasks/sec)", flush=True)
    out_file.close()
    print(f"Wrote {out_csv}")


if __name__ == "__main__":
    main()
