#!/usr/bin/env python3
"""Materialize frozen v2 child order into historical 20-row batch files.

Outcome-free: reads only the frozen child-order CSV and writes
children_<parent>_batch<N>.txt in the exact order already frozen.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
from collections import defaultdict
from pathlib import Path

BATCH_SIZE = 20


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("frozen_children_csv", type=Path)
    ap.add_argument("output_dir", type=Path)
    args = ap.parse_args()

    with args.frozen_children_csv.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit("empty frozen child CSV")

    required = {"parent", "solver_default_rank", "move", "child_state"}
    missing = required - set(rows[0])
    if missing:
        raise SystemExit(f"missing columns: {sorted(missing)}")
    forbidden = {"loss_child", "outcome", "memo", "visited", "maxdepth", "seconds", "probe"}
    leaked = forbidden & set(rows[0])
    if leaked:
        raise SystemExit(f"result-bearing columns forbidden: {sorted(leaked)}")

    by_parent: dict[str, list[dict[str, str]]] = defaultdict(list)
    parent_order: list[str] = []
    seen_parent = set()
    for row in rows:
        parent = row["parent"]
        if parent not in seen_parent:
            parent_order.append(parent)
            seen_parent.add(parent)
        by_parent[parent].append(row)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    total_batches = 0
    total_rows = 0

    for parent in parent_order:
        prs = by_parent[parent]
        expected_ranks = list(range(1, len(prs) + 1))
        got_ranks = [int(r["solver_default_rank"]) for r in prs]
        if got_ranks != expected_ranks:
            raise SystemExit(f"non-contiguous solver_default_rank for {parent}")
        states = [r["child_state"] for r in prs]
        if len(states) != len(set(states)):
            raise SystemExit(f"duplicate child state for {parent}")

        slug = parent.replace(",", "_")
        for batch_index, start in enumerate(range(0, len(states), BATCH_SIZE)):
            chunk = states[start:start + BATCH_SIZE]
            path = args.output_dir / f"children_{slug}_batch{batch_index}.txt"
            path.write_text("\n".join(chunk) + "\n", encoding="ascii", newline="\n")
            manifest.append({
                "parent": parent,
                "batch_index": batch_index,
                "rows": len(chunk),
                "first_solver_default_rank": start + 1,
                "last_solver_default_rank": start + len(chunk),
                "sha256": sha256(path),
                "path": path.name,
            })
            total_batches += 1
            total_rows += len(chunk)

    manifest_path = args.output_dir / "v2-batch-manifest.csv"
    fields = ["parent", "batch_index", "rows", "first_solver_default_rank", "last_solver_default_rank", "sha256", "path"]
    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(manifest)

    # Strong round-trip check: concatenating batches for each parent must exactly
    # reproduce the frozen child_state sequence.
    for parent in parent_order:
        slug = parent.replace(",", "_")
        got: list[str] = []
        i = 0
        while True:
            path = args.output_dir / f"children_{slug}_batch{i}.txt"
            if not path.exists():
                break
            got.extend(x for x in path.read_text(encoding="ascii").splitlines() if x)
            i += 1
        want = [r["child_state"] for r in by_parent[parent]]
        if got != want:
            raise SystemExit(f"round-trip child order mismatch for {parent}")

    print(f"parents={len(parent_order)}")
    print(f"batch_size={BATCH_SIZE}")
    print(f"batches={total_batches}")
    print(f"rows={total_rows}")
    print(f"manifest_sha256={sha256(manifest_path)}")
    print(f"manifest={manifest_path}")
    print("outcome_columns_read=0")
    print("round_trip_order=PASS")


if __name__ == "__main__":
    main()
