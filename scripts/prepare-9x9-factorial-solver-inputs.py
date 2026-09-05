#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path

COMPARISONS = {
    "E_at_O0": ("sample_E_at_O0", "top_T", "top_TE"),
    "O_at_E0": ("census_O_at_E0", "top_T", "top_TO"),
    "E_at_O1": ("sample_E_at_O1", "top_TO", "top_raw"),
    "O_at_E1": ("census_O_at_E1", "top_TE", "top_raw"),
}


def truthy(value):
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("holdout_csv")
    p.add_argument("output_dir")
    args = p.parse_args()

    with open(args.holdout_csv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit("empty holdout CSV")

    required = {"canonical_parent"}
    for member, left, right in COMPARISONS.values():
        required.update((member, left, right))
    missing = required - set(rows[0])
    if missing:
        raise SystemExit(f"holdout CSV missing columns: {sorted(missing)}")

    parents = [r["canonical_parent"] for r in rows]
    if len(set(parents)) != len(parents):
        raise SystemExit("duplicate canonical_parent in holdout CSV")

    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    for label, (member, left, right) in COMPARISONS.items():
        selected = [r for r in rows if truthy(r[member])]
        selected.sort(key=lambda r: r["canonical_parent"])
        path = outdir / f"{label}.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            # kyouen_solver_9_compare requires the second column to be named pair_top.
            # In this factorial use it means the component-absent baseline move.
            w.writerow(["canonical_parent", "pair_top", "added_top"])
            for r in selected:
                l = int(r[left])
                rr = int(r[right])
                if l == rr:
                    raise SystemExit(
                        f"{label}: selected parent has identical moves: "
                        f"{r['canonical_parent']} -> {l}"
                    )
                w.writerow([r["canonical_parent"], l, rr])
        print(f"{label}: rows={len(selected)} output={path}")


if __name__ == "__main__":
    main()
