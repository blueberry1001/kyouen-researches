#!/usr/bin/env python3
"""Fail-closed preflight for the cache-aware bucket-order optimization.

This script intentionally performs the irreversible source patch only after the
frozen synthetic order-equivalence test and patch dry-run both succeed.  It then
runs the independent source-diff audit immediately.  Any failure stops the
pipeline before build/benchmark.

Usage:
  python scripts/preflight_cache_aware_bucket_order.py --check
      Run equivalence test + patch dry-run only; do not modify solver sources.

  python scripts/preflight_cache_aware_bucket_order.py --apply
      Run equivalence test + patch dry-run, apply the frozen patch, then require
      the independent source-diff audit to pass.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EQ = ROOT / "scripts/test_cache_aware_bucket_order_equivalence.py"
PATCH = ROOT / "scripts/prepare_cache_aware_bucket_order_implementation.py"
AUDIT = ROOT / "scripts/audit_cache_aware_bucket_order_source_diff.py"


def run(label: str, cmd: list[str]) -> None:
    print(f"== {label} ==", flush=True)
    print("+", " ".join(cmd), flush=True)
    p = subprocess.run(cmd, cwd=ROOT)
    if p.returncode != 0:
        raise SystemExit(f"PREFLIGHT FAIL at {label}: rc={p.returncode}")


def main() -> None:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="validate without modifying solver sources")
    mode.add_argument("--apply", action="store_true", help="validate, apply frozen patch, and audit resulting sources")
    args = ap.parse_args()

    for path in (EQ, PATCH, AUDIT):
        if not path.is_file():
            raise SystemExit(f"PREFLIGHT FAIL: missing required tool {path.relative_to(ROOT)}")

    # The mathematical/order-equivalence gate is deliberately first.  We never
    # modify solver source if the proposed transformation itself is not frozen
    # and empirically equivalent on the deterministic fixture suite.
    run("order equivalence", [sys.executable, str(EQ)])

    # Dry-run proves all three frozen OLD snippets occur exactly once and that
    # no source is already partially patched.
    run("patch dry-run", [sys.executable, str(PATCH), "--check"])

    if args.check:
        print("BUCKET PREFLIGHT CHECK PASS")
        print("solver_sources_modified=0")
        return

    run("apply frozen implementation delta", [sys.executable, str(PATCH)])

    # Independent reconstruction from base e9d0460 must match byte-for-byte.
    # If patching somehow produced anything outside the preregistered delta,
    # fail before compilation or timing can occur.
    run("source diff audit", [sys.executable, str(AUDIT)])

    print("BUCKET PREFLIGHT APPLY PASS")
    print("next_gate=build same binary, then C1 12-parent semantic parity")


if __name__ == "__main__":
    main()
