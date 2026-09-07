#!/usr/bin/env python3
"""Preregistered analysis for 10x10 Clean Holdout V2.

Identical ranking rule and endpoints as V1 (see docs/10X10_FRESH_PARENT_HOLDOUT_V2_PREREG.md):
- ranking = probe LOSS first, unresolved by memo ascending, probe WIN last, move-index tiebreak
- primary: first LOSS rank vs exact random median per eligible parent; one-sided sign test
- secondary: rank sum, normalized ranks, AUC, per-parent table

Inputs (all frozen before exact outcomes except probes which were frozen before exact):
  results/10x10/clean-holdout-v2/holdout_v2_parents_primary.csv
  results/10x10/clean-holdout-v2/children/children_<parent>.txt
  results/10x10/clean-holdout-v2/independent_probe_1000000.csv
  results/10x10/clean-holdout-v2/exact_outcomes.csv (merged from exact_outcomes_w*.csv)
"""

from __future__ import annotations

import csv
import json
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
V2_DIR = REPO_ROOT / "results" / "10x10" / "clean-holdout-v2"
CHILDREN_DIR = V2_DIR / "children"
PRIMARY_CSV = V2_DIR / "holdout_v2_parents_primary.csv"
PROBE_CSV = V2_DIR / "independent_probe_1000000.csv"
EXACT_CSV = V2_DIR / "exact_outcomes.csv"
PARENT_CSV = V2_DIR / "preregistered_parent_results.csv"
SUMMARY_JSON = V2_DIR / "preregistered_summary.json"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from analyze_probe_holdout_preregistered import (
    auc_from_order,
    corrected_key,
    first_loss_rank,
    norm_state,
    one_sided_sign_p,
    random_median,
)


def safe_parent(parent: str) -> str:
    return parent.replace(",", "_")


def load_parents() -> list[str]:
    with PRIMARY_CSV.open(newline="", encoding="utf-8") as f:
        return [r["parent_canonical"].strip() for r in csv.DictReader(f)]


def load_children(parent: str) -> list[str]:
    p = CHILDREN_DIR / f"children_{safe_parent(parent)}.txt"
    out = [norm_state(x.strip()) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    if len(out) != len(set(out)):
        raise RuntimeError(f"duplicate children for {parent}")
    return out


def load_probe() -> dict[tuple[str, str], dict[str, str]]:
    with PROBE_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        key = (row["parent"].strip(), norm_state(row["state"]))
        if key in out:
            raise RuntimeError(f"duplicate probe row: {key}")
        out[key] = row
    return out


def load_exact() -> dict[tuple[str, str], str]:
    if not EXACT_CSV.exists():
        # Fall back to per-worker files (pre-merge)
        worker_files = sorted(V2_DIR.glob("exact_outcomes_w*.csv"))
        if not worker_files:
            raise FileNotFoundError(f"no exact outcomes found in {V2_DIR}")
        out: dict[tuple[str, str], str] = {}
        for wf in worker_files:
            with wf.open(newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    key = (row["parent"].strip(), norm_state(row["state"]))
                    outcome = row["outcome"].strip().upper()
                    if outcome not in {"WIN", "LOSS"}:
                        raise RuntimeError(f"non-exact outcome in {wf}: {outcome}")
                    if key in out and out[key] != outcome:
                        raise RuntimeError(f"conflicting exact outcome for {key}")
                    out[key] = outcome
        return out
    with EXACT_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = {}
    for row in rows:
        key = (row["parent"].strip(), norm_state(row["state"]))
        outcome = row["outcome"].strip().upper()
        if outcome not in {"WIN", "LOSS"}:
            raise RuntimeError(f"non-exact outcome: {outcome}")
        out[key] = outcome
    return out


def main() -> None:
    parents = load_parents()
    probes = load_probe()
    exact_all = load_exact()

    parent_rows: list[dict[str, object]] = []
    aucs: list[float] = []
    ranks: list[int] = []
    expected_null_sum = 0.0

    for parent in parents:
        children = load_children(parent)
        exact = {s: exact_all[(parent, s)] for s in children}
        pmap = {s: probes[(parent, s)] for s in children}
        order = sorted(children, key=lambda s: corrected_key(parent, s, pmap[s]))
        m = len(children)
        loss = sum(1 for s in children if exact[s] == "LOSS")
        rank = first_loss_rank(order, exact)
        med = random_median(m, loss)
        auc = auc_from_order(order, exact)
        if auc is not None:
            aucs.append(auc)
        relation = "better" if rank < med else "worse" if rank > med else "tie"
        # Expected first-loss rank under random null: (m+1)/(loss+1)
        if loss > 0:
            ranks.append(rank)
            expected_null_sum += (m + 1) / (loss + 1)
        parent_rows.append({
            "parent": parent,
            "m": m,
            "loss": loss,
            "first_loss_rank": rank,
            "random_median": med,
            "relation": relation,
            "auc": auc,
            "normalized_rank": rank / m,
        })

    eligible = [r for r in parent_rows if r["loss"] and r["loss"] > 0]
    scored = [r for r in eligible if r["relation"] != "tie"]
    better = sum(1 for r in scored if r["relation"] == "better")
    worse = sum(1 for r in scored if r["relation"] == "worse")
    tie = sum(1 for r in eligible if r["relation"] == "tie")

    summary = {
        "parents": len(parents),
        "eligible_parents": len(eligible),
        "better": better,
        "tie": tie,
        "worse": worse,
        "one_sided_sign_p": one_sided_sign_p(better, worse),
        "rank_sum": sum(ranks),
        "rank_sum_null_expectation": expected_null_sum,
        "mean_normalized_rank": statistics.mean([r["normalized_rank"] for r in eligible]) if eligible else None,
        "median_normalized_rank": statistics.median([r["normalized_rank"] for r in eligible]) if eligible else None,
        "mean_auc": statistics.mean(aucs) if aucs else None,
        "median_auc": statistics.median(aucs) if aucs else None,
        "aucs_computed": len(aucs),
    }

    with PARENT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(parent_rows[0].keys()))
        w.writeheader()
        w.writerows(parent_rows)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    for r in parent_rows:
        auc_str = f"{r['auc']:.3f}" if r["auc"] is not None else "N/A"
        print(f"{r['parent']:<12} m={r['m']:<4} l={r['loss']:<4} rank={r['first_loss_rank']:<4} med={r['random_median']:<4} {r['relation']:<7} auc={auc_str}")


if __name__ == "__main__":
    main()
