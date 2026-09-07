#!/usr/bin/env python3
"""P4-P7 verification gate for the clean holdout V2 artifacts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from analyze_probe_holdout_v2 import load_unique_rows, verify_coverage  # noqa: E402
from holdout_v2_common import load_tasks, task_set_digest, verify_selection  # noqa: E402

BASE_SHA = "2bcd387102874ee20ee641ebd7311c0101d849b5"
EXPECTED_TASKS = 1914
EXPECTED_DIGEST = "22ec3bf65379b64e8aa8a35dea8b2264a37bd9e9ebd42425d0932c7dfc2a8728"
OUT_DIR = REPO_ROOT / "results" / "10x10" / "blind-probe-holdout-v2"
PROTECTED_V1 = [
    "docs/10X10_PROBE_HOLDOUT_PREREGISTRATION.md",
    "results/10x10/holdout-parent-selection-preregistered.csv",
    "results/10x10/two-stone-90-66-child-proof.csv",
    "results/10x10/two-stone-90-61-child-proof.csv",
    "scripts/run_probe_holdout_independent.py",
    "scripts/analyze_probe_holdout_preregistered.py",
    "scripts/probe_cert_solver.cpp",
    "scripts/probe_parts",
]


def verify_base_unchanged() -> None:
    proc = subprocess.run(["git", "diff", "--quiet", BASE_SHA, "--", *PROTECTED_V1], cwd=REPO_ROOT)
    if proc.returncode == 1:
        subprocess.run(["git", "diff", BASE_SHA, "--", *PROTECTED_V1], cwd=REPO_ROOT)
        raise RuntimeError("protected V1/source/solver paths changed relative to frozen base")
    if proc.returncode != 0:
        raise RuntimeError(f"git diff failed with rc={proc.returncode}")


def manifests(pattern: str) -> list[dict[str, object]]:
    paths = sorted(OUT_DIR.glob(pattern))
    if not paths:
        raise RuntimeError(f"no manifests match {pattern}")
    return [json.loads(p.read_text(encoding="utf-8")) for p in paths]


def verify_manifests() -> None:
    probe = manifests("independent_probe_1000000_w*-of-*.protocol.json")
    exact = manifests("exact_outcomes_w*-of-*.protocol.json")
    for m in probe:
        if m.get("budget") != 1_000_000 or m.get("shrink") != 3 or m.get("load") != 80:
            raise RuntimeError(f"bad primary probe protocol: {m}")
    for m in exact:
        if m.get("budget") != 0 or m.get("shrink") != 0 or m.get("load") != 90:
            raise RuntimeError(f"bad exact protocol: {m}")
    for m in probe + exact:
        if m.get("full_task_count") != EXPECTED_TASKS or m.get("full_tasks_sha256") != EXPECTED_DIGEST:
            raise RuntimeError("manifest is not bound to the frozen V2 task set")
    source_hashes = {str(m.get("solver_sources_sha256")) for m in probe + exact}
    if len(source_hashes) != 1:
        raise RuntimeError(f"solver source digest drift across V2 runs: {source_hashes}")


def main() -> None:
    verify_base_unchanged()
    verify_selection()
    tasks = load_tasks()
    if len(tasks) != EXPECTED_TASKS or task_set_digest(tasks) != EXPECTED_DIGEST:
        raise RuntimeError("recomputed V2 task set differs from preregistered manifest")
    verify_manifests()
    probes = load_unique_rows("independent_probe_1000000_w*-of-*.csv", "probe_outcome")
    exact = load_unique_rows("exact_outcomes_w*-of-*.csv", "outcome")
    verify_coverage(probes, exact)
    summary_path = OUT_DIR / "preregistered_v2_summary.json"
    if not summary_path.exists():
        raise RuntimeError("primary V2 summary has not been generated")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("task_set_sha256") != EXPECTED_DIGEST or summary.get("tasks") != EXPECTED_TASKS:
        raise RuntimeError("primary summary does not bind to the frozen task set")
    print(f"V2 VERIFIED: parents=20 tasks={EXPECTED_TASKS} sha256={EXPECTED_DIGEST}")


if __name__ == "__main__":
    main()
