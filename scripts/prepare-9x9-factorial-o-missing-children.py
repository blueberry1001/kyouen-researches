#!/usr/bin/env python3
"""Prepare unique missing O-census child roots from the frozen reconstruction audit.

Reads results/9x9/factorial/o-full-census-reconstruction-audit.json and emits a
single-root solver input keyed by (canonical_parent, move). Does not change the
fixed missing sets (86 / 63) and does not select by outcome.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


COMP = {
    "O_at_E0": ("diff_O_at_E0", "top_T", "top_TO"),
    "O_at_E1": ("diff_O_at_E1", "top_TE", "top_raw"),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--audit",
        default="results/9x9/factorial/o-full-census-reconstruction-audit.json",
    )
    ap.add_argument("--holdout", default="artifacts/9x9-factorial-holdout.csv")
    ap.add_argument("--population", default="artifacts/9x9-factorial-population.csv")
    ap.add_argument(
        "--out",
        default="artifacts/solve/o-missing-unique-children.csv",
    )
    ap.add_argument(
        "--join-plan",
        default="artifacts/solve/o-missing-join-plan.json",
    )
    args = ap.parse_args()

    audit = json.loads(Path(args.audit).read_text(encoding="utf-8"))
    pop = {r["canonical_parent"]: r for r in csv.DictReader(open(args.population, newline="", encoding="utf-8"))}
    hold = {r["canonical_parent"]: r for r in csv.DictReader(open(args.holdout, newline="", encoding="utf-8"))}

    # unique child key -> list of (comparison, role)
    children: dict[tuple[str, int], list[dict]] = {}
    join_plan = {"comparisons": {}, "unique_children": 0}

    for label, meta in audit["comparisons"].items():
        left_col, right_col = COMP[label][1], COMP[label][2]
        parents = [m["canonical_parent"] for m in meta["missing_states"]]
        join_plan["comparisons"][label] = {
            "missing_parents": len(parents),
            "parents": parents,
        }
        for m in meta["missing_states"]:
            parent = m["canonical_parent"]
            # Prefer audit moves; verify against holdout/population tops.
            src = hold.get(parent) or pop[parent]
            left = int(src[left_col])
            right = int(src[right_col])
            if int(m["left_move"]) != left or int(m["right_move"]) != right:
                raise SystemExit(
                    f"{label} {parent}: audit moves {m['left_move']}/{m['right_move']} "
                    f"!= tops {left}/{right}"
                )
            children.setdefault((parent, left), []).append(
                {"comparison": label, "role": "left"}
            )
            children.setdefault((parent, right), []).append(
                {"comparison": label, "role": "right"}
            )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    keys = sorted(children.keys())
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["canonical_parent", "move"])
        for parent, move in keys:
            w.writerow([parent, move])

    join_plan["unique_children"] = len(keys)
    join_plan["child_keys"] = [
        {"canonical_parent": p, "move": m, "uses": children[(p, m)]}
        for p, m in keys
    ]
    Path(args.join_plan).write_text(
        json.dumps(join_plan, indent=2) + "\n", encoding="utf-8"
    )
    print(f"O_at_E0_missing={join_plan['comparisons']['O_at_E0']['missing_parents']}")
    print(f"O_at_E1_missing={join_plan['comparisons']['O_at_E1']['missing_parents']}")
    print(f"unique_children={len(keys)}")
    print(f"wrote {out_path}")
    print(f"wrote {args.join_plan}")


if __name__ == "__main__":
    main()
