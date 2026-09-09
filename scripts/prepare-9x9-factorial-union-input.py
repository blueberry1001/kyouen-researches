#!/usr/bin/env python3
import argparse
import csv

COMPARISONS = {
    "E_at_O0": ("sample_E_at_O0", "top_T", "top_TE"),
    "O_at_E0": ("census_O_at_E0", "top_T", "top_TO"),
    "E_at_O1": ("sample_E_at_O1", "top_TO", "top_raw"),
    "O_at_E1": ("census_O_at_E1", "top_TE", "top_raw"),
}
MOVE_COLUMNS = ("top_T", "top_TE", "top_TO", "top_raw")


def truthy(value):
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ordered_required_moves(row):
    needed = set()
    memberships = 0
    for label, (member, left, right) in COMPARISONS.items():
        if not truthy(row[member]):
            continue
        memberships += 1
        l = int(row[left])
        r = int(row[right])
        if l == r:
            raise SystemExit(
                f"{label}: selected parent has identical moves: "
                f"{row['canonical_parent']} -> {l}"
            )
        needed.add(l)
        needed.add(r)

    ordered = []
    for col in MOVE_COLUMNS:
        move = int(row[col])
        if move in needed and move not in ordered:
            ordered.append(move)
    if set(ordered) != needed:
        raise SystemExit(
            f"internal move ordering mismatch for {row['canonical_parent']}: "
            f"needed={sorted(needed)} ordered={ordered}"
        )
    return ordered, memberships


def pair_moves(moves):
    if not moves:
        return []
    if len(moves) < 2:
        raise SystemExit(f"selected parent requires fewer than two distinct moves: {moves}")
    pairs = []
    i = 0
    while i + 1 < len(moves):
        pairs.append((moves[i], moves[i + 1]))
        i += 2
    if i < len(moves):
        # Existing compare solver always solves two roots per input row.  For an
        # odd number of required moves, pair the final new move with the first
        # already-covered move.  The repeated root should be an immediate memo
        # hit in the same process; reconstruction later checks outcome identity.
        pairs.append((moves[0], moves[i]))
    return pairs


def main():
    p = argparse.ArgumentParser(
        description=(
            "Prepare one union input for kyouen-solver-9-compare so factorial "
            "comparisons share child solves within each parent."
        )
    )
    p.add_argument("holdout_csv")
    p.add_argument("output_csv")
    args = p.parse_args()

    rows = read_csv(args.holdout_csv)
    if not rows:
        raise SystemExit("empty holdout CSV")

    required = {"canonical_parent", *MOVE_COLUMNS}
    for member, left, right in COMPARISONS.values():
        required.update((member, left, right))
    missing = required - set(rows[0])
    if missing:
        raise SystemExit(f"holdout CSV missing columns: {sorted(missing)}")

    parents = [r["canonical_parent"] for r in rows]
    if len(set(parents)) != len(parents):
        raise SystemExit("duplicate canonical_parent in holdout CSV")

    output_rows = []
    selected_parents = 0
    memberships = 0
    unique_children = 0

    for row in sorted(rows, key=lambda r: r["canonical_parent"]):
        moves, parent_memberships = ordered_required_moves(row)
        if not parent_memberships:
            continue
        selected_parents += 1
        memberships += parent_memberships
        unique_children += len(moves)
        for left, right in pair_moves(moves):
            if left == right:
                raise SystemExit(
                    f"union pair unexpectedly identical for {row['canonical_parent']}: {left}"
                )
            output_rows.append((row["canonical_parent"], left, right))

    if not output_rows:
        raise SystemExit("no selected factorial parents")

    with open(args.output_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        # The existing solver accepts any third-column name and echoes it.
        w.writerow(["canonical_parent", "pair_top", "union_top"])
        for parent, left, right in output_rows:
            w.writerow([parent, left, right])

    solver_root_calls = 2 * len(output_rows)
    naive_root_calls = 2 * memberships
    repeated_root_calls = solver_root_calls - unique_children
    saved_calls = naive_root_calls - solver_root_calls
    print(f"selected_parents={selected_parents}")
    print(f"comparison_memberships={memberships}")
    print(f"naive_root_calls={naive_root_calls}")
    print(f"unique_required_children={unique_children}")
    print(f"union_input_rows={len(output_rows)}")
    print(f"union_solver_root_calls={solver_root_calls}")
    print(f"intentional_repeated_root_calls={repeated_root_calls}")
    print(f"root_calls_saved_vs_four_inputs={saved_calls}")
    print(f"output={args.output_csv}")


if __name__ == "__main__":
    main()
