#!/usr/bin/env python3
import csv
from pathlib import Path

SRC = Path("results/10x10/parent-benchmark/parent_benchmark_results.csv")
OUT = Path("results/10x10/parent-benchmark/parent_strategy_switch_headroom.txt")

rows = list(csv.DictReader(SRC.open(newline="", encoding="utf-8")))
for r in rows:
    r["A"] = int(r["A_visited"])
    r["B"] = int(r["B_work"])
    r["gain"] = max(r["A"] - r["B"], 0)
    r["ratio"] = r["B"] / r["A"]

sum_a = sum(r["A"] for r in rows)
sum_b = sum(r["B"] for r in rows)
sum_best = sum(min(r["A"], r["B"]) for r in rows)
total_gain = sum(r["gain"] for r in rows)
b_wins = [r for r in rows if r["B"] < r["A"]]

lines = [
    "Parent-level native(A) vs 10k-order(B) switch headroom",
    f"parents={len(rows)}",
    f"sum_A_visited={sum_a}",
    f"sum_B_work={sum_b}",
    f"sum_oracle_best={sum_best}",
    f"oracle_best_over_A={sum_best / sum_a:.6f}",
    f"oracle_improvement_vs_A={(sum_a - sum_best) / sum_a:.6%}",
    f"B_wins={len(b_wins)}/{len(rows)}",
    "",
    "B-winning parents:",
]
for r in sorted(b_wins, key=lambda x: -x["gain"]):
    share = r["gain"] / total_gain if total_gain else 0.0
    lines.append(
        f"  {r['parent']}: A={r['A']} B={r['B']} "
        f"B/A={r['ratio']:.6f} gain={r['gain']} share_of_oracle_gain={share:.6%} "
        f"A_entered={r['A_entered']} B_entered={r['B_entered']}"
    )

if b_wins:
    biggest = max(b_wins, key=lambda x: x["gain"])
    lines += [
        "",
        f"largest_gain_parent={biggest['parent']}",
        f"largest_gain_share={biggest['gain'] / total_gain:.6%}",
    ]

OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
