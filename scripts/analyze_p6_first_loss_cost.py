#!/usr/bin/env python3
"""P6 (data-only, no new solves): cost to first exact LOSS child under different
candidate orderings, with probe cost included in the total.

Orderings:
  A. file order (deterministic baseline = children txt order)
  B. fresh 1M probe memo ascending + move tiebreak (preregistered V2 rule)

Cost model per parent:
  cost_A = sum of exact `seconds` for children examined until first LOSS in file order
  cost_B = (sum of probe `seconds` over ALL children) + (sum of exact `seconds`
             for children examined until first LOSS in memo order)

Uses already-collected V2 probe and exact CSVs. No new solver runs.
"""

from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
V2_DIR = REPO_ROOT / "results" / "10x10" / "clean-holdout-v2"
OUT_JSON = V2_DIR / "p6_first_loss_cost.json"
OUT_CSV = V2_DIR / "p6_first_loss_cost.csv"


def norm(s: str) -> str:
    return "-".join(str(x) for x in sorted(int(v) for v in s.replace(",", "-").split("-") if v != ""))


def move_of(parent: str, child: str) -> int:
    p = set(int(v) for v in parent.replace(",", "-").split("-"))
    c = set(int(v) for v in child.replace(",", "-").split("-"))
    return next(iter(c - p))


def main() -> None:
    probes: dict[tuple[str, str], dict[str, str]] = {}
    with (V2_DIR / "independent_probe_1000000.csv").open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            probes[(r["parent"].strip(), norm(r["state"]))] = r
    exacts: dict[tuple[str, str], dict[str, str]] = {}
    with (V2_DIR / "exact_outcomes.csv").open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            exacts[(r["parent"].strip(), norm(r["state"]))] = r

    parents = sorted({p for (p, _) in probes})
    rows = []
    for p in parents:
        children = sorted({s for (q, s) in probes if q == p})
        # A: file order = numeric sort of child tuple (matches children txt generation order)
        order_a = sorted(children)
        # B: memo ascending, move tiebreak
        order_b = sorted(children, key=lambda s: (int(probes[(p, s)]["memo"]), move_of(p, s)))

        def cost_to_first_loss(order: list[str]) -> tuple[int, float]:
            total = 0.0
            for i, s in enumerate(order, 1):
                total += float(exacts[(p, s)]["seconds"])
                if exacts[(p, s)]["outcome"].strip().upper() == "LOSS":
                    return i, total
            return len(order) + 1, total

        pos_a, exact_cost_a = cost_to_first_loss(order_a)
        pos_b, exact_cost_b = cost_to_first_loss(order_b)
        probe_cost = sum(float(probes[(p, s)]["seconds"]) for s in children)
        total_a = exact_cost_a
        total_b = probe_cost + exact_cost_b
        rows.append({
            "parent": p,
            "m": len(children),
            "probe_cost_s": round(probe_cost, 2),
            "pos_first_loss_file_order": pos_a,
            "exact_cost_to_first_loss_file_order_s": round(exact_cost_a, 2),
            "total_cost_file_order_s": round(total_a, 2),
            "pos_first_loss_memo_order": pos_b,
            "exact_cost_to_first_loss_memo_order_s": round(exact_cost_b, 2),
            "total_cost_memo_order_s": round(total_b, 2),
            "total_cost_ratio_memo_over_file": round(total_b / total_a, 3) if total_a > 0 else None,
        })

    ratios = [r["total_cost_ratio_memo_over_file"] for r in rows if r["total_cost_ratio_memo_over_file"]]
    summary = {
        "parents": len(rows),
        "mean_total_cost_file_order_s": statistics.mean([r["total_cost_file_order_s"] for r in rows]),
        "mean_total_cost_memo_order_s": statistics.mean([r["total_cost_memo_order_s"] for r in rows]),
        "median_total_cost_ratio_memo_over_file": statistics.median(ratios),
        "mean_total_cost_ratio_memo_over_file": statistics.mean(ratios),
        "parents_where_memo_total_cheaper": sum(1 for x in ratios if x < 1.0),
    }

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    OUT_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    for r in rows:
        print(f"{r['parent']:<12} A: pos={r['pos_first_loss_file_order']:<4} cost={r['total_cost_file_order_s']:<10} "
              f"B: pos={r['pos_first_loss_memo_order']:<4} probe={r['probe_cost_s']:<9} total={r['total_cost_memo_order_s']:<10} "
              f"ratio={r['total_cost_ratio_memo_over_file']}")


if __name__ == "__main__":
    main()
