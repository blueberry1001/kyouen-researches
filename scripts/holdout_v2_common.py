#!/usr/bin/env python3
"""Shared, outcome-blind task construction for the clean 10x10 holdout V2."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SELECTION = REPO_ROOT / "results" / "10x10" / "holdout-v2-parent-selection-preregistered.csv"
OLD_SELECTION = REPO_ROOT / "results" / "10x10" / "blind-probe-parent-selection.csv"
SOURCE_FILES = [
    REPO_ROOT / "results" / "10x10" / "two-stone-90-66-child-proof.csv",
    REPO_ROOT / "results" / "10x10" / "two-stone-90-61-child-proof.csv",
]
BATCH_SIZE = 20


def cells(state: str) -> tuple[int, ...]:
    vals = tuple(sorted(int(x) for x in state.replace("-", ",").split(",") if x.strip()))
    if len(vals) != len(set(vals)):
        raise RuntimeError(f"duplicate cell in state: {state}")
    if any(x < 0 or x >= 100 for x in vals):
        raise RuntimeError(f"cell out of 10x10 range: {state}")
    return vals


def state_text(values: tuple[int, ...]) -> str:
    return ",".join(str(x) for x in values)


def _transform_cell(cell: int, k: int) -> int:
    r, c = divmod(cell, 10)
    rc = (
        (r, c),
        (c, 9 - r),
        (9 - r, 9 - c),
        (9 - c, r),
        (r, 9 - c),
        (9 - r, c),
        (c, r),
        (9 - c, 9 - r),
    )[k]
    return rc[0] * 10 + rc[1]


def canonical_parent(state: str) -> tuple[int, ...]:
    p = cells(state)
    if len(p) != 3:
        raise RuntimeError(f"expected 3-stone parent: {state}")
    return min(tuple(sorted(_transform_cell(x, k) for x in p)) for k in range(8))


def _det4(matrix: list[list[int]]) -> int:
    """Exact Bareiss determinant for the 4x4 circle/line matrix."""
    a = [row[:] for row in matrix]
    sign = 1
    denom = 1
    for k in range(3):
        if a[k][k] == 0:
            swap = next((i for i in range(k + 1, 4) if a[i][k] != 0), None)
            if swap is None:
                return 0
            a[k], a[swap] = a[swap], a[k]
            sign *= -1
        pivot = a[k][k]
        for i in range(k + 1, 4):
            for j in range(k + 1, 4):
                a[i][j] = (a[i][j] * pivot - a[i][k] * a[k][j]) // denom
        denom = pivot
        for i in range(k + 1, 4):
            a[i][k] = 0
    return sign * a[3][3]


def four_is_forbidden(four: tuple[int, ...]) -> bool:
    if len(four) != 4:
        raise RuntimeError("four_is_forbidden requires four points")
    matrix: list[list[int]] = []
    for cell in four:
        y, x = divmod(cell, 10)
        matrix.append([x * x + y * y, x, y, 1])
    return _det4(matrix) == 0


def legal_children(parent: str) -> list[str]:
    p = cells(parent)
    if len(p) != 3:
        raise RuntimeError(f"expected 3-stone parent: {parent}")
    out: list[str] = []
    occupied = set(p)
    for move in range(100):
        if move in occupied:
            continue
        child = tuple(sorted(p + (move,)))
        if not four_is_forbidden(child):
            out.append(state_text(child))
    return out


def load_selection_rows() -> list[dict[str, str]]:
    with SELECTION.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 20:
        raise RuntimeError(f"V2 selection must contain exactly 20 parents, got {len(rows)}")
    return rows


def load_parents() -> list[str]:
    rows = load_selection_rows()
    parents = [r["parent"].strip() for r in rows]
    if len(parents) != len(set(parents)):
        raise RuntimeError("duplicate parent orientation in V2 selection")
    can = [canonical_parent(p) for p in parents]
    if len(can) != len(set(can)):
        raise RuntimeError("D4-duplicate parent in V2 selection")
    return parents


def _source_candidates() -> list[tuple[tuple[int, ...], str, int, str]]:
    rows: list[tuple[tuple[int, ...], str, int, str]] = []
    for path in SOURCE_FILES:
        with path.open(newline="", encoding="utf-8") as f:
            for idx, row in enumerate(csv.DictReader(f)):
                # Selection intentionally reads only the parent state and source position.
                parent = row["state"].strip()
                rows.append((canonical_parent(parent), path.name, idx, parent))
    return rows


def verify_selection() -> None:
    """Recompute V2 parent identities without consulting child outcome columns."""
    with OLD_SELECTION.open(newline="", encoding="utf-8") as f:
        old_rows = [r for r in csv.DictReader(f) if int(r["stones"]) == 3]
    excluded = {canonical_parent(r["parent"].strip()) for r in old_rows}
    if len(excluded) != 19:
        raise RuntimeError(f"expected 19 old D4 orbits, got {len(excluded)}")

    by_canonical: dict[tuple[int, ...], tuple[str, int, str]] = {}
    for can, source, idx, parent in _source_candidates():
        if can in excluded:
            continue
        by_canonical.setdefault(can, (source, idx, parent))
    expected = sorted(by_canonical.items())[:20]

    actual = load_selection_rows()
    for i, ((can, (source, idx, parent)), row) in enumerate(zip(expected, actual), 1):
        got_can = tuple(int(x) for x in row["canonical_parent"].split(","))
        if int(row["selection_index"]) != i:
            raise RuntimeError(f"selection index mismatch at row {i}")
        if row["parent"].strip() != parent:
            raise RuntimeError(f"parent mismatch at row {i}: expected {parent}, got {row['parent']}")
        if got_can != can:
            raise RuntimeError(f"canonical mismatch at row {i}: expected {can}, got {got_can}")
        if row["source"].strip() != source or int(row["source_index"]) != idx:
            raise RuntimeError(f"source provenance mismatch at row {i}")
        generated = legal_children(parent)
        if int(row["candidate_count"]) != len(generated):
            raise RuntimeError(
                f"candidate_count mismatch for {parent}: selection={row['candidate_count']} generated={len(generated)}"
            )

    # Regression anchor: generated legality/order must exactly reproduce one
    # committed V1 child list before V2 is allowed to run.
    anchor = REPO_ROOT / "results" / "10x10" / "blind_probe_children" / "children_0_36_50.txt"
    expected_anchor = [x.strip() for x in anchor.read_text(encoding="utf-8").splitlines() if x.strip()]
    generated_anchor = legal_children("0,36,50")
    if generated_anchor != expected_anchor:
        raise RuntimeError("V2 legal-child generator does not reproduce the committed V1 anchor")


def load_tasks() -> list[tuple[str, int, int, str]]:
    verify_selection()
    tasks: list[tuple[str, int, int, str]] = []
    for parent in load_parents():
        for ordinal, state in enumerate(legal_children(parent)):
            tasks.append((parent, ordinal // BATCH_SIZE, ordinal % BATCH_SIZE, state))
    if len(tasks) != 1914:
        raise RuntimeError(f"unexpected frozen V2 task count: {len(tasks)}")
    if len({(p, s) for p, _b, _pos, s in tasks}) != len(tasks):
        raise RuntimeError("duplicate V2 parent/state task")
    return tasks


def task_set_digest(tasks: list[tuple[str, int, int, str]] | None = None) -> str:
    if tasks is None:
        tasks = load_tasks()
    h = hashlib.sha256()
    for task in tasks:
        data = json.dumps(task, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    return h.hexdigest()


if __name__ == "__main__":
    tasks = load_tasks()
    print(f"parents={len(load_parents())} tasks={len(tasks)} sha256={task_set_digest(tasks)}")
