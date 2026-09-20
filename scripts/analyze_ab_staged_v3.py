#!/usr/bin/env python3
"""Evaluate AB staged-V3 root-order benchmark against frozen gates."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "results" / "10x10" / "ab-staged-v3-root"

N = 16
IMPROVED_MIN = 13
WORST_MAX = 2.0


def median(xs: list[float]) -> float:
    ys = sorted(xs)
    n = len(ys)
    if n == 0:
        return float("nan")
    mid = n // 2
    return float(ys[mid] if n % 2 else (ys[mid - 1] + ys[mid]) / 2)


def geom_mean(xs: list[float]) -> float:
    if not xs:
        return float("nan")
    return math.exp(sum(math.log(x) for x in xs) / len(xs))


def sign_test_one_sided(improved: int, worse: int) -> float:
    """Exact one-sided sign test: P(X >= improved | n=improved+worse, p=0.5)."""
    n = improved + worse
    if n == 0:
        return 1.0
    # sum_{k=improved..n} C(n,k) / 2^n
    total = 0
    for k in range(improved, n + 1):
        total += math.comb(n, k)
    return total / (2 ** n)


def main() -> None:
    raw = list(csv.DictReader((OUT / "ab_exact_raw.csv").open(newline="", encoding="utf-8")))
    by: dict[str, dict[str, dict[str, str]]] = {}
    for r in raw:
        by.setdefault(r["parent"], {})[r["strategy"]] = r

    rank_rows = list(csv.DictReader((OUT / "top11_rank_1m.csv").open(newline="", encoding="utf-8")))
    first_loss_rank: dict[str, int | None] = {}
    for parent in sorted({r["parent"] for r in rank_rows}):
        rows = [r for r in rank_rows if r["parent"] == parent]
        # This rank is among shortlist only (not exact). Exact first-loss is
        # determined from root_entered after labels — use entered as proxy.
        first_loss_rank[parent] = None

    parent_rows = []
    mismatches = []
    for parent in sorted(by):
        a = by[parent].get("A")
        b = by[parent].get("B")
        if a is None or b is None:
            raise RuntimeError(f"missing strategy for {parent}")
        if a["outcome"] != b["outcome"]:
            mismatches.append((parent, a["outcome"], b["outcome"]))

        a_vis = int(a["exact_visited"])
        b_exact = int(b["exact_visited"])
        p10 = int(b["probe10k_visited"])
        p1m = int(b["probe1m_visited"])
        probe_vis = p10 + p1m
        b_total = probe_vis + b_exact
        ratio = b_total / a_vis if a_vis else float("inf")
        exact_only_ratio = b_exact / a_vis if a_vis else float("inf")
        probe_overhead_ratio = probe_vis / a_vis if a_vis else float("inf")

        a_sec = float(a["exact_seconds"])
        b_sec = float(b["exact_seconds"]) + float(b["probe_seconds_total"])
        sec_ratio = b_sec / a_sec if a_sec else float("inf")

        parent_rows.append(
            {
                "parent": parent,
                "a_outcome": a["outcome"],
                "b_outcome": b["outcome"],
                "a_exact_visited": a_vis,
                "b_exact_visited": b_exact,
                "probe10k_visited": p10,
                "probe1m_visited": p1m,
                "probe_visited_total": probe_vis,
                "b_total_visited": b_total,
                "visited_ratio": ratio,
                "exact_only_ratio": exact_only_ratio,
                "probe_overhead_ratio": probe_overhead_ratio,
                "a_entered": int(a["root_entered"]),
                "b_entered": int(b["root_entered"]),
                "a_unique": int(a["root_unique"]),
                "b_unique": int(b["root_unique"]),
                "a_seconds": a_sec,
                "b_probe_seconds": float(b["probe_seconds_total"]),
                "b_exact_seconds": float(b["exact_seconds"]),
                "b_total_seconds": b_sec,
                "seconds_ratio": sec_ratio,
                "a_wall": float(a["wall_seconds"]),
                "b_wall": float(b["wall_seconds"]),
                "a_memo": int(a["exact_memo"]),
                "b_memo": int(b["exact_memo"]),
            }
        )

    fields = list(parent_rows[0].keys())
    with (OUT / "parent_summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(parent_rows)

    ratios = [r["visited_ratio"] for r in parent_rows]
    exact_ratios = [r["exact_only_ratio"] for r in parent_rows]
    sec_ratios = [r["seconds_ratio"] for r in parent_rows]
    improved = sum(1 for r in parent_rows if r["visited_ratio"] < 1.0)
    tied = sum(1 for r in parent_rows if r["visited_ratio"] == 1.0)
    worse = sum(1 for r in parent_rows if r["visited_ratio"] > 1.0)
    worst = max(ratios)
    agg_ratio = sum(r["b_total_visited"] for r in parent_rows) / sum(r["a_exact_visited"] for r in parent_rows)
    agg_exact_ratio = sum(r["b_exact_visited"] for r in parent_rows) / sum(r["a_exact_visited"] for r in parent_rows)
    agg_probe = sum(r["probe_visited_total"] for r in parent_rows)
    agg_a = sum(r["a_exact_visited"] for r in parent_rows)
    agg_b_exact = sum(r["b_exact_visited"] for r in parent_rows)

    correctness = len(mismatches) == 0 and len(parent_rows) == N
    gates = {
        "correctness_16_of_16": correctness,
        "aggregate_ratio_lt_1": agg_ratio < 1.0,
        "median_ratio_lt_1": median(ratios) < 1.0,
        "improved_parents_ge_13": improved >= IMPROVED_MIN,
        "worst_ratio_le_2": worst <= WORST_MAX,
    }
    confirmatory_success = all(gates.values())

    summary = {
        "n_parents": len(parent_rows),
        "correctness": {
            "outcome_agreement": f"{len(parent_rows) - len(mismatches)}/{len(parent_rows)}",
            "mismatches": mismatches,
            "pass": correctness,
        },
        "primary_visited": {
            "aggregate_ratio": agg_ratio,
            "median_ratio": median(ratios),
            "gmean_ratio": geom_mean(ratios),
            "improved": improved,
            "tied": tied,
            "worse": worse,
            "worst_ratio": worst,
            "sign_test_one_sided_p": sign_test_one_sided(improved, worse),
            "aggregate_a_visited": agg_a,
            "aggregate_b_exact_visited": agg_b_exact,
            "aggregate_probe_visited": agg_probe,
            "aggregate_b_total_visited": agg_b_exact + agg_probe,
            "aggregate_exact_only_ratio": agg_exact_ratio,
            "probe_overhead_share_of_A": agg_probe / agg_a,
        },
        "secondary_seconds": {
            "median_ratio": median(sec_ratios),
            "aggregate_ratio": sum(r["b_total_seconds"] for r in parent_rows)
            / sum(r["a_seconds"] for r in parent_rows),
        },
        "gates": gates,
        "confirmatory_success": confirmatory_success,
        "verdict": (
            "CONFIRMATORY SUCCESS (probe-inclusive end-to-end)"
            if confirmatory_success
            else (
                "CORRECTNESS PASS; PERFORMANCE FAIL"
                if correctness
                else "CORRECTNESS FAIL — performance invalid"
            )
        ),
        "per_parent_ratios": {r["parent"]: r["visited_ratio"] for r in parent_rows},
    }
    (OUT / "aggregate_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print("=== AB staged-V3 root-order evaluation ===")
    print(f"parents: {len(parent_rows)}")
    print(f"correctness: {summary['correctness']['outcome_agreement']}")
    print(f"aggregate visited ratio: {agg_ratio:.4f}")
    print(f"median visited ratio:    {median(ratios):.4f}")
    print(f"gmean visited ratio:     {geom_mean(ratios):.4f}")
    print(f"improved/tied/worse:     {improved}/{tied}/{worse}  (need >={IMPROVED_MIN} improved)")
    print(f"worst ratio:             {worst:.4f}  (need <= {WORST_MAX})")
    print(f"sign test one-sided p:   {summary['primary_visited']['sign_test_one_sided_p']:.6f}")
    print(f"aggregate exact-only:    {agg_exact_ratio:.4f}")
    print(f"probe overhead / A:      {agg_probe/agg_a:.4f}")
    print(f"median seconds ratio:    {median(sec_ratios):.4f}")
    print(f"gates: {gates}")
    print(f"VERDICT: {summary['verdict']}")
    print()
    print(f"{'parent':<12} {'A_vis':>12} {'B_exact':>12} {'probe':>12} {'B_total':>12} {'ratio':>8} {'exOnly':>8} {'entA':>5} {'entB':>5}")
    for r in parent_rows:
        print(
            f"{r['parent']:<12} {r['a_exact_visited']:>12} {r['b_exact_visited']:>12} "
            f"{r['probe_visited_total']:>12} {r['b_total_visited']:>12} {r['visited_ratio']:>8.3f} "
            f"{r['exact_only_ratio']:>8.3f} {r['a_entered']:>5} {r['b_entered']:>5}"
        )


if __name__ == "__main__":
    main()
