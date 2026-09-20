#!/usr/bin/env python3
"""Build the capacity-rerun solver from audited sources and emit a provenance receipt.

This closes three provenance holes:

1. the semantic regression cases all fit in old C2 memo capacity, so an old C2
   binary could pass 6/6 regression even though it lacks the enlarged tables;
2. a receipt must never claim that regression was run merely because it was
   requested -- it is published only after a successful regression;
3. the regression parent/reference contract must itself be frozen and hashed,
   rather than silently drifting inside the executable gate.

The script therefore audits sources, deletes any stale target, rebuilds with the
frozen flags, optionally runs the frozen-contract exact regression against that
just-built binary, and only then atomically publishes a receipt describing what
actually succeeded.
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
REGRESSION = ROOT / "scripts/test_capacity_rerun_regression_frozen.py"
REGRESSION_IMPL = ROOT / "scripts/test_capacity_rerun_regression.py"
REGRESSION_EXPECTED = ROOT / "results/10x10/cache-aware-below-root-capacity-rerun/regression_expected.json"
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


def atomic_write_json(path: Path, obj: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


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

    # A failed new attempt must not leave an old successful receipt that could be
    # mistaken for provenance of the newly requested build.
    receipt.unlink(missing_ok=True)
    receipt.with_name(receipt.name + ".tmp").unlink(missing_ok=True)

    # Fail closed before compiling: only the preregistered source-capacity delta
    # may differ from the C2 base.
    run_checked([sys.executable, str(AUDIT)])

    for rel in SOURCES:
        p = ROOT / rel
        if not p.is_file():
            raise SystemExit(f"missing audited source: {rel}")
    for p in (REGRESSION, REGRESSION_IMPL, REGRESSION_EXPECTED):
        if not p.is_file():
            raise SystemExit(f"missing regression contract input: {p.relative_to(ROOT)}")

    binary.parent.mkdir(parents=True, exist_ok=True)
    receipt.parent.mkdir(parents=True, exist_ok=True)

    # A compiler failure must never leave a stale old-C2 executable at the path
    # that the regression or endpoint runner later consumes.
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

    if binary.stat().st_mtime_ns < int(started.timestamp() * 1_000_000_000):
        raise SystemExit("target binary mtime predates build start; refusing stale artifact")

    head = git_head()
    binary_hash = sha256(binary)
    regression_status = "not-requested"

    print(f"BUILD PASS binary_sha256={binary_hash}")

    if args.run_regression:
        run_checked([sys.executable, str(REGRESSION), "--bin", str(binary)])
        # Re-hash after regression so the receipt also proves the tested artifact
        # was not modified while the regression was running.
        if sha256(binary) != binary_hash:
            raise SystemExit("binary changed during regression; refusing provenance receipt")
        regression_status = "pass"
        print("BUILD+REGRESSION PASS")

    receipt_obj = {
        "experiment": "10x10-cache-aware-below-root-capacity-rerun",
        "git_head": head,
        "built_at_utc": finished.isoformat(),
        "compiler": compiler_identity(args.cxx),
        "compile_command": cmd,
        "frozen_flags": FROZEN_FLAGS,
        "source_diff_audit": str(AUDIT.relative_to(ROOT)),
        "source_diff_audit_sha256": sha256(AUDIT),
        "binary": str(binary.relative_to(ROOT)),
        "binary_size": binary.stat().st_size,
        "binary_sha256": binary_hash,
        "sources_sha256": {rel: sha256(ROOT / rel) for rel in SOURCES},
        "regression_script": str(REGRESSION.relative_to(ROOT)),
        "regression_script_sha256": sha256(REGRESSION),
        "regression_impl": str(REGRESSION_IMPL.relative_to(ROOT)),
        "regression_impl_sha256": sha256(REGRESSION_IMPL),
        "regression_expected": str(REGRESSION_EXPECTED.relative_to(ROOT)),
        "regression_expected_sha256": sha256(REGRESSION_EXPECTED),
        "regression_requested": bool(args.run_regression),
        "regression_status": regression_status,
    }
    atomic_write_json(receipt, receipt_obj)
    print(f"receipt={receipt.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
