#!/usr/bin/env python3
"""Mechanism decomposition for AB staged-V3 root-order results (post hoc)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "results" / "10x10" / "ab-staged-v3-root"


def load_order(parent: str) -> list[str]:
    p = OUT / "root_orders" / f"order_{parent.replace(',', '_')}.txt"
    return [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]


def main() -> None:
    summary = list(csv.DictReader((OUT / "parent_summary.csv").open(newline="", encoding="utf-8")))
    rank1m = list(csv.DictReader((OUT / "top11_rank_1m.csv").open(newline="", encoding="utf-8")))
    by_rank = {}
    for r in rank1m:
        by_rank.setdefault(r["parent"], []).append(r)

    rows = []
    for r in summary:
        parent = r["parent"]
        order = load_order(parent)
        head = [x for x in order[:11]]
        ranks = sorted(by_rank.get(parent, []), key=lambda x: int(x["rank_1m"]))
        shortlist_states = [x["state"] for x in ranks]
        # Is the B first entered child inside the 1M shortlist head?
        # entered==1 means first child proved the parent (LOSS for next).
        b_entered = int(r["b_entered"])
        a_entered = int(r["a_entered"])
        exact_delta = int(r["b_exact_visited"]) - int(r["a_exact_visited"])
        probe = int(r["probe_visited_total"])
        total_delta = int(r["b_total_visited"]) - int(r["a_exact_visited"])
        # WIN-prefix count proxy
        win_prefix_a = max(a_entered - 1, 0)
        win_prefix_b = max(b_entered - 1, 0)

        first_loss_in_shortlist = "unknown"
        if b_entered == 1 and order:
            first = order[0]
            first_loss_in_shortlist = first in shortlist_states

        rows.append(
            {
                "parent": parent,
                "visited_ratio": float(r["visited_ratio"]),
                "exact_only_ratio": float(r["exact_only_ratio"]),
                "probe_visited": probe,
                "probe_over_A": probe / int(r["a_exact_visited"]),
                "exact_delta": exact_delta,
                "total_delta": total_delta,
                "probe_component": probe,
                "exact_component": exact_delta,
                "a_entered": a_entered,
                "b_entered": b_entered,
                "win_prefix_a": win_prefix_a,
                "win_prefix_b": win_prefix_b,
                "win_prefix_saved": win_prefix_a - win_prefix_b,
                "first_loss_in_shortlist_head": first_loss_in_shortlist,
                "improved": int(r["b_total_visited"]) < int(r["a_exact_visited"]),
                "mechanism_class": (
                    "cheap_A_probe_dominated"
                    if int(r["a_exact_visited"]) < 15_000_000 and not (int(r["b_total_visited"]) < int(r["a_exact_visited"]))
                    else (
                        "expensive_A_wins"
                        if int(r["b_total_visited"]) < int(r["a_exact_visited"])
                        else "loss_proof_cost_or_order"
                    )
                ),
            }
        )

    fields = list(rows[0].keys())
    with (OUT / "mechanism_decomposition.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    # hypothesis support
    h1 = sum(1 for r in rows if r["win_prefix_saved"] > 0)
    h1_win = sum(1 for r in rows if r["win_prefix_saved"] > 0 and r["improved"])
    cheap_fail = [r["parent"] for r in rows if r["mechanism_class"] == "cheap_A_probe_dominated"]
    exact_worse = [r["parent"] for r in rows if r["exact_delta"] > 0]

    mech = {
        "h1_win_prefix_reduced_parents": h1,
        "h1_of_those_improved": h1_win,
        "cheap_A_probe_dominated_failures": cheap_fail,
        "exact_worse_parents": exact_worse,
        "median_probe_over_A": sorted(r["probe_over_A"] for r in rows)[len(rows) // 2],
        "classes": {
            k: sum(1 for r in rows if r["mechanism_class"] == k)
            for k in {r["mechanism_class"] for r in rows}
        },
    }
    (OUT / "mechanism_summary.json").write_text(json.dumps(mech, indent=2) + "\n", encoding="utf-8")

    print("mechanism classes:", mech["classes"])
    print(f"H1 (entered reduced): {h1}/16; of those improved {h1_win}/{h1}")
    print("cheap A probe-dominated failures:", cheap_fail)
    print("exact worse (selected LOSS cost):", exact_worse)
    print(f"median probe/A: {mech['median_probe_over_A']:.3f}")


if __name__ == "__main__":
    main()
