#!/usr/bin/env python3
"""Select a fresh 3-stone v2 probe holdout without exposing child labels.

The source proof CSVs contain `loss_child`, but selection is deliberately based
only on source name, source row index and 3-stone parent state. Outcome and
loss_child fields are never read into the candidate records and never emitted.

Rows whose labels may have been exposed while designing this selector are
quarantined before hashing. This keeps the final selected parents unseen not
only by the selection algorithm but also by the analysis process that fixed it.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "results" / "10x10"

SEED = "kyouen-three-stone-isolated-probe-v2-holdout-2026-09-10"
SOURCES = (
    "two-stone-90-61-child-proof.csv",
    "two-stone-90-66-child-proof.csv",
)
DEFAULT_QUOTA = 6
# During holdout-design inspection, proof rows through source index 38 could
# have been visible. Exclude the same prefix from both sources conservatively.
MIN_UNEXPOSED_SOURCE_INDEX = 39


def key_for(source: str, index: int, parent: str) -> str:
    payload = f"{SEED}|{source}|{index}|{parent}".encode()
    return hashlib.sha256(payload).hexdigest()


def read_historical_parents(path: Path) -> set[str]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = csv.DictReader(f)
        return {r["parent"] for r in rows if r.get("stones") == "3"}


def label_sequestered_candidates(path: Path, source: str) -> list[dict[str, object]]:
    """Read only index/state; do not retain or branch on any label column."""
    out: list[dict[str, object]] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        try:
            index_col = header.index("index")
            state_col = header.index("state")
        except ValueError as e:
            raise SystemExit(f"{source}: missing index/state columns") from e

        for raw in reader:
            if not raw:
                continue
            index = int(raw[index_col])
            if index < MIN_UNEXPOSED_SOURCE_INDEX:
                continue
            parent = raw[state_col].strip()
            points = [int(x) for x in parent.split(",")]
            if len(points) != 3 or points != sorted(points) or len(set(points)) != 3:
                raise SystemExit(f"{source} index {index}: noncanonical parent {parent!r}")
            out.append(
                {
                    "source": source,
                    "source_index": index,
                    "parent": parent,
                    "selection_hash": key_for(source, index, parent),
                }
            )
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("output_csv", type=Path)
    ap.add_argument("--quota-per-source", type=int, default=DEFAULT_QUOTA)
    args = ap.parse_args()
    if args.quota_per_source <= 0:
        raise SystemExit("quota must be positive")

    historical_path = RESULTS / "blind-probe-parent-selection.csv"
    historical = read_historical_parents(historical_path)
    selected: list[dict[str, object]] = []
    used = set(historical)

    # Fixed source order; within each source use SHA-256 order. Global
    # de-duplication prevents the same parent appearing through both sources.
    eligible_counts: dict[str, int] = {}
    for source in SOURCES:
        candidates = label_sequestered_candidates(RESULTS / source, source)
        eligible = [r for r in candidates if r["parent"] not in used]
        eligible_counts[source] = len(eligible)
        eligible.sort(key=lambda r: (r["selection_hash"], r["source_index"], r["parent"]))
        take = eligible[: args.quota_per_source]
        if len(take) != args.quota_per_source:
            raise SystemExit(
                f"{source}: only {len(take)} eligible parents; need {args.quota_per_source}"
            )
        selected.extend(take)
        used.update(str(r["parent"]) for r in take)

    parents = [str(r["parent"]) for r in selected]
    if len(parents) != len(set(parents)):
        raise SystemExit("duplicate selected parent")
    overlap = set(parents) & historical
    if overlap:
        raise SystemExit(f"historical overlap: {sorted(overlap)}")
    if any(int(r["source_index"]) < MIN_UNEXPOSED_SOURCE_INDEX for r in selected):
        raise SystemExit("quarantined source row selected")

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["source", "source_index", "parent", "selection_hash"],
            lineterminator="\n",
        )
        w.writeheader()
        w.writerows(selected)

    digest = hashlib.sha256(args.output_csv.read_bytes()).hexdigest()
    print(f"seed={SEED}")
    print(f"quota_per_source={args.quota_per_source}")
    print(f"min_unexposed_source_index={MIN_UNEXPOSED_SOURCE_INDEX}")
    for source in SOURCES:
        print(f"eligible_{source}={eligible_counts[source]}")
    print(f"historical_3stone_parents={len(historical)}")
    print(f"selected={len(selected)}")
    print("historical_overlap=0")
    print("quarantined_rows_selected=0")
    print(f"selection_sha256={digest}")
    print(f"output={args.output_csv}")


if __name__ == "__main__":
    main()
