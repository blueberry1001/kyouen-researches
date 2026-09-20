#!/usr/bin/env python3
"""Nested leave-one-parent-out analysis for exact LOSS proof cost.

Goal:
  Test whether one cheap child-geometry feature adds useful information beyond
  legal_move_count when choosing a cheap-to-prove LOSS child.

The outer held-out parent is never used either to fit coefficients or to choose
which extra feature is used. Feature selection is done by an inner
leave-one-parent-out loop over the remaining parents.

This is intentionally exploratory on the current dataset. Any feature/rule
suggested by this script should be frozen and tested on new LOSS parents before
being treated as confirmed.
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path
from statistics import median

DEFAULT_DATA = Path("results/10x10/parent-benchmark/loss_proof_cost_dataset.csv")

# Pre-solver quantities only. banned_child is intentionally excluded because
# on these 4-stone children it is largely the complement of legal_move_count.
CANDIDATES = (
    "newly_banned",
    "raw_pair_sum",
    "T_union_new",
    "move_cdist",
    "pairdist_mean",
    "pairdist_min",
    "bbox_area",
    "n_rows",
    "n_cols",
)

EPS = 1e-12


def load_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    numeric = {"exact_visited", "legal_move_count", *CANDIDATES}
    for row in rows:
        for col in numeric:
            row[col] = float(row[col])
    return rows


def group_by_parent(rows):
    out = defaultdict(list)
    for row in rows:
        out[row["parent"]].append(row)
    return dict(out)


def percentile_ranks(values):
    """Average-tie ranks scaled to [0,1]; lower original value -> lower rank."""
    n = len(values)
    if n <= 1:
        return [0.0] * n
    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    p = 0
    while p < n:
        q = p + 1
        v = values[order[p]]
        while q < n and values[order[q]] == v:
            q += 1
        avg = (p + q - 1) / 2.0
        for k in range(p, q):
            ranks[order[k]] = avg / (n - 1)
        p = q
    return ranks


def make_ranked(groups):
    ranked = {}
    for parent, rows in groups.items():
        legal = percentile_ranks([r["legal_move_count"] for r in rows])
        target = percentile_ranks([r["exact_visited"] for r in rows])
        feats = {c: percentile_ranks([r[c] for r in rows]) for c in CANDIDATES}
        rr = []
        for i, row in enumerate(rows):
            x = dict(row)
            x["_legal_rank"] = legal[i]
            x["_target_rank"] = target[i]
            for c in CANDIDATES:
                x[f"_{c}_rank"] = feats[c][i]
            rr.append(x)
        ranked[parent] = rr
    return ranked


def solve3(a, b):
    """Solve a 3x3 linear system with Gaussian elimination; None if singular."""
    m = [list(a[i]) + [b[i]] for i in range(3)]
    for col in range(3):
        pivot = max(range(col, 3), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < 1e-10:
            return None
        m[col], m[pivot] = m[pivot], m[col]
        div = m[col][col]
        for j in range(col, 4):
            m[col][j] /= div
        for r in range(3):
            if r == col:
                continue
            fac = m[r][col]
            for j in range(col, 4):
                m[r][j] -= fac * m[col][j]
    return [m[i][3] for i in range(3)]


def fit_feature(ranked, train_parents, feature):
    """Parent-balanced WLS: target_rank ~ 1 + legal_rank + feature_rank."""
    xtx = [[0.0] * 3 for _ in range(3)]
    xty = [0.0] * 3
    for parent in train_parents:
        rows = ranked[parent]
        w = 1.0 / len(rows)
        for r in rows:
            x = [1.0, r["_legal_rank"], r[f"_{feature}_rank"]]
            y = r["_target_rank"]
            for i in range(3):
                xty[i] += w * x[i] * y
                for j in range(3):
                    xtx[i][j] += w * x[i] * x[j]
    return solve3(xtx, xty)


def selected_ratio(rows, score):
    chosen = min(rows, key=lambda r: (score(r), r["key"]))
    oracle = min(r["exact_visited"] for r in rows)
    return chosen["exact_visited"] / oracle, chosen


def legal_result(rows):
    return selected_ratio(rows, lambda r: r["legal_move_count"])


def model_result(rows, feature, beta):
    return selected_ratio(
        rows,
        lambda r: beta[0] + beta[1] * r["_legal_rank"] + beta[2] * r[f"_{feature}_rank"],
    )


def summary_metric(ratios):
    # Fixed lexicographic objective: median first, then mean log ratio.
    return (median(ratios), sum(math.log(max(x, EPS)) for x in ratios) / len(ratios))


def inner_choose_feature(ranked, train_parents):
    scores = {}
    for feature in CANDIDATES:
        ratios = []
        valid = True
        for inner_hold in train_parents:
            inner_train = [p for p in train_parents if p != inner_hold]
            beta = fit_feature(ranked, inner_train, feature)
            if beta is None:
                valid = False
                break
            ratio, _ = model_result(ranked[inner_hold], feature, beta)
            ratios.append(ratio)
        if valid:
            scores[feature] = (summary_metric(ratios), ratios)
    if not scores:
        return None, {}
    best = min(scores, key=lambda f: (scores[f][0], f))
    return best, scores


def run_nested(ranked):
    parents = sorted(ranked)
    outer = []
    for hold in parents:
        train = [p for p in parents if p != hold]
        feature, _inner_scores = inner_choose_feature(ranked, train)
        if feature is None:
            raise RuntimeError(f"No nonsingular feature for outer holdout {hold}")
        beta = fit_feature(ranked, train, feature)
        if beta is None:
            raise RuntimeError("Unexpected singular final fit")
        model_ratio, model_child = model_result(ranked[hold], feature, beta)
        legal_ratio, legal_child = legal_result(ranked[hold])
        outer.append(
            {
                "parent": hold,
                "feature": feature,
                "legal_ratio": legal_ratio,
                "model_ratio": model_ratio,
                "legal_key": legal_child["key"],
                "model_key": model_child["key"],
                "beta_feature": beta[2],
            }
        )
    return outer


def run_fixed_features(ranked):
    """Exploratory per-feature LOPO; fixed-feature ranking is not confirmatory."""
    parents = sorted(ranked)
    result = {}
    for feature in CANDIDATES:
        ratios = []
        usable = True
        for hold in parents:
            train = [p for p in parents if p != hold]
            beta = fit_feature(ranked, train, feature)
            if beta is None:
                usable = False
                break
            ratio, _ = model_result(ranked[hold], feature, beta)
            ratios.append(ratio)
        if usable:
            result[feature] = ratios
    return result


def fmt(x):
    return f"{x:.4f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA)
    args = ap.parse_args()

    rows = load_rows(args.data)
    groups = group_by_parent(rows)
    ranked = make_ranked(groups)
    parents = sorted(ranked)
    if len(parents) < 4:
        raise SystemExit("Need at least 4 parents for nested parent-level validation")

    outer = run_nested(ranked)
    legal_ratios = [r["legal_ratio"] for r in outer]
    model_ratios = [r["model_ratio"] for r in outer]
    improved = sum(m < b - 1e-12 for b, m in zip(legal_ratios, model_ratios))
    tied = sum(abs(m - b) <= 1e-12 for b, m in zip(legal_ratios, model_ratios))
    worse = len(outer) - improved - tied

    print(f"rows={len(rows)} parents={len(parents)}")
    print("NESTED_LOPO (outer parent untouched during feature selection)")
    print(
        "legal median_ratio=" + fmt(median(legal_ratios))
        + " nested_one_feature median_ratio=" + fmt(median(model_ratios))
    )
    print(f"outer improved/tied/worse={improved}/{tied}/{worse}")
    print()
    print("parent\tchosen_feature\tlegal_ratio\tmodel_ratio\tfeature_coef")
    for r in outer:
        print(
            f'{r["parent"]}\t{r["feature"]}\t{fmt(r["legal_ratio"])}\t'
            f'{fmt(r["model_ratio"])}\t{fmt(r["beta_feature"])}'
        )

    print()
    print("EXPLORATORY_FIXED_FEATURE_LOPO")
    fixed = run_fixed_features(ranked)
    ranked_features = sorted(fixed, key=lambda f: (summary_metric(fixed[f]), f))
    for f in ranked_features:
        rs = fixed[f]
        imp = sum(r < b - 1e-12 for r, b in zip(rs, legal_ratios))
        tie = sum(abs(r - b) <= 1e-12 for r, b in zip(rs, legal_ratios))
        print(
            f"{f}\tmedian={fmt(median(rs))}\t"
            f"mean_log={fmt(summary_metric(rs)[1])}\t"
            f"vs_legal improved/tied/worse={imp}/{tie}/{len(rs)-imp-tie}"
        )

    print()
    print("Interpretation rule:")
    print("- Nested LOPO is the generalization check for 'add one cheap feature'.")
    print(
        "- Fixed-feature ranking is exploratory only; freeze any proposed "
        "feature/rule before testing on new LOSS parents."
    )


if __name__ == "__main__":
    main()
