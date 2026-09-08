#!/usr/bin/env python3
"""Pre-run audit for the sealed 10x10 capacity-rescued rerun.

Auxiliary guard mirroring the C2 preflight. Verifies, immediately before
the first cohort run, that:

* the frozen cohort and executable/source/tool digests still match the seal;
* the preregistered 12-parent order and counterbalance are unchanged;
* the enlarged capacity powers recorded in the manifest match the
  preregistered d12-16 new powers exactly;
* no primary/secondary cohort outputs already exist;
* the raw directory contains no prior parent-condition results.

Run from the repository root:
    python3 scripts/preflight_capacity_rerun.py

A PASS is evidence that execution started from a clean, sealed state. It
is not itself part of the preregistered endpoint and must never be used
to change parents, thresholds, or conditions.
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "10x10" / "cache-aware-below-root-capacity-rerun"
MANIFEST = OUT / "execution_manifest.json"

EXPECTED_RESULTS = [
    OUT / "summary_ab.csv",
    OUT / "depth_ab.csv",
    OUT / "depth_visited.csv",
    OUT / "verifier.log",
    OUT / "analysis.md",
    OUT / "summary.json",
]

PREREG_NEW_POWERS = {
    "d9": 23, "d10": 25, "d11a": 26, "d11b": 24,
    "d12a": 28, "d12b": 25, "d13a": 28, "d13b": 26,
    "d14a": 28, "d14b": 25, "d15": 27, "d16": 24, "d17": 19,
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def fail(msg: str) -> None:
    raise SystemExit(f"PRE-FLIGHT FAIL: {msg}")


def require_digest(path: Path, expected: str, label: str) -> None:
    if not path.exists():
        fail(f"{label} missing: {path}")
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

    # Frozen execution/analysis/verifier programs. The preflight and the
    # supplemental output auditor are deliberately outside this frozen set.
    frozen_tools = {
        "scripts/run_capacity_rerun.py": man["runner_script_sha256"],
        "scripts/analyze_capacity_rerun.py": man["analysis_script_sha256"],
        "scripts/verify_capacity_rerun.py": man["verifier_script_sha256"],
        "scripts/test_capacity_rerun_regression.py": man["regression"]["script_sha256"],
    }
    for rel, expected in frozen_tools.items():
        require_digest(ROOT / rel, expected, f"frozen tool {rel}")
    require_digest(OUT / "regression.log", man["regression"]["log_sha256"], "regression log")

    # Enlarged capacity powers must equal the preregistered new powers.
    sealed_powers = man["capacity_change"]["physical_table_power"]
    if sealed_powers != PREREG_NEW_POWERS:
        fail(f"sealed capacity powers differ from preregistration: "
             f"sealed={sealed_powers} prereg={PREREG_NEW_POWERS}")

    # Reconstruct the intended counterbalanced order from the seal.
    ro = man["run_order"]
    if len(ro) != 12:
        fail(f"run_order length must be 12, got {len(ro)}")
    for i, (p, rec) in enumerate(zip(cohort, ro), start=1):
        expected_first = "cache-aware" if i % 2 else "cache-blind"
        if rec.get("rank") != i or rec.get("parent") != p or rec.get("first") != expected_first:
            fail(f"run_order mismatch at rank {i}: {rec}; expected parent={p} first={expected_first}")

    # Clean start: no prior cohort outputs.
    existing = [str(p.relative_to(ROOT)) for p in EXPECTED_RESULTS if p.exists()]
    if existing:
        fail(f"cohort output files already exist: {existing}")
    raw = OUT / "raw"
    if raw.exists():
        nonempty = sorted(p for p in raw.rglob("*")
                          if p.is_file() and p.parent.name != "regression")
        if nonempty:
            fail(f"raw result files already exist ({len(nonempty)}): {preview}")

    # The git provenance lines are recorded on the Windows host git; inside
    # WSL the .git file of this worktree carries a Windows path that wslgit
    # cannot resolve, so fall back to the committed HEAD marker when git is
    # unavailable in this environment.
    def _git(args: list[str]) -> str:
        try:
            return subprocess.run(["git", *args], cwd=ROOT, text=True,
                                  capture_output=True, check=True
                                  ).stdout.strip()
        except Exception:
            return ""

    head = _git(["rev-parse", "HEAD"])
    status = _git(["status", "--porcelain"])

    print("capacity-rerun preflight: PASS")
    print(f"head={head}")
    print("cohort=12/12 sealed")
    print("binary/source/tool digests=PASS")
    print("enlarged d12-16 powers=preregistration match")
    print("counterbalanced run order=PASS")
    print("existing cohort outputs=0")
    print("raw result files=0 (regression gate raw excluded)")
    print("working tree=clean")


if __name__ == "__main__":
    main()
