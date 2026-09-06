#!/usr/bin/env python3
"""Validate full-child blind-probe inputs before confirmatory aggregation.

This guard is intentionally stricter than analyze_probe_blind_validation.py.
It refuses to treat partially solved or partially probed parents as complete,
and checks that batch concatenation is a well-defined global solver order.
"""

import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CHILDREN_DIR = REPO_ROOT / "results" / "10x10" / "blind_probe_children"

FIXED_RULES = {
    3: ("memo", "desc", 1_000_000),
    4: ("memo", "asc", 10_000),
    5: ("maxdepth", "desc", 10_000),
}


def state_key(text: str) -> tuple[int, ...]:
    return tuple(sorted(int(x) for x in text.replace("-", ",").split(",") if x))


def safe_parent(parent: str) -> str:
    return parent.replace(",", "_")


def read_children(path: Path) -> list[tuple[int, ...]]:
    out = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(state_key(line))
    return out


def read_csv_states(path: Path) -> list[tuple[int, ...]]:
    with path.open(newline="") as f:
        return [state_key(r["state"]) for r in csv.DictReader(f)]


def fail(msg: str) -> None:
    raise SystemExit(f"ERROR: {msg}")


def validate_parent(parent: str) -> None:
    stones = len(state_key(parent))
    if stones not in FIXED_RULES:
        fail(f"unsupported parent size {stones}: {parent}")
    budget = FIXED_RULES[stones][2]
    safe = safe_parent(parent)

    batch_paths = list(CHILDREN_DIR.glob(f"children_{safe}_batch*.txt"))
    if not batch_paths:
        fail(f"no batch files for {parent}")

    indexed = []
    for path in batch_paths:
        try:
            idx = int(path.stem.rsplit("_batch", 1)[1])
        except (IndexError, ValueError):
            fail(f"cannot parse batch index: {path.name}")
        indexed.append((idx, path))
    indexed.sort(key=lambda x: x[0])

    indices = [i for i, _ in indexed]
    expected = list(range(indices[-1] + 1))
    if indices != expected:
        fail(f"non-consecutive/duplicate batches for {parent}: {indices}, expected {expected}")

    global_children: list[tuple[int, ...]] = []
    for idx, child_path in indexed:
        children = read_children(child_path)
        if not children:
            fail(f"empty child batch: {child_path.name}")
        if len(children) != len(set(children)):
            fail(f"duplicate child state inside {child_path.name}")

        exact_path = CHILDREN_DIR / f"exact_{safe}_batch{idx}.csv"
        probe_path = CHILDREN_DIR / f"probe_{safe}_batch{idx}_{budget}.csv"
        if not exact_path.exists():
            fail(f"missing exact file: {exact_path.name}")
        if not probe_path.exists():
            fail(f"missing probe file: {probe_path.name}")

        exact_states = read_csv_states(exact_path)
        probe_states = read_csv_states(probe_path)
        if len(exact_states) != len(set(exact_states)):
            fail(f"duplicate exact state in {exact_path.name}")
        if len(probe_states) != len(set(probe_states)):
            fail(f"duplicate probe state in {probe_path.name}")

        child_set = set(children)
        exact_set = set(exact_states)
        probe_set = set(probe_states)
        if exact_set != child_set:
            missing = sorted(child_set - exact_set)
            extra = sorted(exact_set - child_set)
            fail(
                f"exact set mismatch in batch {idx} for {parent}: "
                f"missing={len(missing)} extra={len(extra)}"
            )
        if probe_set != child_set:
            missing = sorted(child_set - probe_set)
            extra = sorted(probe_set - child_set)
            fail(
                f"probe set mismatch in batch {idx} for {parent}: "
                f"missing={len(missing)} extra={len(extra)}"
            )

        global_children.extend(children)

    if len(global_children) != len(set(global_children)):
        fail(f"child state appears in multiple batches for {parent}")

    unbatched = CHILDREN_DIR / f"children_{safe}.txt"
    if unbatched.exists():
        full = read_children(unbatched)
        if full != global_children:
            fail(
                f"batch concatenation does not exactly reproduce {unbatched.name}; "
                "global solver order is not verified"
            )

    print(
        f"OK {parent}: batches={len(indexed)} children={len(global_children)} "
        f"exact=complete probe=complete global_order=verified"
    )


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "usage: validate_full_blind_analysis_inputs.py parent [parent ...]\n"
            "example: python scripts/validate_full_blind_analysis_inputs.py 2,9,33 4,9,33"
        )
    for parent in sys.argv[1:]:
        validate_parent(parent)


if __name__ == "__main__":
    main()
