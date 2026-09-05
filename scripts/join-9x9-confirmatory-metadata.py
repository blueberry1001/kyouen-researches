#!/usr/bin/env python3
import argparse
import csv


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("results_csv")
    p.add_argument("meta_csv")
    p.add_argument("output_csv")
    args = p.parse_args()

    results = read_rows(args.results_csv)
    meta = read_rows(args.meta_csv)
    if not results or not meta:
        raise SystemExit("empty CSV")

    by_parent = {r["canonical_parent"]: r for r in meta}
    if len(by_parent) != len(meta):
        raise SystemExit("duplicate canonical_parent in metadata")

    merged = []
    for result in results:
        parent = result["canonical_parent"]
        if parent not in by_parent:
            raise SystemExit(f"metadata missing parent: {parent}")
        row = dict(by_parent[parent])
        row.update(result)
        merged.append(row)

    fields = list(meta[0].keys())
    for field in results[0].keys():
        if field not in fields:
            fields.append(field)

    with open(args.output_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(merged)

    print(f"rows={len(merged)}")
    print(f"output={args.output_csv}")


if __name__ == "__main__":
    main()
