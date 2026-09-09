#!/usr/bin/env python3
"""Collect the frozen 24-run semantic-parity gate for no-hit fastpath.

This is deliberately a collector, not an analyzer.  It runs the exact C1
12-parent cohort in the order frozen in execution_plan.json, using one fresh
process per parent/implementation, and writes raw stdout/stderr/instrumentation
for the dedicated verifier.  It never computes timing ratios or opens the
72-run timing endpoint.

Required preparation, in order:
  1. apply scripts/prepare_cache_aware_nohit_fastpath.py --apply
  2. pass scripts/audit_cache_aware_nohit_fastpath_source_diff.py
  3. build with scripts/build_nohit_fastpath_binary.py
  4. commit/freeze build_receipt.json if required by the execution protocol
  5. run this collector
  6. run scripts/verify_nohit_fastpath_parity.py

Any operational failure preserves the raw failure artifacts and exits nonzero.
Existing raw parity output is never overwritten.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "10x10" / "cache-aware-nohit-fastpath"
PLAN_PATH = OUT / "execution_plan.json"
BUILD_RECEIPT_PATH = OUT / "build_receipt.json"
RAW = OUT / "raw_parity"
COLLECTION_RECEIPT = OUT / "parity_collection_receipt.json"
AUDIT = ROOT / "scripts" / "audit_cache_aware_nohit_fastpath_source_diff.py"

EXACT_SHRINK = 0
EXACT_LOAD = 90
ROOT_DEPTH = 3
DEFAULT_TIMEOUT = 14400.0
EXPECTED_PARENTS = [
    "0,11,35", "11,38,44", "11,78,87", "12,24,68", "12,32,55",
    "13,52,57", "14,64,74", "23,44,45", "3,47,63", "3,53,84",
    "4,24,26", "4,42,54",
]
IMPL_MAP = {"S": "sort", "F": "nohit"}


def fail(msg: str) -> None:
    raise SystemExit(f"NOHIT PARITY COLLECT FAIL: {msg}")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict:
    if not path.is_file():
        fail(f"missing {rel(path)}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        fail(f"cannot parse {rel(path)}: {e}")
    raise AssertionError


def check_single_stdout_row(text: str, parent: str) -> None:
    rows = list(csv.DictReader(text.splitlines()))
    if len(rows) != 1:
        fail(f"{parent}: expected exactly one solver stdout row, got {len(rows)}")
    row = rows[0]
    if row.get("outcome") not in ("WIN", "LOSS"):
        fail(f"{parent}: unexpected outcome {row.get('outcome')!r}")


def frozen_run_order(plan: dict) -> list[tuple[int, int, str, str]]:
    parents = plan.get("parents_ranked")
    if parents != EXPECTED_PARENTS:
        fail("parents_ranked differs from the frozen C1 12-parent cohort")
    parity = plan.get("parity", {})
    if parity.get("runs") != 24 or parity.get("fresh_process_each_run") is not True or parity.get("serial") is not True:
        fail("parity execution-plan invariants are not frozen at 24 fresh serial runs")
    order_rule = parity.get("order_by_rank_parity", {})
    if order_rule.get("odd_rank") != ["S", "F"] or order_rule.get("even_rank") != ["F", "S"]:
        fail("parity order differs from frozen odd S->F / even F->S")

    runs: list[tuple[int, int, str, str]] = []
    order_index = 0
    for zero_idx, parent in enumerate(parents):
        rank = zero_idx + 1
        labels = order_rule["odd_rank"] if rank % 2 else order_rule["even_rank"]
        for label in labels:
            if label not in IMPL_MAP:
                fail(f"unknown frozen implementation label {label!r}")
            order_index += 1
            runs.append((order_index, rank, parent, IMPL_MAP[label]))
    if len(runs) != 24:
        fail(f"constructed run order has {len(runs)} entries, expected 24")
    return runs


def assert_clean_endpoint() -> None:
    if COLLECTION_RECEIPT.exists():
        fail(f"collection receipt already exists: {rel(COLLECTION_RECEIPT)}")
    if RAW.exists():
        entries = list(RAW.iterdir())
        if entries:
            fail(f"raw_parity is nonempty ({len(entries)} entries); refusing overwrite")
    # Parity must precede all timing output.  Do not accidentally bless a tree
    # where endpoint timing has already been opened.
    forbidden = [OUT / "timing", OUT / "timing_summary.csv", OUT / "timing_analysis.json"]
    present = [rel(p) for p in forbidden if p.exists()]
    if present:
        fail(f"timing artifacts already exist before parity gate: {present}")


def verify_build_and_source() -> tuple[Path, dict]:
    plan = load_json(PLAN_PATH)
    receipt = load_json(BUILD_RECEIPT_PATH)
    if receipt.get("experiment") != "10x10-cache-aware-nohit-fastpath":
        fail("build receipt belongs to another experiment")
    binary_rel = receipt.get("binary")
    binary_sha = receipt.get("binary_sha256")
    if not isinstance(binary_rel, str) or not isinstance(binary_sha, str):
        fail("build receipt lacks binary/binary_sha256")
    binary = ROOT / binary_rel
    if not binary.is_file():
        fail(f"sealed binary missing: {rel(binary)}")
    if sha256_file(binary) != binary_sha:
        fail("binary SHA256 differs from build receipt")
    if receipt.get("same_binary_required_for") != ["sort", "nohit"]:
        fail("build receipt does not seal one binary for sort/nohit")
    if receipt.get("flags") != ["-O2", "-std=c++20"]:
        fail("build flags differ from frozen endpoint flags")

    audit = subprocess.run(
        [sys.executable, rel(AUDIT)], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if audit.returncode != 0 or "NOHIT SOURCE AUDIT PASS" not in audit.stdout:
        print(audit.stdout, end="")
        print(audit.stderr, end="", file=sys.stderr)
        fail("dedicated source-diff audit does not PASS")
    return binary, plan


def run_one(binary: Path, order_index: int, rank: int, parent: str, impl: str,
            timeout: float) -> dict:
    run_dir = RAW / f"{parent.replace(',', '_')}_{impl}"
    if run_dir.exists():
        fail(f"run directory already exists: {rel(run_dir)}")
    run_dir.mkdir(parents=True)
    stdout_path = run_dir / "stdout.txt"
    stderr_path = run_dir / "stderr.txt"
    instr_path = run_dir / "depth_raw.csv"
    meta_path = run_dir / "run_meta.json"

    with tempfile.NamedTemporaryFile(
        "w", suffix=".txt", delete=False, encoding="utf-8", dir=str(ROOT)
    ) as tmp:
        tmp.write(parent + "\n")
        state_path = Path(tmp.name)

    cmd = [
        str(binary), str(state_path), str(EXACT_SHRINK), str(EXACT_LOAD), "0", "0",
        "--root-depth", str(ROOT_DEPTH),
        "--below-root-order", "cache-aware",
        "--cache-aware-order-impl", impl,
        "--memo-instr-out", str(instr_path),
    ]
    started = datetime.now(timezone.utc)
    t0 = time.monotonic()
    rc: int | None = None
    timed_out = False
    out = ""
    err = ""
    try:
        pop = subprocess.Popen(
            cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        try:
            out, err = pop.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            pop.kill()
            out, err = pop.communicate()
        rc = pop.returncode
    finally:
        state_path.unlink(missing_ok=True)
    wall = time.monotonic() - t0
    stdout_path.write_text(out, encoding="utf-8")
    stderr_path.write_text(err, encoding="utf-8")

    meta = {
        "order_index": order_index,
        "rank": rank,
        "parent": parent,
        "implementation": impl,
        "started_at_utc": started.isoformat(),
        "wall_seconds": wall,
        "returncode": rc,
        "timed_out": timed_out,
        "command_semantics": {
            "shrink": EXACT_SHRINK,
            "load": EXACT_LOAD,
            "root_depth": ROOT_DEPTH,
            "below_root_order": "cache-aware",
            "cache_aware_order_impl": impl,
        },
    }
    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Preserve all raw evidence before failing closed.
    if timed_out:
        fail(f"order {order_index}/24 {parent}/{impl}: timeout after {timeout}s")
    if rc != 0:
        fail(f"order {order_index}/24 {parent}/{impl}: rc={rc}; see {rel(stderr_path)}")
    if f"below_root_order=cache-aware" not in err:
        fail(f"order {order_index}/24 {parent}/{impl}: cache-aware marker missing")
    if f"cache_aware_impl={impl}" not in err:
        fail(f"order {order_index}/24 {parent}/{impl}: implementation marker missing")
    if not instr_path.is_file() or instr_path.stat().st_size == 0:
        fail(f"order {order_index}/24 {parent}/{impl}: instrumentation output missing/empty")
    check_single_stdout_row(out, parent)

    files = {}
    for p in (stdout_path, stderr_path, instr_path, meta_path):
        files[p.name] = sha256_file(p)
    return {
        "order_index": order_index,
        "rank": rank,
        "parent": parent,
        "implementation": impl,
        "wall_seconds": wall,
        "files_sha256": files,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                    help="operational per-run timeout seconds; default 14400")
    args = ap.parse_args()
    if args.timeout <= 0:
        fail("timeout must be positive")

    binary, plan = verify_build_and_source()
    runs = frozen_run_order(plan)
    assert_clean_endpoint()
    RAW.mkdir(parents=True, exist_ok=True)

    print("NOHIT PARITY COLLECT START")
    print(f"binary={rel(binary)}")
    print(f"binary_sha256={sha256_file(binary)}")
    print("runs=24 fresh serial; timing analysis forbidden")
    completed: list[dict] = []
    for order_index, rank, parent, impl in runs:
        print(f"[{order_index:02d}/24] rank={rank} parent={parent} impl={impl}", flush=True)
        completed.append(run_one(binary, order_index, rank, parent, impl, args.timeout))

    receipt = load_json(BUILD_RECEIPT_PATH)
    collection = {
        "experiment": "10x10-cache-aware-nohit-fastpath",
        "status": "24/24 operationally complete; UNVERIFIED semantic parity",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "runs_completed": len(completed),
        "fresh_process_each_run": True,
        "serial": True,
        "analysis_performed": False,
        "timing_gate_open": False,
        "binary": rel(binary),
        "binary_sha256": receipt["binary_sha256"],
        "execution_plan_sha256": sha256_file(PLAN_PATH),
        "build_receipt_sha256": sha256_file(BUILD_RECEIPT_PATH),
        "source_audit": "PASS before collection",
        "runs": completed,
        "next_required_command": "python3 scripts/verify_nohit_fastpath_parity.py",
    }
    tmp = COLLECTION_RECEIPT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(collection, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(COLLECTION_RECEIPT)

    print("NOHIT PARITY COLLECT COMPLETE: 24/24")
    print("semantic_status=UNVERIFIED")
    print("timing_gate=CLOSED")
    print(f"receipt={rel(COLLECTION_RECEIPT)}")
    print("next=python3 scripts/verify_nohit_fastpath_parity.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
