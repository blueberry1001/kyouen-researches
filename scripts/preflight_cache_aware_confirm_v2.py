#!/usr/bin/env python3
"""Pre-run audit for the sealed 10x10 cache-order confirmation V2.

This is an auxiliary guard added after the execution manifest was frozen. It
must not alter the frozen protocol. It verifies, immediately before the first
cohort run, that:

* the frozen cohort and executable/source/tool digests still match the seal;
* the preregistered 12-parent order is unchanged;
* no primary/secondary cohort outputs already exist;
* the raw directory contains no prior parent-condition results.

Run from the repository root:
    python3 scripts/preflight_cache_aware_confirm_v2.py

A PASS is evidence that execution started from a clean, sealed state. It is
not itself part of the preregistered endpoint and must never be used to change
parents, thresholds, or conditions.
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "10x10" / "cache-aware-below-root-confirmation-v2"
MANIFEST = OUT / "execution_manifest.json"

EXPECTED_RESULTS = [
    OUT / "summary_ab.csv",
    OUT / "depth_ab.csv",
    OUT / "depth_visited.csv",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fail(msg: str) -> None:
    raise SystemExit(f"PRE-FLIGHT FAIL: {msg}")


def require_digest(path: Path, expected: str, label: str) -> None:
    if not path.exists():
        fail(f"missing {label}: {path}")
    got = sha256_file(path)
    if got != expected:
        fail(f"{label} SHA256 mismatch: expected={expected} got={got} path={path}")


def main() -> None:
    if not MANIFEST.exists():
        fail(f"missing frozen execution manifest: {MANIFEST}")
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))

    cohort_path = ROOT / man["cohort_file"]
    require_digest(cohort_path, man["cohort_sha256"], "cohort")
    with cohort_path.open(newline="", encoding="utf-8") as f:
        cohort_rows = list(csv.DictReader(f))
    cohort = [r["parent_canonical"].strip() for r in cohort_rows]
    sealed_parents = list(man["cohort"]["parents"])
    if cohort != sealed_parents:
        fail(f"cohort order differs from seal: csv={cohort} manifest={sealed_parents}")
    if len(cohort) != 12 or len(set(cohort)) != 12:
        fail(f"cohort must contain 12 unique parents, got {len(cohort)}/{len(set(cohort))}")

    # Exact executable and every source/include file frozen in the manifest.
    parent_solve = man["parent_solve"]
    require_digest(ROOT / parent_solve["binary"], parent_solve["binary_sha256"], "solver binary")
    for rel, expected in man["include_files_sha256"].items():
        require_digest(ROOT / rel, expected, f"solver source {rel}")

    # Frozen execution/analysis/verifier programs. The supplemental auditor and
    # this preflight are deliberately outside this frozen set.
    frozen_tools = {
        "scripts/run_cache_aware_confirm_v2.py": man["runner_script_sha256"],
        "scripts/analyze_cache_aware_confirm_v2.py": man["analysis_script_sha256"],
        "scripts/verify_10x10_cache_aware_confirm_v2.py": man["verifier_script_sha256"],
        "scripts/test_order_ab_regression.py": man["regression"]["script_sha256"],
    }
    for rel, expected in frozen_tools.items():
        require_digest(ROOT / rel, expected, f"frozen tool {rel}")
    require_digest(OUT / "regression.log", man["regression"]["log_sha256"], "regression log")

    # Reconstruct the intended counterbalanced order from the seal, rather than
    # trusting prose in condition_order.
    ro = man["run_order"]
    if len(ro) != 12:
        fail(f"run_order length must be 12, got {len(ro)}")
    for i, (p, rec) in enumerate(zip(cohort, ro), start=1):
        expected_first = "cache-aware" if i % 2 else "cache-blind"
        if rec.get("rank") != i or rec.get("parent") != p or rec.get("first") != expected_first:
            fail(f"run_order mismatch at rank {i}: {rec}; expected parent={p} first={expected_first}")

    # A clean start matters: otherwise an interrupted/partially inspected run
    # could accidentally be presented as a single sealed execution. Resume is
    # handled only after a separately recorded machine interruption.
    existing = [str(p.relative_to(ROOT)) for p in EXPECTED_RESULTS if p.exists()]
    if existing:
        fail(f"cohort output files already exist: {existing}")
    raw = OUT / "raw"
    if raw.exists():
        nonempty = sorted(p for p in raw.rglob("*") if p.is_file())
        if nonempty:
            preview = [str(p.relative_to(ROOT)) for p in nonempty[:10]]
            fail(f"raw result files already exist ({len(nonempty)}): {preview}")

    # Record only descriptive provenance; HEAD is allowed to be after the seal
    # because auxiliary audits were intentionally added without touching the
    # frozen runner/binary/source files.
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True, capture_output=True, check=True
    ).stdout.strip()
    if status:
        fail("working tree is dirty; commit/stash unrelated changes before sealed execution")

    print("confirmation-V2 preflight: PASS")
    print(f"head={head}")
    print("cohort=12/12 sealed")
    print("binary/source/tool digests=PASS")
    print("counterbalanced run order=PASS")
    print("existing cohort outputs=0")
    print("raw result files=0")
    print("working tree=clean")


if __name__ == "__main__":
    main()
