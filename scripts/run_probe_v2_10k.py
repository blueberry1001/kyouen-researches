#!/usr/bin/env python3
"""Run 10x10 Clean Holdout V2 fresh 10k probes (frozen protocol).

One fresh Solver process per child; no memo sharing across children.
See docs/10X10_V2_10K_PROBE_PREREG.md (frozen before first row).

Usage:
  python scripts/run_probe_v2_10k.py --build
  python scripts/run_probe_v2_10k.py --workers 12
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
OUT_CSV = V2_DIR / "independent_probe_10000.csv"
RUN_MANIFEST = V2_DIR / "independent_probe_10000.protocol.json"
RUNLOG = V2_DIR / "independent_probe_10000.runlog.jsonl"

SOLVER_SRC = REPO_ROOT / "scripts" / "probe_cert_solver.cpp"
SOLVER_PARTS = REPO_ROOT / "scripts" / "probe_parts"
SOLVER_BIN = REPO_ROOT / "tmp-kb" / "probe_holdout_native"
SOLVER_STAMP = REPO_ROOT / "tmp-kb" / "probe_holdout_native.sources.sha256"

BUDGET = 10_000
SHRINK = 3
LOAD = 80
BUILD_CMD = ["g++", "-O2", "-std=c++20"]

# Frozen expectations (see prereg doc). Canonical tuple digest is authoritative;
# raw file-bytes SHA is recorded for transparency (CRLF/LF checkout variance).
FROZEN_TASK_SET_SHA256 = "aeccb6662a37ef25faf3fe6d0ab6707a9677718889139123060fff4a48566bc7"
FROZEN_TASK_COUNT = 1136
FROZEN_SOLVER_BINARY_SHA256 = "15d805ea9b354cc11c5c5ee5329512b723241897e32d135bf5a82094cdccd585"
FROZEN_SOLVER_SOURCES_SHA256 = "9b6f227ffb9fd802851ae69bad3a5621ce78857af1c65084ae92d09aa67e47b3"

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


def build_solver() -> None:
    SOLVER_BIN.parent.mkdir(parents=True, exist_ok=True)
    digest_before = solver_source_digest()
    cmd = BUILD_CMD + ["-o", str(SOLVER_BIN), str(SOLVER_SRC)]
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
        raise RuntimeError(f"missing {SOLVER_BIN} or stamp; run --build first")
    recorded = SOLVER_STAMP.read_text(encoding="ascii").strip()
    current = solver_source_digest()
    if recorded != current:
        raise RuntimeError(
            "probe solver sources changed since the binary was built; "
            "refusing to run (rebuild would change the frozen digest)"
        )
    binary_sha = sha256_file(SOLVER_BIN)
    if binary_sha != FROZEN_SOLVER_BINARY_SHA256:
        raise RuntimeError(f"solver binary digest mismatch: {binary_sha}")
    if current != FROZEN_SOLVER_SOURCES_SHA256:
        raise RuntimeError(f"solver sources digest mismatch: {current}")


def current_protocol_manifest(tasks: list[dict[str, str]]) -> dict[str, object]:
    require_fresh_solver()
    return {
        "format": 2,
        "budget": BUDGET,
        "shrink": SHRINK,
        "load": LOAD,
        "build_cmd": BUILD_CMD + ["-o", "<bin>", "<src>"],
        "solver_binary_sha256": sha256_file(SOLVER_BIN),
        "solver_sources_sha256": solver_source_digest(),
        "holdout_task_count": len(tasks),
        "task_set_sha256": task_set_digest(tasks),
        "holdout_tasks_file_sha256": hashlib.sha256(TASK_CSV.read_bytes()).hexdigest(),
        "tie_break": "probe LOSS first; unresolved memo_used ascending; probe WIN last; 4th-move board index ascending",
        "ranking": "memo_used ascending under corrected_key (identical to V2 1M)",
        "fresh_process_per_child": True,
        "memo_sharing": "forbidden",
        "output_schema": FIELDS,
        "resume_policy": "append by (parent,state); manifest must match; no row rewrite",
        "failure_policy": "nonzero exit or !=1 stdout row -> no CSV row, runlog record, stays pending",
        "wall_time": "solver-reported seconds primary; orchestration wall_seconds in runlog only",
    }


def require_or_create_protocol_manifest(tasks: list[dict[str, str]]) -> None:
    current = current_protocol_manifest(tasks)
    if current["task_set_sha256"] != FROZEN_TASK_SET_SHA256:
        raise RuntimeError("task set digest mismatch vs frozen V2 cohort")
    if current["holdout_task_count"] != FROZEN_TASK_COUNT:
        raise RuntimeError("task count mismatch vs frozen V2 cohort")
    if RUN_MANIFEST.exists():
        recorded = json.loads(RUN_MANIFEST.read_text(encoding="utf-8"))
        if recorded != current and recorded != {**current, "holdout_tasks_file_sha256": recorded.get("holdout_tasks_file_sha256")}:
            # Line-ending variance: allow only the file-bytes SHA to differ.
            rec2 = dict(recorded)
            cur2 = dict(current)
            rec2.pop("holdout_tasks_file_sha256", None)
            cur2.pop("holdout_tasks_file_sha256", None)
            if rec2 != cur2:
                raise RuntimeError(
                    "10k protocol differs from the frozen manifest; refusing to mix rows"
                )
        return
    if OUT_CSV.exists() and OUT_CSV.stat().st_size > 0:
        raise RuntimeError(
            f"{OUT_CSV} exists but {RUN_MANIFEST} does not; refusing to append "
            "because existing row provenance cannot be established"
        )
    RUN_MANIFEST.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_single_probe(task: dict[str, str]) -> dict[str, str]:
    state = task["state"]
    t_start = time.time()
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
    wall = time.time() - t_start

    log_rec: dict[str, object] = {
        "parent": task["parent"],
        "state": state,
        "solver_exit": proc.returncode,
        "wall_seconds": round(wall, 6),
        "attempt": 1,
        "ts": time.time(),
    }
    if proc.returncode != 0:
        log_rec["stderr_tail"] = (proc.stderr or "")[-500:]
        append_runlog(log_rec)
        raise RuntimeError(f"probe failed for {state}: rc={proc.returncode}\n{proc.stderr[-500:]}")

    rows = list(csv.DictReader(proc.stdout.splitlines()))
    if len(rows) != 1:
        log_rec["stdout_tail"] = (proc.stdout or "")[-500:]
        append_runlog(log_rec)
        raise RuntimeError(f"expected 1 row for {state}, got {len(rows)}")
    row = rows[0]
    try:
        log_rec["solver_seconds"] = float(row["seconds"])
    except Exception:
        log_rec["solver_seconds"] = row.get("seconds")
    append_runlog(log_rec)
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


def append_runlog(rec: dict[str, object]) -> None:
    with RUNLOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")


def _worker_init() -> None:
    # Each pool worker is a separate process; solver itself always runs as a
    # fresh subprocess per task, so no memo state can leak across children.
    pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--build", action="store_true")
    args = parser.parse_args()

    if args.build:
        build_solver()
        return

    with TASK_CSV.open(newline="", encoding="utf-8") as f:
        tasks = list(csv.DictReader(f))

    require_or_create_protocol_manifest(tasks)

    completed: set[tuple[str, str]] = set()
    if OUT_CSV.exists():
        with OUT_CSV.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                key = (r["parent"], r["state"])
                if key in completed:
                    raise RuntimeError(f"duplicate probe row: {key}")
                completed.add(key)

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
        out_file.flush()

    done_count = len(completed)
    base_done = len(completed)
    with mp.Pool(processes=args.workers, initializer=_worker_init) as pool:
        for res in pool.imap_unordered(run_single_probe, pending, chunksize=16):
            writer.writerow(res)
            out_file.flush()
            done_count += 1
            if done_count % 50 == 0 or done_count == len(tasks):
                elapsed = time.time() - t0
                speed = (done_count - base_done) / elapsed if elapsed > 0 else 0
                print(f"[{done_count}/{len(tasks)}] elapsed={elapsed:.1f}s ({speed:.2f} tasks/sec)", flush=True)

    out_file.close()
    print("Probe run finished successfully.")


if __name__ == "__main__":
    main()
