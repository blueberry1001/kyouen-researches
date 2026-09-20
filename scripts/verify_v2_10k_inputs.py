#!/usr/bin/env python3
"""P0 input-integrity check for the V2 10k probe experiment.

Verifies the frozen 12-parent / 1,136-child cohort is used verbatim:
parents, task count, no duplicates, set equality with the frozen exact
targets and 1M probe targets (normalized spelling), task order, and the
canonical task-set digest. Exits nonzero on any mismatch (experiment stops).
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
V2 = REPO_ROOT / "results" / "10x10" / "clean-holdout-v2"
EXPECTED_TASK_SET_SHA = "aeccb6662a37ef25faf3fe6d0ab6707a9677718889139123060fff4a48566bc7"
EXPECTED_PARENTS = 12
EXPECTED_TASKS = 1136


def norm(s: str) -> str:
    return "-".join(str(x) for x in sorted(int(v) for v in s.replace(",", "-").split("-") if v != ""))


def load(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    tasks = load(V2 / "exact_task_list.csv")
    exact = load(V2 / "exact_outcomes.csv")
    with (V2 / "tasks_manifest.json").open(encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["parent_count"] == EXPECTED_PARENTS, manifest
    assert manifest["total_tasks"] == EXPECTED_TASKS, manifest
    assert manifest["task_set_sha256"] == EXPECTED_TASK_SET_SHA, manifest
    assert len(tasks) == EXPECTED_TASKS, len(tasks)
    assert len({r["parent"].strip() for r in tasks}) == EXPECTED_PARENTS

    keys = [(r["parent"].strip(), norm(r["state"])) for r in tasks]
    assert len(keys) == len(set(keys)), "duplicate tasks"
    ekeys = [(r["parent"].strip(), norm(r["state"])) for r in exact]
    assert set(keys) == set(ekeys), "task set != exact set"
    assert keys == ekeys, "task order != exact order"

    probe_path = V2 / "independent_probe_1000000.csv"
    if probe_path.exists():
        probe = load(probe_path)
        pkeys = [(r["parent"].strip(), norm(r["state"])) for r in probe]
        assert len(pkeys) == EXPECTED_TASKS and len(set(pkeys)) == EXPECTED_TASKS
        assert set(keys) == set(pkeys), "task set != 1M probe set"

    h = hashlib.sha256()
    for t in tasks:
        data = json.dumps(
            [t["parent"], int(t["batch"]), int(t["batch_position"]), t["state"]],
            separators=(",", ":"),
        ).encode()
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    assert h.hexdigest() == EXPECTED_TASK_SET_SHA, h.hexdigest()

    # Per-parent counts must match the frozen manifest.
    from collections import Counter
    counts = Counter(p for p, _ in keys)
    for ps in manifest["parent_stats"]:
        assert counts[ps["parent"]] == ps["children_count"], ps
    print(f"P0 OK: 12 parents, 1136 tasks, no dups, task_set_sha={EXPECTED_TASK_SET_SHA}")
    print("per-parent:", dict(sorted(counts.items())))


if __name__ == "__main__":
    sys.exit(main())
