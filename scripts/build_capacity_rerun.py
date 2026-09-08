#!/usr/bin/env python3
"""Build the capacity-rerun solver from audited sources and emit a provenance receipt.

This closes a subtle stale-binary hole: the semantic regression cases all fit in
old C2 memo capacity, so an old C2 binary could pass 6/6 regression even though
it does not contain the enlarged d12--d16 tables.  This script therefore:

1. runs the frozen source-diff audit;
2. deletes the target binary before compilation;
3. compiles the audited working-tree source with the frozen C2 compiler flags;
4. records source hashes, binary hash, compiler identity, command, and git HEAD;
5. optionally runs the exact 6/6 regression against that just-built binary.

The receipt is intended to be committed and referenced by the execution
manifest before any endpoint run starts.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts/audit_capacity_rerun_source_diff.py"
REGRESSION = ROOT / "scripts/test_capacity_rerun_regression.py"
DEFAULT_BIN = ROOT / "tmp-kb/order_ab_capacity"
DEFAULT_RECEIPT = ROOT / "results/10x10/cache-aware-below-root-capacity-rerun/build_receipt.json"

SOURCES = [
    "scripts/probe_cert_solver.cpp",
    "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_0.inc",
    "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_1.inc",
    "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_2.inc",
    "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_3.inc",
    "scripts/probe_parts/kyouen_solver_10_kyoenc4_resume_4.inc",
    "scripts/probe_parts/kyouen_solver_10_kyoenc4_witness_log.inc",
]

FROZEN_FLAGS = ["-O2", "-std=c++20"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_checked(cmd: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(cmd), flush=True)
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=capture)
    if p.returncode != 0:
        if capture:
            sys.stderr.write(p.stdout)
            sys.stderr.write(p.stderr)
        raise SystemExit(f"command failed rc={p.returncode}: {' '.join(cmd)}")
    return p


def git_head() -> str:
    return run_checked(["git", "rev-parse", "HEAD"], capture=True).stdout.strip()


def compiler_identity(cxx: str) -> str:
    p = run_checked([cxx, "--version"], capture=True)
    first = p.stdout.splitlines()
    return first[0] if first else p.stdout.strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cxx", default=os.environ.get("CXX", "g++"))
    ap.add_argument("--bin", type=Path, default=DEFAULT_BIN)
    ap.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    ap.add_argument("--run-regression", action="store_true",
                    help="run the preregistered 6/6 exact regression after build")
    args = ap.parse_args()

    binary = args.bin if args.bin.is_absolute() else (ROOT / args.bin)
    receipt = args.receipt if args.receipt.is_absolute() else (ROOT / args.receipt)

    # Fail closed before compiling: only the preregistered source-capacity delta
    # may differ from the C2 base.
    run_checked([sys.executable, str(AUDIT)])

    for rel in SOURCES:
        p = ROOT / rel
        if not p.is_file():
            raise SystemExit(f"missing audited source: {rel}")

    binary.parent.mkdir(parents=True, exist_ok=True)
    receipt.parent.mkdir(parents=True, exist_ok=True)

    # The deletion is deliberate.  A compiler failure must never leave a stale
    # old-C2 executable at the path that the regression later consumes.
    binary.unlink(missing_ok=True)
    if binary.exists():
        raise SystemExit(f"failed to remove pre-existing target binary: {binary}")

    source = ROOT / "scripts/probe_cert_solver.cpp"
    cmd = [args.cxx, *FROZEN_FLAGS, str(source), "-o", str(binary)]
    started = dt.datetime.now(dt.timezone.utc)
    run_checked(cmd)
    finished = dt.datetime.now(dt.timezone.utc)

    if not binary.is_file() or binary.stat().st_size == 0:
        raise SystemExit("compiler returned success but target binary is missing/empty")

    # Use nanosecond mtimes only as an additional sanity check; the stronger
    # provenance is the delete-before-build procedure plus the receipt hashes.
    if binary.stat().st_mtime_ns < int(started.timestamp() * 1_000_000_000):
        raise SystemExit("target binary mtime predates build start; refusing stale artifact")

    head = git_head()
    receipt_obj = {
        "experiment": "10x10-cache-aware-below-root-capacity-rerun",
        "git_head": head,
        "built_at_utc": finished.isoformat(),
        "compiler": compiler_identity(args.cxx),
        "compile_command": cmd,
        "frozen_flags": FROZEN_FLAGS,
        "source_diff_audit": str(AUDIT.relative_to(ROOT)),
        "binary": str(binary.relative_to(ROOT)),
        "binary_size": binary.stat().st_size,
        "binary_sha256": sha256(binary),
        "sources_sha256": {rel: sha256(ROOT / rel) for rel in SOURCES},
        "regression_script": str(REGRESSION.relative_to(ROOT)),
        "regression_run_in_this_build": bool(args.run_regression),
    }
    receipt.write_text(json.dumps(receipt_obj, indent=2, sort_keys=True) + "\n",
                       encoding="utf-8")

    print(f"BUILD PASS binary_sha256={receipt_obj['binary_sha256']}")
    print(f"receipt={receipt.relative_to(ROOT)}")

    if args.run_regression:
        run_checked([sys.executable, str(REGRESSION), "--bin", str(binary)])
        print("BUILD+REGRESSION PASS")


if __name__ == "__main__":
    main()
