#!/usr/bin/env python3
import argparse
import csv
import hashlib
from pathlib import Path

DEFAULT_SEED = "kyouen-9x9-pair-components-factorial-v1-2026-09-05"
DEFAULT_E_TARGET = 1024

MEMBERSHIP = {
    "E0": "diff_E_at_O0",
    "O0": "diff_O_at_E0",
    "E1": "diff_E_at_O1",
    "O1": "diff_O_at_E1",
}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("population_csv")
    p.add_argument("output_csv")
    p.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="CSV containing canonical_parent; may be repeated",
    )
    p.add_argument("--e-target", type=int, default=DEFAULT_E_TARGET)
    p.add_argument("--seed", default=DEFAULT_SEED)
    return p.parse_args()


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def digest(seed, label, parent):
    payload = seed + "\0" + label + "\0" + parent
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def truthy(value):
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def main():
    args = parse_args()
    if args.e_target < 0:
        raise SystemExit("--e-target must be nonnegative")

    population = read_rows(args.population_csv)
    if not population:
        raise SystemExit("empty population CSV")

    required = {
        "canonical_parent",
        "top_T",
        "top_TE",
        "top_TO",
        "top_raw",
        "diff_E_at_O0",
        "diff_O_at_E0",
        "diff_E_at_O1",
        "diff_O_at_E1",
    }
    missing = required - set(population[0])
    if missing:
        raise SystemExit(f"population CSV missing columns: {sorted(missing)}")

    excluded = set()
    for path in args.exclude:
        rows = read_rows(path)
        if rows and "canonical_parent" not in rows[0]:
            raise SystemExit(f"exclude CSV lacks canonical_parent: {path}")
        excluded.update(r["canonical_parent"] for r in rows)

    eligible = [r for r in population if r["canonical_parent"] not in excluded]
    by_parent = {r["canonical_parent"]: r for r in eligible}
    if len(by_parent) != len(eligible):
        raise SystemExit("duplicate canonical_parent in population")

    members = {
        label: [r for r in eligible if truthy(r[column])]
        for label, column in MEMBERSHIP.items()
    }

    # E effects have large populations. Take independent deterministic hash samples
    # for E|O=0 and E|O=1 so their analysis sets are not changed by the O census.
    selected_e = {}
    for label in ("E0", "E1"):
        ordered = sorted(
            members[label],
            key=lambda r: (
                digest(args.seed, label, r["canonical_parent"]),
                r["canonical_parent"],
            ),
        )
        selected_e[label] = {
            r["canonical_parent"]
            for r in ordered[: min(args.e_target, len(ordered))]
        }

    # O effects have much smaller populations, so use a census after exclusions.
    selected_o = {
        "O0": {r["canonical_parent"] for r in members["O0"]},
        "O1": {r["canonical_parent"] for r in members["O1"]},
    }

    solve_parents = (
        selected_e["E0"]
        | selected_e["E1"]
        | selected_o["O0"]
        | selected_o["O1"]
    )

    output_rows = []
    for parent in solve_parents:
        row = dict(by_parent[parent])
        row["sample_E_at_O0"] = int(parent in selected_e["E0"])
        row["census_O_at_E0"] = int(parent in selected_o["O0"])
        row["sample_E_at_O1"] = int(parent in selected_e["E1"])
        row["census_O_at_E1"] = int(parent in selected_o["O1"])
        output_rows.append(row)

    output_rows.sort(
        key=lambda r: (
            digest(args.seed, "solve", r["canonical_parent"]),
            r["canonical_parent"],
        )
    )

    output_fields = list(population[0].keys()) + [
        "sample_E_at_O0",
        "census_O_at_E0",
        "sample_E_at_O1",
        "census_O_at_E1",
    ]
    with open(args.output_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=output_fields)
        w.writeheader()
        w.writerows(output_rows)

    manifest_path = str(Path(args.output_csv).with_suffix("")) + ".manifest.csv"
    manifest = [
        {
            "comparison": "E_at_O0",
            "design": f"hash_sample_{args.e_target}",
            "eligible": len(members["E0"]),
            "selected": len(selected_e["E0"]),
        },
        {
            "comparison": "O_at_E0",
            "design": "census",
            "eligible": len(members["O0"]),
            "selected": len(selected_o["O0"]),
        },
        {
            "comparison": "E_at_O1",
            "design": f"hash_sample_{args.e_target}",
            "eligible": len(members["E1"]),
            "selected": len(selected_e["E1"]),
        },
        {
            "comparison": "O_at_E1",
            "design": "census",
            "eligible": len(members["O1"]),
            "selected": len(selected_o["O1"]),
        },
    ]
    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f, fieldnames=["comparison", "design", "eligible", "selected"]
        )
        w.writeheader()
        w.writerows(manifest)

    print(f"seed={args.seed}")
    print(
        f"population={len(population)} excluded_unique={len(excluded)} "
        f"eligible={len(eligible)}"
    )
    print(
        f"E_at_O0 eligible={len(members['E0'])} "
        f"selected={len(selected_e['E0'])}"
    )
    print(
        f"O_at_E0 eligible={len(members['O0'])} "
        f"selected={len(selected_o['O0'])} census=1"
    )
    print(
        f"E_at_O1 eligible={len(members['E1'])} "
        f"selected={len(selected_e['E1'])}"
    )
    print(
        f"O_at_E1 eligible={len(members['O1'])} "
        f"selected={len(selected_o['O1'])} census=1"
    )
    print(f"unique_parents_to_solve={len(output_rows)}")
    print(f"output={Path(args.output_csv)}")
    print(f"manifest={Path(manifest_path)}")


if __name__ == "__main__":
    main()
