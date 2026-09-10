#!/usr/bin/env python3
"""Validate and score the preregistered depth-5 observed-prefix child trace.

This script deliberately uses only columns available before recursion for ranking.
Post-recursion outcome/visited_delta/cutoff are labels used only for evaluation.
The fixed final holdout root is 13-52-57; it must not be used to choose a rule.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

REQUIRED = {
    "root_state",
    "node_id",
    "parent_lo",
    "parent_hi",
    "order_index",
    "child_count",
    "child_lo",
    "child_hi",
    "outcome",
    "visited_delta",
    "cutoff",
}

FIXED_HOLDOUT = "13-52-57"


def as_int(row: dict[str, str], key: str) -> int:
    try:
        return int(row[key], 0)
    except Exception as exc:
        raise ValueError(f"bad integer {key}={row.get(key)!r}") from exc


def key128(row: dict[str, str]) -> int:
    return (as_int(row, "child_hi") << 64) | as_int(row, "child_lo")


def candidate_key(name: str, row: dict[str, str]) -> tuple[int, int]:
    count = as_int(row, "child_count")
    key = key128(row)
    if name == "min_count_key_asc":
        return (count, key)
    if name == "min_count_key_desc":
        return (count, -key)
    if name == "max_count_key_asc":
        return (-count, key)
    if name == "max_count_key_desc":
        return (-count, -key)
    raise KeyError(name)


CANDIDATES = (
    "min_count_key_asc",   # frozen baseline
    "min_count_key_desc",  # tie-break-only intervention
    "max_count_key_asc",   # tests the direction of child.count
    "max_count_key_desc",
)


def load(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = set(reader.fieldnames or ())
        missing = sorted(REQUIRED - fields)
        if missing:
            raise ValueError(f"missing columns: {', '.join(missing)}")
        rows = list(reader)
    if not rows:
        raise ValueError("empty trace")
    return rows


def validate(rows: list[dict[str, str]]) -> dict[tuple[str, str], list[dict[str, str]]]:
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[(row["root_state"], row["node_id"])].append(row)

    for ident, group in groups.items():
        group.sort(key=lambda r: as_int(r, "order_index"))
        order = [as_int(r, "order_index") for r in group]
        if any(b <= a for a, b in zip(order, order[1:])):
            raise ValueError(f"{ident}: order_index is not strictly increasing")
        if len({(r["parent_lo"], r["parent_hi"]) for r in group}) != 1:
            raise ValueError(f"{ident}: parent bits change inside node")

        # The observed-prefix analysis assumes that the trace was produced by
        # the frozen native depth-5 baseline: child_count ascending, then
        # canonical key ascending.  Verify that assumption from pre-recursion
        # columns before using post-recursion labels.  Without this check, an
        # instrumentation/order mismatch could masquerade as a successful
        # repair rule.
        baseline_keys = [candidate_key("min_count_key_asc", row) for row in group]
        if any(b < a for a, b in zip(baseline_keys, baseline_keys[1:])):
            raise ValueError(
                f"{ident}: trace order disagrees with frozen min_count_key_asc baseline"
            )

        for row in group:
            if as_int(row, "visited_delta") < 1:
                raise ValueError(f"{ident}: visited_delta < 1 at order {row['order_index']}")
            if row["outcome"] not in {"WIN", "LOSS"}:
                raise ValueError(f"{ident}: invalid outcome {row['outcome']!r}")
            if as_int(row, "cutoff") not in {0, 1}:
                raise ValueError(f"{ident}: cutoff must be 0/1")

        losses = [i for i, r in enumerate(group) if r["outcome"] == "LOSS"]
        cutoffs = [i for i, r in enumerate(group) if as_int(r, "cutoff") == 1]
        if losses or cutoffs:
            if len(losses) != 1 or len(cutoffs) != 1 or losses[0] != cutoffs[0]:
                raise ValueError(f"{ident}: completed WIN node must have one LOSS cutoff row")
            if losses[0] != len(group) - 1:
                raise ValueError(f"{ident}: rows appear after cutoff LOSS")
            if any(r["outcome"] != "WIN" for r in group[:-1]):
                raise ValueError(f"{ident}: non-cutoff entered child is not WIN")
        else:
            # A traced LOSS node may have only WIN children and no cutoff.
            if any(r["outcome"] != "WIN" for r in group):
                raise ValueError(f"{ident}: no-cutoff node contains non-WIN child")
    return groups


def score_group(group: list[dict[str, str]], candidate: str) -> tuple[int, int] | None:
    if not group or group[-1]["outcome"] != "LOSS" or as_int(group[-1], "cutoff") != 1:
        return None
    loss = group[-1]
    lk = candidate_key(candidate, loss)
    repaired = sum(lk < candidate_key(candidate, win) for win in group[:-1])
    return repaired, len(group) - 1


def summarize(groups: dict[tuple[str, str], list[dict[str, str]]]) -> dict:
    by_root: dict[str, dict[str, dict[str, int | float]]] = defaultdict(dict)
    for root in sorted({root for root, _ in groups}):
        root_groups = [g for (r, _), g in groups.items() if r == root]
        for candidate in CANDIDATES:
            repaired = total = nodes = 0
            for group in root_groups:
                x = score_group(group, candidate)
                if x is None:
                    continue
                a, b = x
                repaired += a
                total += b
                nodes += 1
            by_root[root][candidate] = {
                "win_nodes": nodes,
                "repaired_pairs": repaired,
                "eligible_pairs": total,
                "repair_rate": (repaired / total if total else 0.0),
            }

    roots = sorted(by_root)
    train_roots = [r for r in roots if r != FIXED_HOLDOUT]
    train = {}
    for candidate in CANDIDATES:
        repaired = sum(int(by_root[r][candidate]["repaired_pairs"]) for r in train_roots)
        total = sum(int(by_root[r][candidate]["eligible_pairs"]) for r in train_roots)
        train[candidate] = {
            "repaired_pairs": repaired,
            "eligible_pairs": total,
            "repair_rate": (repaired / total if total else 0.0),
        }

    # Candidate selection is fixed: maximize training pairwise repair rate,
    # then prefer the least invasive rule in this preregistered order.
    selected = max(CANDIDATES, key=lambda c: (train[c]["repair_rate"], -CANDIDATES.index(c)))
    return {
        "fixed_holdout_root": FIXED_HOLDOUT,
        "roots_present": roots,
        "training_roots": train_roots,
        "candidate_order": list(CANDIDATES),
        "selection_rule": "max training repair_rate; ties by candidate_order",
        "per_root": by_root,
        "training": train,
        "selected_candidate": selected,
        "holdout": by_root.get(FIXED_HOLDOUT, {}).get(selected),
        "warning": None if FIXED_HOLDOUT in by_root else "fixed holdout root absent; do not substitute another root",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("trace_csv", type=Path)
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()
    rows = load(args.trace_csv)
    groups = validate(rows)
    result = summarize(groups)
    text = json.dumps(result, indent=2, sort_keys=True)
    print(text)
    if args.json_out:
        args.json_out.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
