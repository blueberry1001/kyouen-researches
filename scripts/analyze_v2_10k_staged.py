#!/usr/bin/env python3
"""P8 (exploratory, data-only): staged-probe simulations on frozen 10k rows.

No new solver runs. Hybrid order rule (fixed before seeing output):
  probed-K sorted by (memo_used ascending, move ascending),
  then the remaining m-K children in frozen file order.
Total cost = sum of 10k probe seconds over the K probed children
           + exact seconds scanning the hybrid order to the first LOSS.
Ratio is against the file-order exact-only baseline (same as P5).

Strategies:
  D-K: probe the first K children in file order. K in {5,10,20,32}.
  C-K-{asc,desc}: rank children by geometric legal-move count (pure-Python
    co-circularity, no solver; noktasinda solver equivalence is NOT claimed
    beyond the shared determinant), probe top K. K in {5,10,20,32}.

Outputs: results/10x10/clean-holdout-v2/staged_10k_simulation.csv/.json
"""

from __future__ import annotations

import csv
import itertools
import json
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
V2 = REPO_ROOT / "results" / "10x10" / "clean-holdout-v2"
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from analyze_probe_holdout_preregistered import norm_state  # noqa: E402
from generate_v2_holdout_children import forbidden  # noqa: E402

KS = (5, 10, 20, 32)


def legal_move_count(child: str) -> int:
    pts = [int(v) for v in child.replace(",", "-").split("-")]
    assert len(pts) == 4
    n = 0
    for p5 in range(100):
        if p5 in pts:
            continue
        illegal = False
        for trio in itertools.combinations(pts, 3):
            if forbidden(*trio, p5):
                illegal = True
                break
        if not illegal:
            n += 1
    return n


def move_of(parent: str, child: str) -> int:
    p = {int(v) for v in parent.replace(",", "-").split("-")}
    c = {int(v) for v in child.replace(",", "-").split("-")}
    return next(iter(c - p))


def main() -> None:
    with (V2 / "exact_task_list.csv").open(newline="", encoding="utf-8") as f:
        tasks = list(csv.DictReader(f))
    probes = {(r["parent"].strip(), norm_state(r["state"])): r
              for r in csv.DictReader(open(V2 / "independent_probe_10000.csv", newline="", encoding="utf-8"))}
    exact = {(r["parent"].strip(), norm_state(r["state"])): r
             for r in csv.DictReader(open(V2 / "exact_outcomes.csv", newline="", encoding="utf-8"))}

    file_order: dict[str, list[str]] = {}
    for t in tasks:
        file_order.setdefault(t["parent"].strip(), []).append(norm_state(t["state"]))
    parents = sorted(file_order)

    # Geometric legal-move counts (cached per child).
    legal: dict[tuple[str, str], int] = {}
    for p in parents:
        for s in file_order[p]:
            legal[(p, s)] = legal_move_count(s)

    def strategies(p: str, children: list[str]) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for k in KS:
            out[f"D-K{k}"] = children[:k]
        for k in KS:
            by_asc = sorted(children, key=lambda s: (legal[(p, s)], file_order[p].index(s)))
            out[f"C-K{k}-asc"] = by_asc[:k]
            by_desc = sorted(children, key=lambda s: (-legal[(p, s)], file_order[p].index(s)))
            out[f"C-K{k}-desc"] = by_desc[:k]
        return out

    def hybrid_order(p: str, children: list[str], probed: list[str]) -> list[str]:
        pset = set(probed)
        head = sorted(probed, key=lambda s: (int(probes[(p, s)]["memo"]), move_of(p, s)))
        tail = [s for s in children if s not in pset]
        return head + tail

    def exact_scan_cost(p: str, order: list[str]) -> tuple[int, float]:
        total = 0.0
        for i, s in enumerate(order, 1):
            total += float(exact[(p, s)]["seconds"])
            if exact[(p, s)]["outcome"].strip().upper() == "LOSS":
                return i, total
        return len(order) + 1, total

    rows = []
    for p in parents:
        children = file_order[p]
        pos_a, cost_a = exact_scan_cost(p, children)
        for name, probed in strategies(p, children).items():
            probe_cost = sum(float(probes[(p, s)]["seconds"]) for s in probed)
            order = hybrid_order(p, children, probed)
            pos, ecost = exact_scan_cost(p, order)
            total = probe_cost + ecost
            rows.append({
                "parent": p, "strategy": name, "K": len(probed),
                "pos_first_loss": pos, "probe_cost_s": round(probe_cost, 2),
                "exact_cost_s": round(ecost, 2), "total_s": round(total, 2),
                "ratio_over_file": round(total / cost_a, 4) if cost_a > 0 else "",
                "file_baseline_s": round(cost_a, 2),
            })

    agg: dict[str, dict] = {}
    for name in sorted({r["strategy"] for r in rows}):
        sub = [r for r in rows if r["strategy"] == name]
        ratios = [r["ratio_over_file"] for r in sub if r["ratio_over_file"] != ""]
        agg[name] = {
            "median_ratio": round(statistics.median(ratios), 4),
            "mean_ratio": round(statistics.mean(ratios), 4),
            "improved": sum(1 for x in ratios if x < 1.0),
            "worse": sum(1 for x in ratios if x > 1.0),
            "aggregate_total_s": round(sum(r["total_s"] for r in sub), 2),
        }

    with (V2 / "staged_10k_simulation.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    (V2 / "staged_10k_simulation.json").write_text(json.dumps(agg, indent=2) + "\n")

    # Reference: primary all-probe medians for comparison.
    print("== staged strategy aggregates (median ratio vs file order) ==")
    for name, a in sorted(agg.items()):
        print(f"{name:<12} median={a['median_ratio']:<8} mean={a['mean_ratio']:<8} "
              f"improved={a['improved']}/12 worse={a['worse']}/12 agg_total={a['aggregate_total_s']}")
    print("reference: primary 10k-all median=0.8475 improved=8/12 agg_total=2002.37; file baseline agg=2893.15")


if __name__ == "__main__":
    main()
