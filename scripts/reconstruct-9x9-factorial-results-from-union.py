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


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def normalize_outcome(value, context):
    outcome = str(value).strip().upper()
    if outcome not in {"WIN", "LOSS"}:
        raise SystemExit(f"bad outcome {value!r} at {context}")
    return outcome


def add_observation(outcomes, parent, move, outcome, context):
    key = (parent, int(move))
    previous = outcomes.get(key)
    if previous is not None and previous != outcome:
        raise SystemExit(
            f"inconsistent repeated outcome for {parent} move {move}: "
            f"{previous} vs {outcome} at {context}"
        )
    outcomes[key] = outcome


def main():
    p = argparse.ArgumentParser(
        description=(
            "Reconstruct the four preregistered factorial solver-result CSVs "
            "from one or more union runs of kyouen-solver-9-compare."
        )
    )
    p.add_argument("holdout_csv")
    p.add_argument(
        "union_result_csv",
        nargs="+",
        help="one or more union solver output CSVs; sharded runs may be passed together",
    )
    p.add_argument("output_dir")
    args = p.parse_args()

    holdout = read_csv(args.holdout_csv)
    if not holdout:
        raise SystemExit("empty holdout CSV")
    by_parent = {r["canonical_parent"]: r for r in holdout}
    if len(by_parent) != len(holdout):
        raise SystemExit("duplicate canonical_parent in holdout CSV")

    required_holdout = {"canonical_parent"}
    for member, left, right in COMPARISONS.values():
        required_holdout.update((member, left, right))
    missing = required_holdout - set(holdout[0])
    if missing:
        raise SystemExit(f"holdout CSV missing columns: {sorted(missing)}")

    expected_keys = set()
    selected_parents = set()
    for parent, row in by_parent.items():
        for label, (member, left, right) in COMPARISONS.items():
            if not truthy(row[member]):
                continue
            l = int(row[left])
            r = int(row[right])
            if l == r:
                raise SystemExit(f"{label}: identical selected moves for {parent}: {l}")
            selected_parents.add(parent)
            expected_keys.add((parent, l))
            expected_keys.add((parent, r))

    outcomes = {}
    actual_parents = set()
    total_union_rows = 0
    for result_path in args.union_result_csv:
        union_rows = read_csv(result_path)
        if not union_rows:
            raise SystemExit(f"empty union solver result CSV: {result_path}")
        required_union = {
            "canonical_parent",
            "pair_top",
            "union_top",
            "pair_child_outcome",
            "other_child_outcome",
        }
        missing = required_union - set(union_rows[0])
        if missing:
            raise SystemExit(
                f"union solver result {result_path} missing columns: {sorted(missing)}"
            )

        total_union_rows += len(union_rows)
        for i, row in enumerate(union_rows, start=2):
            context_prefix = f"{result_path}:row {i}"
            parent = row["canonical_parent"]
            if parent not in by_parent:
                raise SystemExit(f"{context_prefix}: unknown parent {parent}")
            actual_parents.add(parent)
            left_move = int(row["pair_top"])
            right_move = int(row["union_top"])
            if left_move == right_move:
                raise SystemExit(
                    f"{context_prefix}: identical moves for {parent}: {left_move}"
                )
            add_observation(
                outcomes,
                parent,
                left_move,
                normalize_outcome(
                    row["pair_child_outcome"], f"{context_prefix} pair child"
                ),
                f"{context_prefix} pair child",
            )
            add_observation(
                outcomes,
                parent,
                right_move,
                normalize_outcome(
                    row["other_child_outcome"], f"{context_prefix} union child"
                ),
                f"{context_prefix} union child",
            )

    actual_keys = set(outcomes)
    if actual_keys != expected_keys:
        missing_keys = sorted(expected_keys - actual_keys)[:10]
        extra_keys = sorted(actual_keys - expected_keys)[:10]
        raise SystemExit(
            "union result child-key mismatch: "
            f"missing={len(expected_keys-actual_keys)} {missing_keys}; "
            f"extra={len(actual_keys-expected_keys)} {extra_keys}"
        )
    if actual_parents != selected_parents:
        raise SystemExit(
            "union result parent-set mismatch: "
            f"missing={sorted(selected_parents-actual_parents)[:10]} "
            f"extra={sorted(actual_parents-selected_parents)[:10]}"
        )

    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    for label, (member, left_col, right_col) in COMPARISONS.items():
        selected = [r for r in holdout if truthy(r[member])]
        selected.sort(key=lambda r: r["canonical_parent"])
        path = outdir / f"{label}.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    "canonical_parent",
                    "pair_top",
                    "added_top",
                    "pair_child_outcome",
                    "added_child_outcome",
                ]
            )
            for row in selected:
                parent = row["canonical_parent"]
                left = int(row[left_col])
                right = int(row[right_col])
                w.writerow(
                    [
                        parent,
                        left,
                        right,
                        outcomes[(parent, left)],
                        outcomes[(parent, right)],
                    ]
                )
        print(f"{label}: rows={len(selected)} output={path}")

    repeated_observations = 2 * total_union_rows - len(actual_keys)
    print(f"selected_parents={len(selected_parents)}")
    print(f"unique_child_outcomes={len(actual_keys)}")
    print(f"union_result_files={len(args.union_result_csv)}")
    print(f"union_rows={total_union_rows}")
    print(f"consistent_repeated_observations={repeated_observations}")


if __name__ == "__main__":
    main()
