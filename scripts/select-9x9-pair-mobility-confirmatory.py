#!/usr/bin/env python3
import argparse
import csv
import hashlib
from collections import defaultdict
from pathlib import Path

DEFAULT_SEED = "kyouen-9x9-pair-vs-true-mobility-confirmatory-v1-2026-09-05"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("population_csv")
    p.add_argument("pilot_csv")
    p.add_argument("output_csv")
    p.add_argument("--total", type=int, default=1024)
    p.add_argument("--seed", default=DEFAULT_SEED)
    return p.parse_args()


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def largest_remainder(sizes, total):
    n = sum(sizes.values())
    if total > n:
        raise ValueError(f"requested {total} rows but only {n} are available")
    exact = {k: total * v / n for k, v in sizes.items()}
    alloc = {k: int(exact[k]) for k in sizes}
    left = total - sum(alloc.values())
    order = sorted(sizes, key=lambda k: (-(exact[k] - alloc[k]), k))
    for k in order[:left]:
        alloc[k] += 1
    return alloc


def digest(seed, parent):
    return hashlib.sha256((seed + "\0" + parent).encode("utf-8")).hexdigest()


def main():
    args = parse_args()
    population = read_rows(args.population_csv)
    pilot = {r["canonical_parent"] for r in read_rows(args.pilot_csv)}

    required = {"canonical_parent", "pair_top", "true_unique_top", "cause_class"}
    if not population:
        raise SystemExit("empty population CSV")
    missing = required - set(population[0])
    if missing:
        raise SystemExit(f"population CSV missing columns: {sorted(missing)}")

    eligible = [r for r in population if r["canonical_parent"] not in pilot]
    groups = defaultdict(list)
    for row in eligible:
        groups[row["cause_class"]].append(row)

    sizes = {k: len(v) for k, v in groups.items()}
    alloc = largest_remainder(sizes, args.total)

    selected = []
    for cls, rows in groups.items():
        rows.sort(key=lambda r: (digest(args.seed, r["canonical_parent"]), r["canonical_parent"]))
        selected.extend(rows[:alloc[cls]])

    selected.sort(key=lambda r: (r["cause_class"], digest(args.seed, r["canonical_parent"])))
    fields = list(population[0].keys())
    with open(args.output_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(selected)

    print(f"seed={args.seed}")
    print(f"population={len(population)} pilot_excluded={len(population)-len(eligible)} eligible={len(eligible)} sample={len(selected)}")
    for cls in sorted(sizes):
        print(f"{cls}: eligible={sizes[cls]} selected={alloc[cls]}")
    print(f"output={Path(args.output_csv)}")


if __name__ == "__main__":
    main()
