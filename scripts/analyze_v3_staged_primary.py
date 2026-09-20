#!/usr/bin/env python3
"""Evaluate Staged Probe V3 primary/secondary endpoints after exact labels exist."""

from __future__ import annotations

import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
V3 = REPO_ROOT / "results" / "10x10" / "staged-v3-holdout"


def move_of(parent: str, child: str) -> int:
    p = {int(x) for x in parent.split(",")}
    c = {int(x) for x in child.split(",")}
    extra = c - p
    if len(extra) != 1:
        raise RuntimeError(f"not a child: {parent} -> {child}")
    return next(iter(extra))


def corrected_key_from(row: dict[str, str], parent: str, outcome_field: str, memo_field: str) -> tuple:
    outcome = row[outcome_field].strip().upper()
    memo = int(row[memo_field])
    move = move_of(parent, row["state"])
    if outcome == "LOSS":
        tier = 0
    elif outcome == "WIN":
        tier = 2
    else:
        tier = 1
    return (tier, memo, move)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    tasks = load_csv(V3 / "exact_task_list.csv")
    probe_10k = {(r["parent"], r["state"]): r for r in load_csv(V3 / "independent_probe_10000.csv")}
    shortlist = load_csv(V3 / "top11_shortlist.csv")
    rank_1m = load_csv(V3 / "top11_rank_1m.csv")
    exact_rows = load_csv(V3 / "exact_outcomes.csv")

    errors = [r for r in exact_rows if str(r.get("probe_outcome", r.get("outcome", ""))).startswith("ERROR")]
    if errors:
        raise RuntimeError(f"{len(errors)} exact ERROR rows; fix before evaluation")
    if len(exact_rows) != len(tasks):
        raise RuntimeError(f"exact rows {len(exact_rows)} != tasks {len(tasks)}")

    exact = {}
    for r in exact_rows:
        outcome = r.get("outcome") or r.get("probe_outcome")
        exact[(r["parent"], r["state"])] = {
            "outcome": outcome.strip().upper(),
            "visited": int(r["visited"]),
            "memo": int(r["memo"]),
            "seconds": float(r["seconds"]),
            "maxdepth": int(r["maxdepth"]),
        }

    by_parent_tasks: dict[str, list[str]] = defaultdict(list)
    for t in tasks:
        by_parent_tasks[t["parent"]].append(t["state"])

    shortlist_by_parent: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in shortlist:
        shortlist_by_parent[r["parent"]].append(r)
    rank1m_by_parent: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in rank_1m:
        rank1m_by_parent[r["parent"]].append(r)

    parent_rows = []
    for parent in sorted(by_parent_tasks):
        children = by_parent_tasks[parent]
        n = len(children)
        loss_states = [s for s in children if exact[(parent, s)]["outcome"] == "LOSS"]
        l = len(loss_states)
        top11_states = [r["state"] for r in sorted(shortlist_by_parent[parent], key=lambda x: int(x["rank"]))]
        top11_loss = [s for s in top11_states if exact[(parent, s)]["outcome"] == "LOSS"]

        # 10k full ordering
        p10 = [probe_10k[(parent, s)] for s in children]
        p10_ranked = sorted(p10, key=lambda r: corrected_key_from(r, parent, "probe_outcome", "memo"))
        first_loss_10k = None
        for i, r in enumerate(p10_ranked, start=1):
            if exact[(parent, r["state"])]["outcome"] == "LOSS":
                first_loss_10k = i
                break

        # 1M shortlist ordering
        r1m = sorted(rank1m_by_parent[parent], key=lambda x: int(x["rank_1m"]))
        first_loss_1m = None
        first_loss_1m_state = None
        for i, r in enumerate(r1m, start=1):
            if exact[(parent, r["state"])]["outcome"] == "LOSS":
                first_loss_1m = i
                first_loss_1m_state = r["state"]
                break

        top1 = exact[(parent, r1m[0]["state"])]["outcome"] if r1m else None
        top1_hit = top1 == "LOSS"
        top3_hit = any(exact[(parent, r["state"])]["outcome"] == "LOSS" for r in r1m[:3])
        top6_hit = any(exact[(parent, r["state"])]["outcome"] == "LOSS" for r in r1m[:6])

        probe_nodes = 10_000 * n + 1_000_000 * len(top11_states)
        full_1m_nodes = 1_000_000 * n
        reduction = 1.0 - (probe_nodes / full_1m_nodes)

        parent_rows.append(
            {
                "parent": parent,
                "n_children": n,
                "loss_count": l,
                "eligible": int(l >= 1),
                "top11_contains_loss": int(len(top11_loss) >= 1),
                "top11_loss_count": len(top11_loss),
                "first_loss_rank_1m_shortlist": first_loss_1m if first_loss_1m is not None else "",
                "first_loss_state_1m": first_loss_1m_state or "",
                "first_loss_rank_10k_full": first_loss_10k if first_loss_10k is not None else "",
                "top1_loss": int(top1_hit),
                "top3_loss": int(top3_hit),
                "top6_loss": int(top6_hit),
                "probe_nodes_staged": probe_nodes,
                "probe_nodes_full_1m": full_1m_nodes,
                "probe_node_reduction": f"{reduction:.4f}",
                "exact_seconds_sum": f"{sum(exact[(parent, s)]["seconds"] for s in children):.3f}",
                "exact_visited_sum": str(sum(exact[(parent, s)]["visited"] for s in children)),
            }
        )

    out_csv = V3 / "primary_results.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(parent_rows[0].keys()))
        w.writeheader()
        w.writerows(parent_rows)

    eligible = [r for r in parent_rows if r["eligible"] == 1]
    successes = [r for r in eligible if r["top11_contains_loss"] == 1]
    ranks = [r["first_loss_rank_1m_shortlist"] for r in eligible if r["first_loss_rank_1m_shortlist"] != ""]
    ranks = [int(x) for x in ranks]

    def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
        if n == 0:
            return (float("nan"), float("nan"))
        p = k / n
        denom = 1 + z * z / n
        center = (p + z * z / (2 * n)) / denom
        half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
        return (max(0.0, center - half), min(1.0, center + half))

    lo, hi = wilson(len(successes), len(eligible))
    summary = {
        "n_parents": len(parent_rows),
        "n_eligible": len(eligible),
        "primary_successes": len(successes),
        "primary_recall": len(successes) / len(eligible) if eligible else None,
        "primary_wilson95": [lo, hi],
        "first_loss_rank_1m_median": statistics.median(ranks) if ranks else None,
        "first_loss_rank_1m_values": ranks,
        "top1_recall": sum(r["top1_loss"] for r in eligible) / len(eligible) if eligible else None,
        "top3_recall": sum(r["top3_loss"] for r in eligible) / len(eligible) if eligible else None,
        "top6_recall": sum(r["top6_loss"] for r in eligible) / len(eligible) if eligible else None,
        "probe_nodes_staged_total": sum(r["probe_nodes_staged"] for r in parent_rows),
        "probe_nodes_full_1m_total": sum(r["probe_nodes_full_1m"] for r in parent_rows),
        "probe_node_reduction_total": 1.0
        - (
            sum(r["probe_nodes_staged"] for r in parent_rows)
            / sum(r["probe_nodes_full_1m"] for r in parent_rows)
        ),
        "catastrophic_miss_parents": [r["parent"] for r in eligible if r["top11_contains_loss"] == 0],
        "parent_rows": parent_rows,
        "verdict": (
            "SUPPORTS staged top-11 LOSS coverage"
            if eligible and len(successes) == len(eligible)
            else "PARTIAL/FAIL staged top-11 LOSS coverage"
        ),
    }
    (V3 / "primary_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in summary if k != "parent_rows"}, indent=2))
    print("\nPer-parent:")
    for r in parent_rows:
        print(
            f"  {r['parent']}: n={r['n_children']} L={r['loss_count']} "
            f"top11_hit={r['top11_contains_loss']} rank1m={r['first_loss_rank_1m_shortlist']} "
            f"top1={r['top1_loss']} top3={r['top3_loss']} top6={r['top6_loss']} "
            f"red={r['probe_node_reduction']}"
        )


if __name__ == "__main__":
    main()
