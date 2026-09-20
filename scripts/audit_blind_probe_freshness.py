#!/usr/bin/env python3
"""Audit blind-validation probe CSVs for cross-child Solver state carry-over.

The fixed 3-stone rule uses final memo size.  That feature is only meaningful
across children if each child starts from a fresh Solver.  This audit rejects
probe files whose memo is cumulative across rows.
"""
from __future__ import annotations

import csv
import glob
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "results" / "10x10" / "blind_probe_children"
PAT = re.compile(r"probe_(.+)_batch(\d+)_(\d+)\.csv$")


def rankdata(xs):
    order = sorted(range(len(xs)), key=lambda i: (xs[i], i))
    rank = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and xs[order[j]] == xs[order[i]]:
            j += 1
        r = (i + j - 1) / 2 + 1
        for k in range(i, j):
            rank[order[k]] = r
        i = j
    return rank


def pearson(a, b):
    if len(a) < 2:
        return float("nan")
    ma = sum(a) / len(a); mb = sum(b) / len(b)
    da = [x - ma for x in a]; db = [x - mb for x in b]
    num = sum(x*y for x, y in zip(da, db))
    den = (sum(x*x for x in da) * sum(y*y for y in db)) ** 0.5
    return num / den if den else float("nan")


def main():
    bad = 0
    print("file,rows,budget,memo_first,memo_last,spearman_index_memo,cumulative_signature")
    for name in sorted(glob.glob(str(DIR / "probe_*_batch*_*.csv"))):
        p = Path(name)
        m = PAT.search(p.name)
        if not m:
            continue
        budget = int(m.group(3))
        with p.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if not rows or "memo" not in rows[0]:
            continue
        memo = [int(r["memo"]) for r in rows]
        visited = [int(r["visited"]) for r in rows]
        rho = pearson(rankdata(list(range(len(rows)))), rankdata(memo))
        # Strong evidence of reuse: each row spends roughly one budget, while
        # final memo grows well beyond one-child scale and is nearly monotone.
        roughly_budgeted = sum(v >= 0.95 * budget for v in visited) >= max(1, int(0.8 * len(rows)))
        near_monotone = sum(memo[i] >= memo[i-1] for i in range(1, len(memo))) >= max(0, len(memo)-2)
        grows_past_single = max(memo) > 1.5 * budget
        cumulative = bool(len(rows) >= 3 and roughly_budgeted and near_monotone and grows_past_single and rho > 0.9)
        bad += cumulative
        print(f"{p.name},{len(rows)},{budget},{memo[0]},{memo[-1]},{rho:.6f},{int(cumulative)}")
    if bad:
        raise SystemExit(f"FAIL: {bad} probe file(s) show cumulative memo; rankings using absolute memo are invalid")
    print("PASS: no cumulative-memo signature detected")


if __name__ == "__main__":
    main()
