#!/usr/bin/env python3
"""Analyze proof cost *conditional on exact LOSS* in the frozen V2 cohort.

No solver runs are performed.  Inputs are the completed V2 child-level exact
outcomes, frozen 10k probes, and completed parent benchmark raw rows.

Main question: does a heuristic select a cheap LOSS witness, not merely a LOSS?
"""
from __future__ import annotations

import csv
import itertools
import math
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "results" / "10x10" / "clean-holdout-v2"
BENCH = ROOT / "results" / "10x10" / "parent-benchmark"

# Reuse exactly the determinant predicate used by the V2 task generator.
import sys
sys.path.insert(0, str(ROOT / "scripts"))
from generate_v2_holdout_children import forbidden  # noqa: E402


def norm_state(s: str) -> str:
    return "-".join(str(x) for x in sorted(int(v) for v in s.replace(",", "-").split("-") if v != ""))


def pts_of(s: str) -> tuple[int, ...]:
    return tuple(int(v) for v in norm_state(s).split("-"))


def d4_point(p: int, k: int) -> int:
    x, y = p % 10, p // 10
    nx = (x, 9-x, x, 9-x, y, 9-y, y, 9-y)
    ny = (y, y, 9-y, 9-y, x, x, 9-x, 9-x)
    return ny[k] * 10 + nx[k]


def bits_key(points: tuple[int, ...]) -> tuple[int, int]:
    lo = hi = 0
    for p in points:
        if p < 64:
            lo |= 1 << p
        else:
            hi |= 1 << (p - 64)
    return lo, hi


def canonical_bits(state: str) -> tuple[int, int]:
    pts = pts_of(state)
    keys = [bits_key(tuple(sorted(d4_point(p, k) for p in pts))) for k in range(8)]
    # C++ Bits::operator< compares hi first, then lo.
    return min(keys, key=lambda z: (z[1], z[0]))


def legal_move_count(state: str) -> int:
    pts = pts_of(state)
    assert len(pts) == 4
    n = 0
    pset = set(pts)
    for v in range(100):
        if v in pset:
            continue
        if not any(forbidden(*trio, v) for trio in itertools.combinations(pts, 3)):
            n += 1
    return n


def rankdata(xs: list[float]) -> list[float]:
    order = sorted(range(len(xs)), key=xs.__getitem__)
    out = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and xs[order[j]] == xs[order[i]]:
            j += 1
        rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            out[order[k]] = rank
        i = j
    return out


def pearson(x: list[float], y: list[float]) -> float:
    if len(x) < 2:
        return float("nan")
    mx, my = statistics.mean(x), statistics.mean(y)
    dx = [a - mx for a in x]
    dy = [b - my for b in y]
    den = math.sqrt(sum(a*a for a in dx) * sum(b*b for b in dy))
    return sum(a*b for a, b in zip(dx, dy)) / den if den else float("nan")


def spearman(x: list[float], y: list[float]) -> float:
    return pearson(rankdata(x), rankdata(y))


def main() -> None:
    exact = {}
    with (V2 / "exact_outcomes.csv").open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            exact[(r["parent"].strip(), norm_state(r["state"]))] = r

    probes = {}
    with (V2 / "independent_probe_10000.csv").open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            probes[(r["parent"].strip(), norm_state(r["state"]))] = r

    bench = {}
    with (BENCH / "parent_benchmark_raw.csv").open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            bench[(r["parent"], r["strategy"])] = r

    by_parent: dict[str, list[dict]] = defaultdict(list)
    for (p, s), er in exact.items():
        if er["outcome"].strip().upper() != "LOSS":
            continue
        pr = probes[(p, s)]
        lo, hi = canonical_bits(s)
        by_parent[p].append({
            "state": s,
            "visited": int(er["visited"]),
            "seconds": float(er["seconds"]),
            "memo10k": int(pr["memo"]),
            "legal": legal_move_count(s),
            "lo": lo,
            "hi": hi,
        })

    rows = []
    for p in sorted(by_parent):
        losses = by_parent[p]
        costs = [x["visited"] for x in losses]
        legal = [x["legal"] for x in losses]
        memo = [x["memo10k"] for x in losses]
        cheapest = min(costs)

        selected = {}
        for strategy in ("A", "B"):
            br = bench[(p, strategy)]
            key = (int(br["root_first_lo"]), int(br["root_first_hi"]))
            hit = [x for x in losses if (x["lo"], x["hi"]) == key]
            # If the first entered child is not LOSS, no selected-LOSS cost is
            # attributed here; that condition required >1 root entry.
            selected[strategy] = hit[0] if len(hit) == 1 else None

        rec = {
            "parent": p,
            "n_loss": len(losses),
            "rho_legal_vs_loss_visited": spearman(legal, costs),
            "rho_memo10k_vs_loss_visited": spearman(memo, costs),
            "cheapest_loss_visited": cheapest,
        }
        for strategy in ("A", "B"):
            x = selected[strategy]
            if x is None:
                rec[f"{strategy}_first_is_loss"] = 0
                rec[f"{strategy}_selected_loss_visited"] = ""
                rec[f"{strategy}_selected_loss_cost_rank"] = ""
                rec[f"{strategy}_selected_over_cheapest"] = ""
            else:
                rec[f"{strategy}_first_is_loss"] = 1
                rec[f"{strategy}_selected_loss_visited"] = x["visited"]
                rec[f"{strategy}_selected_loss_cost_rank"] = 1 + sum(c < x["visited"] for c in costs)
                rec[f"{strategy}_selected_over_cheapest"] = x["visited"] / cheapest
        rows.append(rec)

    fields = list(rows[0].keys())
    out = BENCH / "loss_proof_cost_analysis.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print("== conditional LOSS proof-cost analysis ==")
    print(f"parents={len(rows)} exact_loss_children={sum(r['n_loss'] for r in rows)}")
    for name in ("rho_legal_vs_loss_visited", "rho_memo10k_vs_loss_visited"):
        vals = [float(r[name]) for r in rows if not math.isnan(float(r[name]))]
        print(f"median_{name}={statistics.median(vals):.4f}")
    for strategy in ("A", "B"):
        ratios = [float(r[f"{strategy}_selected_over_cheapest"]) for r in rows
                  if r[f"{strategy}_selected_over_cheapest"] != ""]
        ranks = [int(r[f"{strategy}_selected_loss_cost_rank"]) for r in rows
                 if r[f"{strategy}_selected_loss_cost_rank"] != ""]
        print(f"{strategy}_first_is_loss={len(ratios)}/{len(rows)}")
        if ratios:
            print(f"{strategy}_selected_over_cheapest_median={statistics.median(ratios):.4f}")
            print(f"{strategy}_selected_loss_cost_rank_median={statistics.median(ranks):.2f}")
            print(f"{strategy}_selected_cheapest_count={sum(r == 1 for r in ranks)}/{len(ranks)}")

    print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
