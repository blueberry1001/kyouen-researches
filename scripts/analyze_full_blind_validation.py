#!/usr/bin/env python3
"""Strict full-child analysis for the 10x10 blind probe validation.

This entry point is deliberately separate from analyze_probe_blind_validation.py.
It refuses partial exact/probe data, preserves one global solver order across
batches, and uses that global order as the deterministic tie-break for the fixed
probe rule.

It reports first-LOSS positions only. Search-cost analysis is intentionally left
out because exact `visited` can depend on solver/memo execution details and is a
separate question from move-order quality.
"""

import csv
import json
import random
import statistics
import sys
from pathlib import Path

import analyze_probe_blind_validation as legacy
import validate_full_blind_analysis_inputs as guard

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "results" / "10x10"
RANDOM_ITERS = 10000
RANDOM_SEED = 20260907


def load_complete_parent(parent: str, stones: int):
    """Return complete children/probe/outcome maps in verified global order."""
    guard.validate_parent(parent)
    feature, direction, _budget = legacy.FIXED_RULES[stones]
    batches = legacy.collect_batches(parent, stones)
    batches.sort(key=lambda b: b["batch_index"])

    children = []
    probe = {}
    outcomes = {}
    seen = set()
    global_pos = 0
    for batch in batches:
        for _local_move, state in batch["order"]:
            if state in seen:
                raise RuntimeError(f"duplicate child across batches for {parent}: {state}")
            seen.add(state)
            global_pos += 1
            children.append((global_pos, state))
        probe.update(batch["probe_rows"])
        for state, row in batch["exact_rows"].items():
            outcome = row.get("outcome")
            if outcome not in {"WIN", "LOSS"}:
                raise RuntimeError(f"invalid exact outcome for {parent} {state}: {outcome!r}")
            outcomes[state] = outcome

    states = {state for _, state in children}
    if set(probe) != states:
        raise RuntimeError(f"probe set changed after validation for {parent}")
    if set(outcomes) != states:
        raise RuntimeError(f"exact set changed after validation for {parent}")

    def fixed_key(item):
        pos, state = item
        value = legacy.parse_float(probe[state].get(feature))
        if value is None:
            raise RuntimeError(f"missing/non-numeric {feature} for {parent} {state}")
        primary = -value if direction == "desc" else value
        return (primary, pos)

    fixed_order = sorted(children, key=fixed_key)
    return children, fixed_order, outcomes, feature, direction


def first_loss(order, outcomes):
    for i, (_pos, state) in enumerate(order, 1):
        if outcomes[state] == "LOSS":
            return i
    return len(order) + 1


def random_positions(children, outcomes, seed):
    rng = random.Random(seed)
    states = list(children)
    out = []
    for _ in range(RANDOM_ITERS):
        shuffled = states[:]
        rng.shuffle(shuffled)
        out.append(first_loss(shuffled, outcomes))
    return out


def main():
    exclude_lopo = "--exclude-lopo-source" in sys.argv
    selection_rows = legacy.load_selection()
    bad = [r["parent"] for r in selection_rows if str(r.get("selected_before_probe", "")).lower() != "true"]
    if bad:
        raise RuntimeError(f"parents not selected before probe: {bad}")
    if exclude_lopo:
        selection_rows = [r for r in selection_rows if str(r.get("lopo_source_used", "")).lower() != "true"]

    rows = []
    for info in selection_rows:
        parent = info["parent"]
        stones = int(info["stones"])
        if stones not in legacy.FIXED_RULES:
            continue
        children, fixed_order, outcomes, feature, direction = load_complete_parent(parent, stones)
        losses = sum(outcome == "LOSS" for outcome in outcomes.values())
        if losses == 0:
            # Keep no-LOSS parents in the raw output; exclude them only from first-LOSS comparisons.
            random_pos = []
            random_median = None
            random_expected = None
        else:
            random_pos = random_positions(children, outcomes, RANDOM_SEED + sum(ord(c) for c in parent))
            random_median = float(statistics.median(random_pos))
            random_expected = (len(children) + 1) / (losses + 1)

        row = {
            "parent": parent,
            "stones": stones,
            "child_count": len(children),
            "loss_child_count": losses,
            "feature": feature,
            "direction": direction,
            "fixed_first_loss_position": first_loss(fixed_order, outcomes),
            "solver_default_first_loss_position": first_loss(children, outcomes),
            "random_median_first_loss_position": random_median,
            "random_theoretical_expected_first_loss_position": random_expected,
        }
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False))

    out_csv = OUT_DIR / "blind-probe-full-rank-results.csv"
    out_json = OUT_DIR / "blind-probe-full-rank-analysis.json"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        with out_csv.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    comparable = [r for r in rows if r["loss_child_count"] > 0]
    summary = {
        "strict_full_child_only": True,
        "random_iterations": RANDOM_ITERS,
        "random_seed": RANDOM_SEED,
        "n_complete_parents": len(rows),
        "n_parents_with_loss": len(comparable),
        "by_stones": {},
    }
    for stones in sorted({r["stones"] for r in comparable}):
        group = [r for r in comparable if r["stones"] == stones]
        fixed = [r["fixed_first_loss_position"] for r in group]
        solver = [r["solver_default_first_loss_position"] for r in group]
        random_med = [r["random_median_first_loss_position"] for r in group]
        summary["by_stones"][str(stones)] = {
            "n": len(group),
            "fixed_median": float(statistics.median(fixed)),
            "solver_median": float(statistics.median(solver)),
            "random_median_of_parent_medians": float(statistics.median(random_med)),
            "fixed_better_than_solver": sum(a < b for a, b in zip(fixed, solver)),
            "fixed_worse_than_solver": sum(a > b for a, b in zip(fixed, solver)),
            "fixed_better_than_random_median": sum(a < b for a, b in zip(fixed, random_med)),
            "fixed_worse_than_random_median": sum(a > b for a, b in zip(fixed, random_med)),
        }

    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
