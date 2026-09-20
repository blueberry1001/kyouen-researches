#!/usr/bin/env python3
"""Primary + secondary analysis for the parent-level 10k benchmark.

Primary (visited work, prereg):
  A_work = A exact_visited
  B_work = probe_visited_total + B exact_visited
  work_ratio = B_work / A_work
Success: median < 1.0 and >=7/12 parents with ratio < 1.0.

Secondary: solver-seconds ratios, wall ratios, exact-only visited ratio,
P5 desk-prediction comparison (seconds basis), probe determinism cross-check
against the earlier frozen 10k CSV (reference only; ordering used fresh rows).

Outputs: parent_benchmark_results.csv, summary.json (under BENCH).
"""

from __future__ import annotations

import csv
import json
import math
import statistics
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
V2 = REPO_ROOT / "results" / "10x10" / "clean-holdout-v2"
BENCH = REPO_ROOT / "results" / "10x10" / "parent-benchmark"


def main() -> None:
    with (BENCH / "parent_benchmark_raw.csv").open(newline="", encoding="utf-8") as f:
        raw = {(r["parent"], r["strategy"]): r for r in csv.DictReader(f)}
    parents = sorted({p for p, _ in raw})
    assert len(parents) == 12 and all((p, "A") in raw and (p, "B") in raw for p in parents)

    p5 = {}
    with (V2 / "p6_10k_first_loss_cost.csv").open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            p5[r["parent"]] = r

    rows = []
    for p in parents:
        a, b = raw[(p, "A")], raw[(p, "B")]
        aw = int(a["exact_visited"])
        bw = int(b["probe_visited_total"]) + int(b["exact_visited"])
        ase = float(a["exact_seconds"])
        bse = float(b["probe_seconds_total"]) + float(b["exact_seconds"])
        awall = float(a["wall_seconds"])
        bwall = float(b["wall_seconds"])
        rows.append({
            "parent": p,
            "outcome_A": a["outcome"], "outcome_B": b["outcome"],
            "A_visited": aw, "B_exact_visited": int(b["exact_visited"]),
            "B_probe_visited": int(b["probe_visited_total"]), "B_work": bw,
            "work_ratio": bw / aw,
            "A_seconds": round(ase, 3), "B_total_seconds": round(bse, 3),
            "seconds_ratio": round(bse / ase, 4) if ase else "",
            "A_wall": awall, "B_wall": bwall,
            "wall_ratio": round(bwall / awall, 4) if awall else "",
            "exact_only_visited_ratio": round(int(b["exact_visited"]) / aw, 4),
            "A_memo": a["exact_memo"], "B_memo": b["exact_memo"],
            "A_entered": a["root_entered"], "B_entered": b["root_entered"],
            "A_unique": a["root_unique"], "B_unique": b["root_unique"],
            "P5_ratio_10k_over_file": p5[p]["ratio_10k_over_file"],
            "P5_total_10k_s": p5[p]["total_cost_10k_s"],
            "P5_file_s": p5[p]["exact_cost_file_order_s"],
        })

    ratios = [r["work_ratio"] for r in rows]
    summary = {
        "parents": 12,
        "agreement_A_B": sum(1 for r in rows if r["outcome_A"] == r["outcome_B"]),
        "median_work_ratio": statistics.median(ratios),
        "geometric_mean_work_ratio": round(math.exp(statistics.mean(math.log(x) for x in ratios)), 4),
        "arithmetic_mean_work_ratio": statistics.mean(ratios),
        "aggregate_work_ratio": sum(r["B_work"] for r in rows) / sum(r["A_visited"] for r in rows),
        "aggregate_A_visited": sum(r["A_visited"] for r in rows),
        "aggregate_B_work": sum(r["B_work"] for r in rows),
        "improved": sum(1 for x in ratios if x < 1.0),
        "tie": sum(1 for x in ratios if x == 1.0),
        "worse": sum(1 for x in ratios if x > 1.0),
        "success_median_lt_1": statistics.median(ratios) < 1.0,
        "success_ge7_improved": sum(1 for x in ratios if x < 1.0) >= 7,
        "best_parent": min(rows, key=lambda r: r["work_ratio"])["parent"],
        "best_ratio": min(ratios),
        "worst_parent": max(rows, key=lambda r: r["work_ratio"])["parent"],
        "worst_ratio": max(ratios),
        "median_seconds_ratio": statistics.median([r["seconds_ratio"] for r in rows]),
        "median_wall_ratio": statistics.median([r["wall_ratio"] for r in rows]),
        "median_exact_only_visited_ratio": statistics.median(
            [r["exact_only_visited_ratio"] for r in rows]),
    }

    with (BENCH / "parent_benchmark_results.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    (BENCH / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    print(json.dumps(summary, indent=2))
    print(f"{'parent':<10} {'A_vis':>12} {'B_work':>12} {'ratio':>8} {'outcome':>9} "
          f"{'sec_r':>7} {'wall_r':>7} {'excl_r':>7} {'P5_r':>7}")
    for r in rows:
        print(f"{r['parent']:<10} {r['A_visited']:>12} {r['B_work']:>12} "
              f"{r['work_ratio']:>8.4f} {r['outcome_A']}/{r['outcome_B']:>9} "
              f"{r['seconds_ratio']:>7} {r['wall_ratio']:>7} "
              f"{r['exact_only_visited_ratio']:>7} {r['P5_ratio_10k_over_file']:>7}")


if __name__ == "__main__":
    main()
