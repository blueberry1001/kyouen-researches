#!/usr/bin/env python3
"""Verify preregistered capacity-rerun outputs before any analysis.

Performs no solver work. Checks before any R ratio is interpreted:

1. A semantic parity with the frozen native cohort is NOT re-derivable
   here (different capacity); instead A/B internal agreement is checked.
2. A/B outcome agreement 12/12.
3. Root behavior identical between A and B per parent.
4. Arithmetic consistency of instrumentation counters per condition/depth.
5. B ordering-change counters are exactly 0 (blind sort provably active).
6. Memo reuse alive in both conditions; A ordering provably active.
7. Manifest + provenance recheck (binary, sources, tools, cohort).
8. All 24 rows present, one A and one B per parent, frozen counterbalance.
9. No old C2 raw directory is referenced by this output tree.

Deliberately ignores wall-clock and solver-seconds.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "10x10" / "cache-aware-below-root-capacity-rerun"
C2_OUT = ROOT / "results" / "10x10" / "cache-aware-below-root-confirmation-v2"
COHORT_CSV = OUT / "cohort.csv"
MANIFEST = OUT / "execution_manifest.json"

SUMMARY_FIELDS = {"parent", "condition", "order_index", "outcome",
                  "exact_visited", "exact_maxdepth", "exact_memo",
                  "solver_seconds", "wall_seconds",
                  "root_unique", "root_entered",
                  "root_first_lo", "root_first_hi", "root_witness"}
COUNTERS = ["entry_lookup_calls", "entry_hit_win", "entry_hit_loss",
            "entry_miss", "prefetch_calls", "prefetch_hit_win",
            "prefetch_hit_loss", "prefetch_miss", "put_win", "put_loss",
            "child_eval_from_cache_win", "child_eval_from_cache_loss",
            "child_eval_recursive", "visited_nonterminal_nodes",
            "nodes_with_any_prefetch_hit",
            "nodes_cache_changes_first_child",
            "nodes_cache_changes_full_order",
            "actual_first_cached_loss", "fallback_first_cached_loss",
            "solved_win_nodes", "win_return_from_cached_loss_child"]
DEPTH_FIELDS = {"parent", "condition", "depth", *COUNTERS}
ROOT_FIELDS = ["root_unique", "root_entered",
               "root_first_lo", "root_first_hi", "root_witness"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def as_int(row: dict[str, str], name: str) -> int:
    try:
        return int(row[name])
    except (KeyError, ValueError) as e:
        raise SystemExit(f"bad integer {name}={row.get(name)!r}: {e}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", type=Path,
                    default=OUT / "summary_ab.csv")
    ap.add_argument("--depth", type=Path, default=OUT / "depth_ab.csv")
    args = ap.parse_args()

    summary = read_csv(args.summary)
    depth = read_csv(args.depth)
    if set(summary[0]) != SUMMARY_FIELDS:
        raise SystemExit(f"{args.summary}: schema mismatch: "
                         f"{sorted(set(summary[0]))}")
    if set(depth[0]) != DEPTH_FIELDS:
        raise SystemExit(f"{args.depth}: schema mismatch: "
                         f"{sorted(set(depth[0]))}")

    import csv as _csv, hashlib as _hl, json as _json
    with COHORT_CSV.open(newline="", encoding="utf-8") as f:
        cohort = [r["parent_canonical"].strip().strip('"')
                  for r in _csv.DictReader(f)]
    if len(cohort) != 12 or len(set(cohort)) != 12:
        raise SystemExit(f"cohort must be 12 unique parents: {cohort}")
    frozen = {p: True for p in cohort}

    got: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for r in summary:
        if r["condition"] not in ("cache-aware", "cache-blind"):
            raise SystemExit(f"unknown condition: {r['condition']!r}")
        if r["parent"] in got[r["condition"]]:
            raise SystemExit(f"duplicate summary row: {r['parent']} "
                             f"{r['condition']}")
        got[r["condition"]][r["parent"]] = r
    for cond in ("cache-aware", "cache-blind"):
        if set(got[cond]) != set(frozen):
            raise SystemExit(
                f"{cond} parent set differs from frozen cohort: "
                f"missing={sorted(set(frozen) - set(got[cond]))} "
                f"extra={sorted(set(got[cond]) - set(frozen))}")

    # 1. Row counts: 12 parents x 2 conditions, one run each.
    n_summary = len(summary)
    if n_summary != 24:
        raise SystemExit(f"expected 24 summary rows, got {n_summary}")

    # 2. A/B outcome agreement.
    for p in sorted(frozen):
        a = got["cache-aware"][p]["outcome"]
        b = got["cache-blind"][p]["outcome"]
        if a not in ("WIN", "LOSS"):
            raise SystemExit(f"bad outcome parent={p}: A={a}")
        if a != b:
            raise SystemExit(f"A/B OUTCOME MISMATCH parent={p}: A={a} B={b}")

    # 3. Root behavior identical.
    for p in sorted(frozen):
        for f in ROOT_FIELDS:
            if got["cache-aware"][p][f] != got["cache-blind"][p][f]:
                raise SystemExit(
                    f"ROOT DIVERGENCE parent={p} field={f}: "
                    f"A={got['cache-aware'][p][f]!r} "
                    f"B={got['cache-blind'][p][f]!r}")

    # 4+5. Counter identities; B ordering counters exactly 0.
    seen = set()
    by_key: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: defaultdict(int))
    for r in depth:
        key = (r["parent"], r["condition"], as_int(r, "depth"))
        if key in seen:
            raise SystemExit(f"duplicate parent/condition/depth row: {key}")
        seen.add(key)
        if key[0] not in frozen or key[1] not in ("cache-aware",
                                                  "cache-blind"):
            raise SystemExit(f"depth CSV has non-cohort key: {key}")
        c = {name: as_int(r, name) for name in COUNTERS}
        if c["entry_lookup_calls"] != (c["entry_hit_win"]
                                      + c["entry_hit_loss"] + c["entry_miss"]):
            raise SystemExit(f"entry lookup identity failed at {key}")
        if c["prefetch_calls"] != (c["prefetch_hit_win"]
                                  + c["prefetch_hit_loss"]
                                  + c["prefetch_miss"]):
            raise SystemExit(f"prefetch lookup identity failed at {key}")
        consumed = (c["child_eval_from_cache_win"]
                    + c["child_eval_from_cache_loss"]
                    + c["child_eval_recursive"])
        if consumed > c["prefetch_calls"]:
            raise SystemExit(f"consumed evaluations exceed prefetches "
                             f"at {key}")
        if c["nodes_with_any_prefetch_hit"] > c["visited_nonterminal_nodes"]:
            raise SystemExit(f"prefetch-hit nodes exceed nonterminal at {key}")
        if c["nodes_cache_changes_first_child"] > c["visited_nonterminal_nodes"]:
            raise SystemExit(f"first-child changes exceed nonterminal at {key}")
        if c["nodes_cache_changes_full_order"] > c["visited_nonterminal_nodes"]:
            raise SystemExit(f"full-order changes exceed nonterminal at {key}")
        if c["nodes_cache_changes_first_child"] > c["nodes_cache_changes_full_order"]:
            raise SystemExit(f"first changes exceed full changes at {key}")
        if c["actual_first_cached_loss"] > c["nodes_with_any_prefetch_hit"]:
            raise SystemExit(f"actual cached-loss-first exceeds hits at {key}")
        if c["fallback_first_cached_loss"] > c["nodes_with_any_prefetch_hit"]:
            raise SystemExit(f"fallback cached-loss-first exceeds hits at {key}")
        if c["win_return_from_cached_loss_child"] > c["solved_win_nodes"]:
            raise SystemExit(f"cached-loss WIN returns exceed solved WIN at {key}")
        if c["win_return_from_cached_loss_child"] > c["child_eval_from_cache_loss"]:
            raise SystemExit(f"cached-loss WIN returns exceed cached LOSS "
                            f"evaluations at {key}")
        if key[1] == "cache-blind" and (
                c["nodes_cache_changes_first_child"] != 0
                or c["nodes_cache_changes_full_order"] != 0):
            raise SystemExit(f"B ordering counter nonzero at {key}: blind "
                             "sort not active?")
        for name, value in c.items():
            by_key[(key[0], key[1])][name] += value

    missing = [(p, c) for p in frozen for c in ("cache-aware", "cache-blind")
               if (p, c) not in by_key]
    if missing:
        raise SystemExit(f"keys with no depth counters: {missing}")

    # 6. Manifest + provenance recheck.
    man = _json.loads(MANIFEST.read_text(encoding="utf-8"))
    if man["cohort_sha256"] != _hl.sha256(COHORT_CSV.read_bytes()).hexdigest():
        raise SystemExit("cohort.csv sha mismatch vs execution manifest")
    if man["parent_solve"]["binary_sha256"] != _hl.sha256(
            (ROOT / man["parent_solve"]["binary"]).read_bytes()).hexdigest():
        raise SystemExit("solver binary sha mismatch vs execution manifest")
    for key, rel in (("runner_script_sha256",
                      "scripts/run_capacity_rerun.py"),
                     ("verifier_script_sha256",
                      "scripts/verify_capacity_rerun.py"),
                     ("analysis_script_sha256",
                      "scripts/analyze_capacity_rerun.py")):
        if man[key] != _hl.sha256((ROOT / rel).read_bytes()).hexdigest():
            raise SystemExit(f"{rel} sha mismatch vs execution manifest")

    # 7. Memo reuse alive in both conditions; A ordering provably active.
    for p in sorted(frozen):
        for cond in ("cache-aware", "cache-blind"):
            c = by_key[(p, cond)]
            if c["prefetch_hit_win"] + c["prefetch_hit_loss"] == 0:
                raise SystemExit(f"memo reuse dead at {(p, cond)}: no hits")
            if (c["child_eval_from_cache_win"]
                    + c["child_eval_from_cache_loss"]) == 0:
                raise SystemExit(f"memo reuse dead at {(p, cond)}: no cached evals")
        if by_key[(p, "cache-aware")]["nodes_cache_changes_full_order"] == 0:
            raise SystemExit(f"A ordering inactive at {p}: no order changes")

    # 8. Old C2 raw tree must not be inside this output tree.
    c2_raw = C2_OUT / "raw"
    this_raw = OUT / "raw"
    if c2_raw.resolve() in this_raw.resolve().parents or (
            this_raw.resolve() in c2_raw.resolve().parents):
        raise SystemExit("old C2 raw directory collides with this output tree")

    print("capacity-rerun verification: PASS")
    print("cohort_match=12/12")
    print("AB_outcome_agreement=12/12")
    print("root_identical=12/12")
    print("manifest_provenance=ok")
    print(f"depth_rows={len(depth)}")
    print("parent,cond,entry_hit_rate,prefetch_hit_rate,"
          "cached_eval_fraction,first_order_change_rate,"
          "any_order_change_rate,cached_loss_win_shortcut_rate")

    def rate(num: int, den: int) -> str:
        return "nan" if den == 0 else f"{num/den:.6f}"

    for p in sorted(frozen):
        for cond in ("cache-aware", "cache-blind"):
            c = by_key[(p, cond)]
            entry_hits = c["entry_hit_win"] + c["entry_hit_loss"]
            prefetch_hits = c["prefetch_hit_win"] + c["prefetch_hit_loss"]
            cached = (c["child_eval_from_cache_win"]
                      + c["child_eval_from_cache_loss"])
            consumed = cached + c["child_eval_recursive"]
            print(",".join([
                p, cond,
                rate(entry_hits, c["entry_lookup_calls"]),
                rate(prefetch_hits, c["prefetch_calls"]),
                rate(cached, consumed),
                rate(c["nodes_cache_changes_first_child"],
                     c["visited_nonterminal_nodes"]),
                rate(c["nodes_cache_changes_full_order"],
                     c["visited_nonterminal_nodes"]),
                rate(c["win_return_from_cached_loss_child"],
                     c["solved_win_nodes"])]))


if __name__ == "__main__":
    main()
