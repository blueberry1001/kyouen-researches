#!/usr/bin/env python3
"""Exact random-order null for the preregistered 10x10 holdout.

This script is committed before holdout probe outcomes are collected. It reads
only the parent-level output of analyze_probe_holdout_preregistered.py and
computes the exact distribution of the sum of first-LOSS ranks under a
uniformly random candidate order for each parent.
"""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "results" / "10x10" / "blind-probe-holdout"
PARENT_CSV = OUT_DIR / "preregistered_parent_results.csv"
OUT_JSON = OUT_DIR / "preregistered_exact_random_null.json"


def first_loss_pmf(m: int, loss: int) -> dict[int, float]:
    if not (1 <= loss <= m):
        raise ValueError((m, loss))
    den = math.comb(m, loss)
    pmf = {
        r: math.comb(m - r, loss - 1) / den
        for r in range(1, m - loss + 2)
    }
    total = sum(pmf.values())
    if abs(total - 1.0) > 1e-12:
        raise AssertionError(f"PMF does not sum to 1: {total}")
    return pmf


def convolve_sum(pmfs: list[dict[int, float]]) -> dict[int, float]:
    dist: dict[int, float] = {0: 1.0}
    for pmf in pmfs:
        nxt: dict[int, float] = defaultdict(float)
        for s, ps in dist.items():
            for r, pr in pmf.items():
                nxt[s + r] += ps * pr
        dist = dict(nxt)
    total = sum(dist.values())
    if abs(total - 1.0) > 1e-10:
        raise AssertionError(f"convolution does not sum to 1: {total}")
    return dist


def main() -> None:
    if not PARENT_CSV.exists():
        raise FileNotFoundError(
            f"missing {PARENT_CSV}; run analyze_probe_holdout_preregistered.py first"
        )
    with PARENT_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise RuntimeError("empty parent results")

    pmfs: list[dict[int, float]] = []
    observed_sum = 0
    expected_sum = 0.0
    parent_parameters = []
    for row in rows:
        m = int(row["m"])
        loss = int(row["loss_children"])
        observed = int(row["corrected_first_loss"])
        pmf = first_loss_pmf(m, loss)
        if observed not in pmf:
            raise RuntimeError(
                f"observed rank outside support for {row['parent']}: "
                f"rank={observed}, m={m}, loss={loss}"
            )
        pmfs.append(pmf)
        observed_sum += observed
        expectation = (m + 1) / (loss + 1)
        expected_sum += expectation
        parent_parameters.append({
            "parent": row["parent"],
            "m": m,
            "loss_children": loss,
            "observed_corrected_first_loss": observed,
            "random_expected_first_loss": expectation,
        })

    dist = convolve_sum(pmfs)
    p_lower = sum(p for s, p in dist.items() if s <= observed_sum)
    p_upper = sum(p for s, p in dist.items() if s >= observed_sum)

    result = {
        "design": "preregistered fresh-memo 1M holdout",
        "test": "exact convolution of parent-specific random first-LOSS ranks",
        "alternative": "corrected rule has smaller summed first-LOSS rank than random order",
        "parents": len(rows),
        "observed_sum_first_loss_rank": observed_sum,
        "random_expected_sum_first_loss_rank": expected_sum,
        "exact_one_sided_p_lower": p_lower,
        "exact_upper_tail_for_reference": p_upper,
        "null_support_min": min(dist),
        "null_support_max": max(dist),
        "parent_parameters": parent_parameters,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
