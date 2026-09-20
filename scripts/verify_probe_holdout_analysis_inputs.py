#!/usr/bin/env python3
"""Verify that holdout analysis still uses the preregistered input snapshot.

This guard intentionally does not inspect exact WIN/LOSS labels or probe outcomes.
It checks provenance/identity only:

* selection + blind_probe_children must be byte-identical (for tracked files) to
  the pre-probe commit frozen below, with no untracked files under those paths;
* the current ordered probe task list must match the task count/digest recorded
  by the run protocol manifest;
* every collected probe row must retain the preregistered parent, batch and
  batch-position identity for its state.

Run this immediately before analyze_probe_holdout_preregistered.py.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FROZEN_INPUT_COMMIT = "c2a127f69b8a62a92ec3ebc9d2b564f11bba306c"
SELECTION = REPO_ROOT / "results" / "10x10" / "holdout-parent-selection-preregistered.csv"
CHILDREN_DIR = REPO_ROOT / "results" / "10x10" / "blind_probe_children"
OUT_DIR = REPO_ROOT / "results" / "10x10" / "blind-probe-holdout"
PROBE_CSV = OUT_DIR / "independent_probe_1000000.csv"
RUN_MANIFEST = OUT_DIR / "independent_probe_1000000.protocol.json"
RUNNER = REPO_ROOT / "scripts" / "run_probe_holdout_independent.py"


def run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, text=True, capture_output=True, check=False
    )


def verify_frozen_files() -> None:
    selection_path = str(SELECTION.relative_to(REPO_ROOT))
    children_path = str(CHILDREN_DIR.relative_to(REPO_ROOT))

    # The selection and the children batch files are frozen pre-probe inputs.
    # Exact-outcome CSVs are the measured labels collected AFTER the freeze
    # (b5172a4-era exacts were already tracked; holdout exacts are new), so
    # they are verified structurally below, not byte-compared here.
    diff = run_git(["diff", "--no-ext-diff", "--quiet", FROZEN_INPUT_COMMIT, "--",
                    selection_path, f"{children_path}/children_*.txt"])
    if diff.returncode == 1:
        raise RuntimeError(
            "selection/children batch files differ from the frozen pre-probe commit "
            f"{FROZEN_INPUT_COMMIT}; refusing analysis"
        )
    if diff.returncode != 0:
        raise RuntimeError(f"git diff failed: {diff.stderr.strip()}")

    # git diff ignores untracked files, while glob-based loaders do not.  An
    # untracked children_* file could otherwise silently enter analysis.
    # (Untracked exact_* files are the expected post-freeze outcome payload;
    # they are allow-listed by task identity in verify_task_manifest_and_probe_rows
    # and cross-checked against the frozen children set in the analyzer.)
    untracked = run_git(["ls-files", "--others", "--exclude-standard", "--",
                         selection_path, f"{children_path}/children_*.txt"])
    if untracked.returncode != 0:
        raise RuntimeError(f"git ls-files failed: {untracked.stderr.strip()}")
    extras = [line for line in untracked.stdout.splitlines() if line.strip()]
    if extras:
        raise RuntimeError(
            "untracked files exist under frozen holdout inputs and could affect glob loading: "
            + ", ".join(extras[:10])
        )


def load_runner_module():
    spec = importlib.util.spec_from_file_location("holdout_runner", RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_task_manifest_and_probe_rows() -> tuple[int, int]:
    if not RUN_MANIFEST.exists():
        raise FileNotFoundError(
            f"missing {RUN_MANIFEST}; no preregistered run provenance to verify"
        )
    if not PROBE_CSV.exists():
        raise FileNotFoundError(PROBE_CSV)

    runner = load_runner_module()
    tasks = runner.load_tasks()
    recorded = json.loads(RUN_MANIFEST.read_text(encoding="utf-8"))
    expected_count = len(tasks)
    expected_digest = runner.task_set_digest(tasks)
    if recorded.get("holdout_task_count") != expected_count:
        raise RuntimeError(
            "protocol task count does not match frozen current task list: "
            f"manifest={recorded.get('holdout_task_count')} current={expected_count}"
        )
    if recorded.get("holdout_tasks_sha256") != expected_digest:
        raise RuntimeError("protocol task digest does not match frozen current task list")

    expected = {
        (parent, state.replace(",", "-")): (batch, pos)
        for parent, batch, pos, state in tasks
    }
    with PROBE_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (row["parent"].strip(), row["state"].strip().replace(",", "-"))
        if key in seen:
            raise RuntimeError(f"duplicate probe row: {key}")
        seen.add(key)
        if key not in expected:
            raise RuntimeError(f"probe row outside frozen task list: {key}")
        batch, pos = expected[key]
        if int(row["batch"]) != batch or int(row["batch_position"]) != pos:
            raise RuntimeError(
                f"probe task identity drift for {key}: "
                f"csv=({row['batch']},{row['batch_position']}) frozen=({batch},{pos})"
            )

    missing = set(expected) - seen
    if missing:
        raise RuntimeError(f"probe CSV incomplete: {len(missing)} frozen tasks are missing")
    return expected_count, len(rows)


def main() -> None:
    verify_frozen_files()
    task_count, row_count = verify_task_manifest_and_probe_rows()
    print(
        "holdout analysis inputs verified: "
        f"frozen_commit={FROZEN_INPUT_COMMIT} tasks={task_count} probe_rows={row_count}"
    )


if __name__ == "__main__":
    main()
