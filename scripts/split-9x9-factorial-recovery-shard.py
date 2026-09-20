#!/usr/bin/env python3
import argparse
import csv
import hashlib
from pathlib import Path


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(
        description=(
            "Deterministically bisect one factorial union shard by contiguous "
            "canonical-parent order for operational recovery."
        )
    )
    p.add_argument("input_csv")
    p.add_argument("output_dir")
    p.add_argument(
        "--level",
        type=int,
        default=1,
        help="recovery depth recorded in manifest; primary 64-parent shard is level 0",
    )
    args = p.parse_args()

    if args.level < 1:
        raise SystemExit("--level must be >= 1 for a recovery split")

    rows = read_csv(args.input_csv)
    if not rows:
        raise SystemExit("empty recovery shard input")
    required = {"canonical_parent", "pair_top", "union_top"}
    missing = required - set(rows[0])
    if missing:
        raise SystemExit(f"input missing columns: {sorted(missing)}")

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
        raise SystemExit("parents must be in canonical_parent order before recovery split")
    if len(parent_order) < 2:
        raise SystemExit("cannot bisect a shard with fewer than two parents")

    # Fixed rule: first floor(n/2) parents go left, remaining parents go right.
    # This depends only on the frozen input order, never on outcome, timing, or memo use.
    cut = len(parent_order) // 2
    groups = [parent_order[:cut], parent_order[cut:]]
    if not groups[0] or not groups[1]:
        raise SystemExit("internal empty recovery half")

    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    stem = Path(args.input_csv).stem
    manifest_rows = []

    for side, parents in zip(("a", "b"), groups):
        path = outdir / f"{stem}.r{args.level}{side}.csv"
        row_count = 0
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["canonical_parent", "pair_top", "union_top"])
            for parent in parents:
                for left, right in by_parent[parent]:
                    w.writerow([parent, left, right])
                    row_count += 1
        manifest_rows.append(
            {
                "level": args.level,
                "side": side,
                "path": str(path),
                "parent_count": len(parents),
                "input_rows": row_count,
                "solver_root_calls": 2 * row_count,
                "first_parent": parents[0],
                "last_parent": parents[-1],
                "sha256": sha256(path),
            }
        )

    manifest = outdir / f"{stem}.recovery-r{args.level}.manifest.csv"
    fields = [
        "level",
        "side",
        "path",
        "parent_count",
        "input_rows",
        "solver_root_calls",
        "first_parent",
        "last_parent",
        "sha256",
    ]
    with open(manifest, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(manifest_rows)

    original_keys = {
        (row["canonical_parent"], int(row["pair_top"]), int(row["union_top"]))
        for row in rows
    }
    recovered_keys = set()
    for rec in manifest_rows:
        for row in read_csv(rec["path"]):
            key = (row["canonical_parent"], int(row["pair_top"]), int(row["union_top"]))
            if key in recovered_keys:
                raise SystemExit(f"duplicate row across recovery halves: {key}")
            recovered_keys.add(key)
    if recovered_keys != original_keys:
        raise SystemExit("recovery halves do not exactly partition the original shard")

    print(f"input={args.input_csv}")
    print(f"input_sha256={sha256(args.input_csv)}")
    print(f"parents={len(parent_order)}")
    print(f"rows={len(rows)}")
    print(f"level={args.level}")
    print(f"left_parents={len(groups[0])}")
    print(f"right_parents={len(groups[1])}")
    print(f"manifest={manifest}")
    print("exact_partition=PASS")


if __name__ == "__main__":
    main()
