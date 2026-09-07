#!/usr/bin/env python3
"""Freeze the outcome-blind 10x10 holdout-v2 child task set.

Reads only the already-frozen parent list. For each 3-stone parent, enumerates
all empty cells and excludes moves that immediately form a 4-point concyclic
or collinear set (4x4 determinant == 0). No game-value, exact-outcome, probe,
or memo data is read.

The expected task count and CSV digest are pinned below so any accidental rule
or ordering change aborts before probes are collected.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
from itertools import permutations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "results" / "10x10" / "fresh-parent-holdout-v2"
PARENTS = DIR / "parents.csv"
TASKS = DIR / "tasks.csv"
MANIFEST = DIR / "tasks.manifest.json"
EXPECTED_PARENT_COUNT = 24
EXPECTED_TASK_COUNT = 2292
EXPECTED_TASKS_SHA256 = "907dc011eb64640ca3722039b0ebcfc0b604e7ad37bb3e7576c9253c607233e1"

PERMS = list(permutations(range(4)))
SIGNS = []
for p in PERMS:
    inv = sum(p[i] > p[j] for i in range(4) for j in range(i + 1, 4))
    SIGNS.append(-1 if inv & 1 else 1)


def determinant4(rows: list[tuple[int, int, int, int]]) -> int:
    total = 0
    for sign, perm in zip(SIGNS, PERMS):
        prod = 1
        for i, j in enumerate(perm):
            prod *= rows[i][j]
        total += sign * prod
    return total


def immediate_terminal(state: tuple[int, int, int, int]) -> bool:
    rows = []
    for cell in state:
        x, y = cell % 10, cell // 10
        rows.append((x * x + y * y, x, y, 1))
    return determinant4(rows) == 0


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    with PARENTS.open(newline="", encoding="utf-8") as f:
        parent_rows = list(csv.DictReader(f))
    if len(parent_rows) != EXPECTED_PARENT_COUNT:
        raise SystemExit(f"expected {EXPECTED_PARENT_COUNT} parents, got {len(parent_rows)}")

    out = io.StringIO(newline="")
    w = csv.writer(out, lineterminator="\n")
    w.writerow(["selection_index", "parent", "move", "state"])
    per_parent = []
    count = 0

    for row in parent_rows:
        idx = int(row["selection_index"])
        parent = tuple(int(x) for x in row["parent"].split(","))
        if len(parent) != 3 or tuple(sorted(parent)) != parent or len(set(parent)) != 3:
            raise SystemExit(f"invalid parent row: {row}")
        continuing = 0
        immediate = []
        for move in range(100):
            if move in parent:
                continue
            state = tuple(sorted(parent + (move,)))
            if immediate_terminal(state):
                immediate.append(move)
                continue
            w.writerow([idx, row["parent"], move, ",".join(map(str, state))])
            continuing += 1
            count += 1
        per_parent.append({
            "selection_index": idx,
            "parent": row["parent"],
            "continuing_children": continuing,
            "immediate_terminal_moves": immediate,
        })

    data = out.getvalue().encode("utf-8")
    digest = sha256_bytes(data)
    if count != EXPECTED_TASK_COUNT:
        raise SystemExit(f"task-count drift: expected {EXPECTED_TASK_COUNT}, got {count}")
    if digest != EXPECTED_TASKS_SHA256:
        raise SystemExit(f"task digest drift: expected {EXPECTED_TASKS_SHA256}, got {digest}")

    DIR.mkdir(parents=True, exist_ok=True)
    TASKS.write_bytes(data)
    manifest = {
        "format": 1,
        "parent_count": len(parent_rows),
        "task_count": count,
        "tasks_sha256": digest,
        "selection_sha256": sha256_bytes(PARENTS.read_bytes()),
        "enumeration": "parents in parents.csv order; move cell ascending 0..99",
        "terminal_filter": "exclude occupied cells and 4-point determinant==0 (concyclic or collinear immediate win)",
        "outcome_data_read": False,
        "per_parent": per_parent,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"frozen {count} tasks sha256={digest}")


if __name__ == "__main__":
    main()
