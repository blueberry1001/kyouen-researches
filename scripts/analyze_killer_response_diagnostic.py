#!/usr/bin/env python3
"""Analyze a completed killer-response manifest under the frozen preregistration.

This script does not solve positions.  It accepts only a manifest whose
exact_outcome column has already been filled with WIN/LOSS and emits the
predeclared per-parent quantities plus the confirmatory decision.  Keeping the
decision logic here prevents thresholds from drifting after outcomes are read.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

FRESH = {"2,9,33", "9,12,33", "9,23,33", "0,31,36", "0,36,44"}
CALIBRATION = {"4,9,33", "9,19,33"}
EXPECTED = FRESH | CALIBRATION


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("manifest", type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()

    by_parent: dict[str, list[dict[str, str]]] = defaultdict(list)
    with args.manifest.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit("empty manifest")

    required = {"cohort", "parent", "v_fixed", "fixed_child", "response",
                "response_state", "unique_gain", "move_rank",
                "gain_competition_rank", "gain_tier_rank", "exact_outcome"}
    if not required <= set(rows[0]):
        raise SystemExit(f"missing columns: {sorted(required - set(rows[0]))}")

    seen_states: set[tuple[str, str]] = set()
    for r in rows:
        parent = r["parent"]
        if parent not in EXPECTED:
            raise SystemExit(f"unexpected parent: {parent}")
        expected_cohort = "fresh" if parent in FRESH else "calibration"
        if r["cohort"] != expected_cohort:
            raise SystemExit(f"cohort mismatch for {parent}: {r['cohort']!r}")

        try:
            parent_ids = tuple(sorted(map(int, parent.split(","))))
            v_fixed = int(r["v_fixed"])
            fixed_child = tuple(sorted(map(int, r["fixed_child"].split(","))))
            response = int(r["response"])
            response_state = tuple(sorted(map(int, r["response_state"].split(","))))
            gain = int(r["unique_gain"])
            move_rank = int(r["move_rank"])
            comp_rank = int(r["gain_competition_rank"])
            tier_rank = int(r["gain_tier_rank"])
        except ValueError as e:
            raise SystemExit(f"invalid integer/state field for {parent}: {e}") from e

        if len(parent_ids) != 3 or len(set(parent_ids)) != 3:
            raise SystemExit(f"invalid parent state: {parent}")
        if not all(0 <= x < 100 for x in (*parent_ids, v_fixed, response)):
            raise SystemExit(f"out-of-board move/state for {parent}")
        if v_fixed in parent_ids or fixed_child != tuple(sorted((*parent_ids, v_fixed))):
            raise SystemExit(f"fixed-child reconstruction mismatch for {parent}")
        if response in fixed_child or response_state != tuple(sorted((*fixed_child, response))):
            raise SystemExit(f"response-state reconstruction mismatch for {parent} response {response}")
        if gain < 0 or move_rank < 1 or comp_rank < 1 or tier_rank < 1:
            raise SystemExit(f"invalid gain/rank for {parent} response {response}")

        outcome = r["exact_outcome"].strip().upper()
        if outcome not in {"WIN", "LOSS"}:
            raise SystemExit(f"unresolved/invalid exact_outcome for {parent} response {r['response']}: {r['exact_outcome']!r}")
        r["exact_outcome"] = outcome
        key = (parent, r["response"])
        if key in seen_states:
            raise SystemExit(f"duplicate response: {key}")
        seen_states.add(key)
        by_parent[parent].append(r)

    if set(by_parent) != EXPECTED:
        raise SystemExit(f"parent set mismatch: got={sorted(by_parent)}")

    summaries = []
    for parent in sorted(EXPECTED, key=lambda s: tuple(map(int, s.split(",")))):
        rs = by_parent[parent]
        # Reconstruct all response-side ranks from unique_gain rather than trusting
        # the manifest.  This catches row drift or hand-edits before outcomes can
        # influence the preregistered decision.
        ordered = sorted(rs, key=lambda r: (-int(r["unique_gain"]), int(r["response"])))
        distinct_gains = sorted({int(r["unique_gain"]) for r in rs}, reverse=True)
        tier_of = {g: i + 1 for i, g in enumerate(distinct_gains)}
        for expected_move_rank, r in enumerate(ordered, 1):
            gain = int(r["unique_gain"])
            expected_comp = 1 + sum(int(q["unique_gain"]) > gain for q in rs)
            expected_tier = tier_of[gain]
            got = (int(r["move_rank"]), int(r["gain_competition_rank"]), int(r["gain_tier_rank"]))
            want = (expected_move_rank, expected_comp, expected_tier)
            if got != want:
                raise SystemExit(
                    f"rank reconstruction mismatch for {parent} response {r['response']}: "
                    f"got={got} expected={want}"
                )

        fixed_values = {(r["v_fixed"], r["fixed_child"]) for r in rs}
        if len(fixed_values) != 1:
            raise SystemExit(f"inconsistent fixed child within parent: {parent}")

        killers = [r for r in rs if r["exact_outcome"] == "LOSS"]
        if not killers:
            raise SystemExit(f"AUDIT FAILURE: no exact killer for losing fixed child {parent}")

        best_move = min(int(r["move_rank"]) for r in killers)
        best_comp = min(int(r["gain_competition_rank"]) for r in killers)
        best_tier = min(int(r["gain_tier_rank"]) for r in killers)
        kg = [int(r["unique_gain"]) for r in killers]
        ng = [int(r["unique_gain"]) for r in rs if r["exact_outcome"] != "LOSS"]
        summaries.append({
            "cohort": "fresh" if parent in FRESH else "calibration",
            "parent": parent,
            "response_count": len(rs),
            "killer_count": len(killers),
            "killer_fraction": len(killers) / len(rs),
            "best_killer_move_rank": best_move,
            "best_killer_gain_competition_rank": best_comp,
            "best_killer_gain_tier_rank": best_tier,
            "top1_has_killer": best_move <= 1,
            "top3_has_killer": best_move <= 3,
            "top5_has_killer": best_move <= 5,
            "top1_gain_tier_has_killer": best_tier <= 1,
            "top3_gain_tiers_has_killer": best_tier <= 3,
            "top5_gain_tiers_has_killer": best_tier <= 5,
            "killer_gains": kg,
            "nonkiller_gains": ng,
        })

    fresh = [s for s in summaries if s["cohort"] == "fresh"]
    weak = sum(s["best_killer_gain_tier_rank"] > 5 for s in fresh)
    strong = sum(s["best_killer_gain_tier_rank"] <= 3 for s in fresh)
    if weak >= 2:
        decision = "POSITIVE_SIGNAL"
    elif strong == 5:
        decision = "STRONG_FALSIFICATION"
    else:
        decision = "INCONCLUSIVE"

    result = {
        "decision": decision,
        "fresh_positive_count_tier_gt_5": weak,
        "fresh_tier_le_3_count": strong,
        "fresh_best_killer_gain_tier_ranks": {
            s["parent"]: s["best_killer_gain_tier_rank"] for s in fresh
        },
        "parents": summaries,
    }
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
