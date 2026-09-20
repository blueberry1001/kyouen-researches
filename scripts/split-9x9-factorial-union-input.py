#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    p = argparse.ArgumentParser(
        description=(
            "Split factorial union input into deterministic parent-preserving shards "
            "so each solver process starts with a fresh memo table."
        )
    )
    p.add_argument("union_input_csv")
    p.add_argument("output_dir")
    p.add_argument("--parents-per-shard", type=int, default=64)
    args = p.parse_args()

    if args.parents_per_shard <= 0:
        raise SystemExit("--parents-per-shard must be positive")

    rows = read_csv(args.union_input_csv)
    if not rows:
        raise SystemExit("empty union input CSV")
    required = {"canonical_parent", "pair_top", "union_top"}
    missing = required - set(rows[0])
    if missing:
        raise SystemExit(f"union input missing columns: {sorted(missing)}")

    by_parent = {}
    parent_order = []
    for i, row in enumerate(rows, start=2):
        parent = row["canonical_parent"]
        if parent not in by_parent:
            by_parent[parent] = []
            parent_order.append(parent)
        left = int(row["pair_top"])
        right = int(row["union_top"])
        if left == right:
            raise SystemExit(f"row {i} has identical moves for {parent}: {left}")
        by_parent[parent].append((left, right))

    if parent_order != sorted(parent_order):
        raise SystemExit(
            "union input parents are not in deterministic canonical_parent order; "
            "regenerate with prepare-9x9-factorial-union-input.py"
        )

    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    manifest_path = outdir / "manifest.csv"
    manifest_rows = []

    for shard_index, start in enumerate(
        range(0, len(parent_order), args.parents_per_shard)
    ):
        parents = parent_order[start : start + args.parents_per_shard]
        shard_path = outdir / f"union-{shard_index:04d}.csv"
        row_count = 0
        with open(shard_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["canonical_parent", "pair_top", "union_top"])
            for parent in parents:
                for left, right in by_parent[parent]:
                    w.writerow([parent, left, right])
                    row_count += 1
        manifest_rows.append(
            {
                "shard": shard_index,
                "path": str(shard_path),
                "parent_count": len(parents),
                "input_rows": row_count,
                "solver_root_calls": 2 * row_count,
                "first_parent": parents[0],
                "last_parent": parents[-1],
            }
        )

    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        fields = [
            "shard",
            "path",
            "parent_count",
            "input_rows",
            "solver_root_calls",
            "first_parent",
            "last_parent",
        ]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(manifest_rows)

    print(f"parents={len(parent_order)}")
    print(f"input_rows={len(rows)}")
    print(f"parents_per_shard={args.parents_per_shard}")
    print(f"shards={len(manifest_rows)}")
    print(f"manifest={manifest_path}")


if __name__ == "__main__":
    main()
