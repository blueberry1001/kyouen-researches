#!/usr/bin/env python3
"""Verify preregistered 10x10 below-root memo instrumentation outputs.

This script performs no solver work.  It checks two things before mechanism
metrics are interpreted:

1. semantic parity with the completed native V2 parent benchmark (strategy A);
2. arithmetic consistency of the frozen instrumentation counters.

Expected files
--------------
summary CSV, one row per parent:
  parent,outcome,exact_visited,exact_memo,root_unique,root_entered,
  root_first_lo,root_first_hi,root_witness

depth CSV, zero or more rows per parent/depth (normally only nonzero depths):
  parent,depth,
  entry_lookup_calls,entry_hit_win,entry_hit_loss,entry_miss,
  prefetch_calls,prefetch_hit_win,prefetch_hit_loss,prefetch_miss,
  put_win,put_loss,
  child_eval_from_cache_win,child_eval_from_cache_loss,child_eval_recursive,
  visited_nonterminal_nodes,nodes_with_any_prefetch_hit,
  nodes_cache_changes_first_child,nodes_cache_changes_full_order,
  actual_first_cached_loss,fallback_first_cached_loss,
  solved_win_nodes,win_return_from_cached_loss_child

The verifier deliberately does not use wall-clock or solver-seconds parity.
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "results" / "10x10" / "parent-benchmark" / "parent_benchmark_raw.csv"

SUMMARY_FIELDS = {
    "parent",
    "outcome",
    "exact_visited",
    "exact_memo",
    "root_unique",
    "root_entered",
    "root_first_lo",
    "root_first_hi",
    "root_witness",
}

COUNTERS = [
    "entry_lookup_calls",
    "entry_hit_win",
    "entry_hit_loss",
    "entry_miss",
    "prefetch_calls",
    "prefetch_hit_win",
    "prefetch_hit_loss",
    "prefetch_miss",
    "put_win",
    "put_loss",
    "child_eval_from_cache_win",
    "child_eval_from_cache_loss",
    "child_eval_recursive",
    "visited_nonterminal_nodes",
    "nodes_with_any_prefetch_hit",
    "nodes_cache_changes_first_child",
    "nodes_cache_changes_full_order",
    "actual_first_cached_loss",
    "fallback_first_cached_loss",
    "solved_win_nodes",
    "win_return_from_cached_loss_child",
]
DEPTH_FIELDS = {"parent", "depth", *COUNTERS}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit(f"empty CSV: {path}")
    return rows


def require_fields(rows: list[dict[str, str]], required: set[str], path: Path) -> None:
    have = set(rows[0])
    missing = sorted(required - have)
    if missing:
        raise SystemExit(f"{path}: missing columns: {missing}")


def as_int(row: dict[str, str], name: str) -> int:
    try:
        value = int(row[name])
    except (KeyError, ValueError) as exc:
        raise SystemExit(f"invalid integer {name}={row.get(name)!r} in {row}") from exc
    if value < 0:
        raise SystemExit(f"negative counter/value {name}={value} in {row}")
    return value


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("summary", type=Path)
    ap.add_argument("depth", type=Path)
    args = ap.parse_args()

    summary = read_csv(args.summary)
    depth = read_csv(args.depth)
    require_fields(summary, SUMMARY_FIELDS, args.summary)
    require_fields(depth, DEPTH_FIELDS, args.depth)

    # Frozen native baseline: only strategy A is relevant to the primary
    # instrumentation cohort.
    baseline_rows = read_csv(BASELINE)
    baseline = {
        r["parent"]: r for r in baseline_rows if r["strategy"].strip() == "A"
    }
    if len(baseline) != 12:
        raise SystemExit(f"expected 12 native baseline parents, got {len(baseline)}")

    inst = {}
    for r in summary:
        p = r["parent"]
        if p in inst:
            raise SystemExit(f"duplicate summary parent: {p}")
        inst[p] = r

    if set(inst) != set(baseline):
        raise SystemExit(
            "instrumented parent set differs from frozen 12-parent native cohort: "
            f"missing={sorted(set(baseline)-set(inst))} "
            f"extra={sorted(set(inst)-set(baseline))}"
        )

    # Exact semantic parity.  Existing baseline column names differ slightly
    # from the instrumented summary names, so map explicitly.
    parity_map = {
        "outcome": "outcome",
        "exact_visited": "exact_visited",
        "exact_memo": "exact_memo",
        "root_unique": "root_unique",
        "root_entered": "root_entered",
        "root_first_lo": "root_first_lo",
        "root_first_hi": "root_first_hi",
        "root_witness": "root_witness",
    }
    for p in sorted(baseline):
        b = baseline[p]
        r = inst[p]
        for out_name, base_name in parity_map.items():
            if r[out_name].strip() != b[base_name].strip():
                raise SystemExit(
                    f"SEMANTIC PARITY FAILURE parent={p} field={out_name}: "
                    f"instrumented={r[out_name]!r} baseline={b[base_name]!r}"
                )

    seen_depth = set()
    by_parent = defaultdict(lambda: defaultdict(int))
    for r in depth:
        p = r["parent"]
        if p not in baseline:
            raise SystemExit(f"depth CSV contains non-cohort parent: {p}")
        d = as_int(r, "depth")
        key = (p, d)
        if key in seen_depth:
            raise SystemExit(f"duplicate parent/depth row: {key}")
        seen_depth.add(key)

        c = {name: as_int(r, name) for name in COUNTERS}

        if c["entry_lookup_calls"] != (
            c["entry_hit_win"] + c["entry_hit_loss"] + c["entry_miss"]
        ):
            raise SystemExit(f"entry lookup identity failed at {key}")
        if c["prefetch_calls"] != (
            c["prefetch_hit_win"] + c["prefetch_hit_loss"] + c["prefetch_miss"]
        ):
            raise SystemExit(f"prefetch lookup identity failed at {key}")

        consumed = (
            c["child_eval_from_cache_win"]
            + c["child_eval_from_cache_loss"]
            + c["child_eval_recursive"]
        )
        if consumed > c["prefetch_calls"]:
            # Not every prefetched child is consumed because WIN nodes stop at
            # the first LOSS child; consumed can be smaller but never larger.
            raise SystemExit(f"consumed child evaluations exceed prefetches at {key}")

        if c["nodes_with_any_prefetch_hit"] > c["visited_nonterminal_nodes"]:
            raise SystemExit(f"prefetch-hit nodes exceed nonterminal nodes at {key}")
        if c["nodes_cache_changes_first_child"] > c["visited_nonterminal_nodes"]:
            raise SystemExit(f"first-child changes exceed nonterminal nodes at {key}")
        if c["nodes_cache_changes_full_order"] > c["visited_nonterminal_nodes"]:
            raise SystemExit(f"full-order changes exceed nonterminal nodes at {key}")
        if c["nodes_cache_changes_first_child"] > c["nodes_cache_changes_full_order"]:
            raise SystemExit(f"first-child changes exceed full-order changes at {key}")
        if c["actual_first_cached_loss"] > c["nodes_with_any_prefetch_hit"]:
            raise SystemExit(f"actual cached-loss-first exceeds hit nodes at {key}")
        if c["fallback_first_cached_loss"] > c["nodes_with_any_prefetch_hit"]:
            raise SystemExit(f"fallback cached-loss-first exceeds hit nodes at {key}")
        if c["win_return_from_cached_loss_child"] > c["solved_win_nodes"]:
            raise SystemExit(f"cached-loss WIN returns exceed solved WIN nodes at {key}")
        if c["win_return_from_cached_loss_child"] > c["child_eval_from_cache_loss"]:
            raise SystemExit(f"cached-loss WIN returns exceed cached LOSS evaluations at {key}")

        for name, value in c.items():
            by_parent[p][name] += value

    missing_depth = sorted(set(baseline) - set(by_parent))
    if missing_depth:
        raise SystemExit(f"parents with no depth counters: {missing_depth}")

    print("instrumentation verification: PASS")
    print("semantic_parity=12/12")
    print(f"depth_rows={len(depth)}")
    print("parent,entry_hit_rate,prefetch_hit_rate,cached_eval_fraction,first_order_change_rate,any_order_change_rate,cached_loss_win_shortcut_rate")
    for p in sorted(by_parent):
        c = by_parent[p]
        entry_hits = c["entry_hit_win"] + c["entry_hit_loss"]
        prefetch_hits = c["prefetch_hit_win"] + c["prefetch_hit_loss"]
        cached_evals = c["child_eval_from_cache_win"] + c["child_eval_from_cache_loss"]
        consumed = cached_evals + c["child_eval_recursive"]
        def rate(num: int, den: int) -> str:
            return "nan" if den == 0 else f"{num/den:.6f}"
        print(
            ",".join(
                [
                    p,
                    rate(entry_hits, c["entry_lookup_calls"]),
                    rate(prefetch_hits, c["prefetch_calls"]),
                    rate(cached_evals, consumed),
                    rate(c["nodes_cache_changes_first_child"], c["visited_nonterminal_nodes"]),
                    rate(c["nodes_cache_changes_full_order"], c["visited_nonterminal_nodes"]),
                    rate(c["win_return_from_cached_loss_child"], c["solved_win_nodes"]),
                ]
            )
        )


if __name__ == "__main__":
    main()
