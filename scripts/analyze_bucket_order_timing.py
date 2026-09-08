#!/usr/bin/env python3
"""Preregistered primary/secondary timing analysis for the bucket-order
optimization.

Reads only results/10x10/cache-aware-bucket-order-optimization/
timing_summary.csv (72 fresh runs from this experiment). Computes:

Primary endpoint (frozen):
  T_i = median_seconds_S / median_seconds_B per parent
  PASS iff BOTH: median T over 12 parents > 1
                 AND bucket faster (T_i > 1) on >= 7 of 12 parents

Secondary: parent-level T, median/gmean/mean, faster/tie/slower counts,
aggregate solver seconds and wall seconds, absolute seconds saved,
paired sign test, visited parity check (must be exact equal S/B).
"""
from __future__ import annotations

import csv
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "10x10" / "cache-aware-bucket-order-optimization"
SUMMARY = OUT / "timing_summary.csv"
COHORT = ["0,11,35", "11,38,44", "11,78,87", "12,24,68", "12,32,55",
          "13,52,57", "14,64,74", "23,44,45", "3,47,63", "3,53,84",
          "4,24,26", "4,42,54"]


def fail(msg: str) -> None:
    print(f"TIMING ANALYSIS FAIL: {msg}")
    sys.exit(1)


def main() -> int:
    with SUMMARY.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 72:
        fail(f"expected 72 timing rows, got {len(rows)}")
    per: dict[tuple[str, str], list[dict[str, str]]] = {}
    for r in rows:
        per.setdefault((r["parent"], r["impl"]), []).append(r)
    for (p, impl), runs in per.items():
        if len(runs) != 3:
            fail(f"{p}/{impl}: {len(runs)} runs != 3")
    visited_mismatch = []
    for p in COHORT:
        vs = {r["exact_visited"] for r in per[(p, "sort")]}
        vb = {r["exact_visited"] for r in per[(p, "bucket")]}
        if vs != vb or len(vs) != 1:
            visited_mismatch.append(p)
    if visited_mismatch:
        fail(f"visited parity broken: {visited_mismatch}")

    # Per-parent medians and ratios
    results = []
    for rank, p in enumerate(COHORT, start=1):
        s = sorted(float(r["solver_seconds"]) for r in per[(p, "sort")])
        b = sorted(float(r["solver_seconds"]) for r in per[(p, "bucket")])
        med_s = statistics.median(s)
        med_b = statistics.median(b)
        ratio = med_s / med_b
        ws = sorted(float(r["wall_seconds"]) for r in per[(p, "sort")])
        wb = sorted(float(r["wall_seconds"]) for r in per[(p, "bucket")])
        results.append({
            "rank": rank, "parent": p,
            "seconds_S": s, "seconds_B": b,
            "median_seconds_S": med_s, "median_seconds_B": med_b,
            "wall_S": ws, "wall_B": wb,
            "median_wall_S": statistics.median(ws),
            "median_wall_B": statistics.median(wb),
            "wall_ratio": statistics.median(ws) / statistics.median(wb),
            "T_time": ratio,
            "visited": per[(p, "sort")][0]["exact_visited"],
            "faster": "B" if ratio > 1 else ("S" if ratio < 1 else "tie"),
        })

    ts = [r["T_time"] for r in results]
    med_t = statistics.median(ts)
    gmean_t = math.exp(sum(math.log(t) for t in ts) / len(ts))
    mean_t = sum(ts) / len(ts)
    b_faster = sum(1 for t in ts if t > 1)
    ties = sum(1 for t in ts if t == 1)
    s_faster = sum(1 for t in ts if t < 1)

    # Aggregate seconds
    agg_s = sum(r["median_seconds_S"] for r in results)
    agg_b = sum(r["median_seconds_B"] for r in results)
    agg_wall_s = sum(r["median_wall_S"] for r in results)
    agg_wall_b = sum(r["median_wall_B"] for r in results)

    # Paired sign test on T direction (B faster = +). Two-sided exact
    # binomial over non-ties.
    n_pos = b_faster
    n_neg = s_faster
    n = n_pos + n_neg
    def comb(nn, k):
        return math.comb(nn, k)
    tail = sum(comb(n, k) for k in range(0, min(n_pos, n_neg) + 1))
    p_two = min(1.0, 2.0 * tail / (2 ** n)) if n > 0 else 1.0

    primary_pass = (med_t > 1 and b_faster >= 7)

    report = {
        "experiment": "10x10 cache-aware bucket-order optimization timing",
        "cohort": "C1 original 12 parents (d9b9a0f)",
        "runs": 72,
        "visited_parity": "exact (S==B all 12 parents)",
        "per_parent": [
            {"rank": r["rank"], "parent": r["parent"],
             "median_seconds_S": r["median_seconds_S"],
             "median_seconds_B": r["median_seconds_B"],
             "T_time": r["T_time"],
             "seconds_S": r["seconds_S"], "seconds_B": r["seconds_B"],
             "wall_ratio": r["wall_ratio"],
             "faster": r["faster"], "visited": r["visited"]}
            for r in results],
        "median_T_time": med_t,
        "gmean_T_time": gmean_t,
        "mean_T_time": mean_t,
        "B_faster": b_faster, "ties": ties, "S_faster": s_faster,
        "aggregate_median_seconds_S": agg_s,
        "aggregate_median_seconds_B": agg_b,
        "aggregate_seconds_saved": agg_s - agg_b,
        "aggregate_median_wall_S": agg_wall_s,
        "aggregate_median_wall_B": agg_wall_b,
        "aggregate_wall_saved": agg_wall_s - agg_wall_b,
        "aggregate_solver_time_ratio": agg_s / agg_b,
        "paired_sign_test": {
            "n_positive_B_faster": n_pos, "n_negative_S_faster": n_neg,
            "n_nonzero": n, "p_two_sided_exact_binomial": p_two},
        "primary": {
            "criterion": ["median T_time > 1", "B faster >= 7 of 12"],
            "median_T_time": med_t, "B_faster_count": b_faster,
            "PASS": primary_pass},
    }
    (OUT / "timing_analysis.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")

    print("TIMING ANALYSIS (preregistered primary + secondary)")
    print(f"runs: 72 (12 parents x 2 impls x 3 reps, fresh processes)")
    print(f"visited parity: exact 12/12")
    print()
    hdr = (f"{'rank':>4} {'parent':>9} {'med_S':>9} {'med_B':>9} "
           f"{'T':>8} {'faster':>6}")
    print(hdr)
    for r in results:
        print(f"{r['rank']:>4} {r['parent']:>9} "
              f"{r['median_seconds_S']:>9.3f} {r['median_seconds_B']:>9.3f} "
              f"{r['T_time']:>8.4f} {r['faster']:>6}")
    print()
    print(f"median T = {med_t:.6f}  gmean = {gmean_t:.6f}  mean = {mean_t:.6f}")
    print(f"B faster on {b_faster}/12 (ties {ties}, S faster {s_faster})")
    print(f"aggregate median solver seconds: S={agg_s:.1f} B={agg_b:.1f} "
          f"(saved {agg_s - agg_b:.1f}s, ratio {agg_s / agg_b:.4f})")
    print(f"aggregate median wall seconds:   S={agg_wall_s:.1f} "
          f"B={agg_wall_b:.1f} (saved {agg_wall_s - agg_wall_b:.1f}s)")
    print(f"paired sign test: +{n_pos} -{n_neg} (n={n}), "
          f"p(two-sided)={p_two:.6f}")
    print()
    verdict = "PASS" if primary_pass else "FAIL"
    print(f"PRIMARY ENDPOINT: {verdict} "
          f"(median T {'>' if med_t > 1 else '<='} 1; "
          f"B faster {b_faster}/12 {'>=' if b_faster >= 7 else '<'} 7)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
