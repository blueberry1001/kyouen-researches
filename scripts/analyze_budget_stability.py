#!/usr/bin/env python3
"""P4: Compare 10k, 100k, and 1M probe rankings on the original 11 holdout parents.

Reports per-parent and aggregate:
- Spearman and Kendall rank correlations between budgets
- Top-1 agreement rate
- Top-5 overlap (Jaccard)
- LOSS AUC per budget
- First LOSS rank per budget
"""

from __future__ import annotations

import csv
import json
import statistics
import sys
from pathlib import Path
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parents[1]
HOLDOUT_DIR = REPO_ROOT / "results" / "10x10" / "blind-probe-holdout"
OUT_JSON = HOLDOUT_DIR / "budget_stability_analysis.json"
OUT_CSV = HOLDOUT_DIR / "budget_stability_analysis.csv"


def load_probe_csv(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    out = {}
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = (r["parent"], r["state"])
            out[key] = r
    return out


def load_all_exact() -> dict[tuple[str, str], str]:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from analyze_probe_holdout_preregistered import load_parents, load_children, load_exact
    out = {}
    for p in load_parents():
        children = load_children(p)
        exact = load_exact(p)
        for c in children:
            out[(p, c.replace(",", "-"))] = exact[c]
    return out


def norm(s: str) -> str:
    return s.replace(",", "-")


def memo_rank(parent: str, probes: dict[tuple[str, str], dict[str, str]]) -> list[str]:
    items = [(norm(s), int(r["memo"])) for (p, s), r in probes.items() if p == parent]
    seen = set()
    unique = []
    for s, m in items:
        if s not in seen:
            seen.add(s)
            unique.append((s, m))
    unique.sort(key=lambda x: (x[1], x[0]))
    return [s for s, _ in unique]


def top_k_overlap(a: list[str], b: list[str], k: int) -> float:
    set_a = set(a[:k])
    set_b = set(b[:k])
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    return inter / union if union > 0 else 0.0


def auc_from_order(order: list[str], exact: dict[str, str]) -> float | None:
    loss_set = {s for s in order if exact[s] == "LOSS"}
    win_set = {s for s in order if exact[s] == "WIN"}
    if not loss_set or not win_set:
        return None
    loss_ranks = sorted(order.index(s) + 1 for s in loss_set)
    win_ranks = sorted(order.index(s) + 1 for s in win_set)
    n_loss = len(loss_ranks)
    n_win = len(win_ranks)
    # U statistic: number of (loss, win) pairs where loss rank < win rank (LOSS ranked earlier/better)
    u = 0
    j = 0
    for wr in win_ranks:
        while j < n_loss and loss_ranks[j] < wr:
            j += 1
        u += j
    auc = u / (n_loss * n_win)
    return auc


def main():
    probe_10k = load_probe_csv(HOLDOUT_DIR / "independent_probe_10000.csv")
    probe_100k = load_probe_csv(HOLDOUT_DIR / "independent_probe_100000.csv")
    probe_1m = load_probe_csv(HOLDOUT_DIR / "independent_probe_1000000.csv")
    exact = load_all_exact()

    parents = sorted({p for (p, _) in probe_1m})
    budgets = {
        "10k": probe_10k,
        "100k": probe_100k,
        "1M": probe_1m,
    }

    rows = []
    for p in parents:
        order = {b: memo_rank(p, data) for b, data in budgets.items()}
        n = len(order["1M"])

        # Rank correlations
        corr_spear_10_100 = stats.spearmanr(
            [order["10k"].index(s) for s in order["1M"]],
            [order["100k"].index(s) for s in order["1M"]],
        )[0]
        corr_spear_100_1m = stats.spearmanr(
            [order["100k"].index(s) for s in order["1M"]],
            [order["1M"].index(s) for s in order["1M"]],
        )[0]
        corr_spear_10_1m = stats.spearmanr(
            [order["10k"].index(s) for s in order["1M"]],
            [order["1M"].index(s) for s in order["1M"]],
        )[0]

        corr_kend_10_100 = stats.kendalltau(
            [order["10k"].index(s) for s in order["1M"]],
            [order["100k"].index(s) for s in order["1M"]],
        )[0]
        corr_kend_100_1m = stats.kendalltau(
            [order["100k"].index(s) for s in order["1M"]],
            [order["1M"].index(s) for s in order["1M"]],
        )[0]
        corr_kend_10_1m = stats.kendalltau(
            [order["10k"].index(s) for s in order["1M"]],
            [order["1M"].index(s) for s in order["1M"]],
        )[0]

        top1_agree_10_100 = 1 if order["10k"][0] == order["100k"][0] else 0
        top1_agree_100_1m = 1 if order["100k"][0] == order["1M"][0] else 0
        top1_agree_10_1m = 1 if order["10k"][0] == order["1M"][0] else 0

        top5_jacc_10_100 = top_k_overlap(order["10k"], order["100k"], 5)
        top5_jacc_100_1m = top_k_overlap(order["100k"], order["1M"], 5)
        top5_jacc_10_1m = top_k_overlap(order["10k"], order["1M"], 5)

        exact_local = {s: exact[(p, s)] for s in order["1M"]}
        aucs = {b: auc_from_order(order[b], exact_local) for b in budgets}

        first_loss_ranks = {}
        for b in budgets:
            for idx, s in enumerate(order[b], start=1):
                if exact_local[s] == "LOSS":
                    first_loss_ranks[b] = idx
                    break

        rows.append({
            "parent": p,
            "m": n,
            "spearman_10k_100k": corr_spear_10_100,
            "spearman_100k_1M": corr_spear_100_1m,
            "spearman_10k_1M": corr_spear_10_1m,
            "kendall_10k_100k": corr_kend_10_100,
            "kendall_100k_1M": corr_kend_100_1m,
            "kendall_10k_1M": corr_kend_10_1m,
            "top1_agree_10k_100k": top1_agree_10_100,
            "top1_agree_100k_1M": top1_agree_100_1m,
            "top1_agree_10k_1M": top1_agree_10_1m,
            "top5_jaccard_10k_100k": top5_jacc_10_100,
            "top5_jaccard_100k_1M": top5_jacc_100_1m,
            "top5_jaccard_10k_1M": top5_jacc_10_1m,
            "auc_10k": aucs["10k"],
            "auc_100k": aucs["100k"],
            "auc_1M": aucs["1M"],
            "first_loss_rank_10k": first_loss_ranks.get("10k"),
            "first_loss_rank_100k": first_loss_ranks.get("100k"),
            "first_loss_rank_1M": first_loss_ranks.get("1M"),
        })

    summary = {
        "parents": len(rows),
        "mean_spearman": {
            "10k_100k": statistics.mean([r["spearman_10k_100k"] for r in rows]),
            "100k_1M": statistics.mean([r["spearman_100k_1M"] for r in rows]),
            "10k_1M": statistics.mean([r["spearman_10k_1M"] for r in rows]),
        },
        "mean_kendall": {
            "10k_100k": statistics.mean([r["kendall_10k_100k"] for r in rows]),
            "100k_1M": statistics.mean([r["kendall_100k_1M"] for r in rows]),
            "10k_1M": statistics.mean([r["kendall_10k_1M"] for r in rows]),
        },
        "top1_agreement_count": {
            "10k_100k": sum(r["top1_agree_10k_100k"] for r in rows),
            "100k_1M": sum(r["top1_agree_100k_1M"] for r in rows),
            "10k_1M": sum(r["top1_agree_10k_1M"] for r in rows),
        },
        "mean_top5_jaccard": {
            "10k_100k": statistics.mean([r["top5_jaccard_10k_100k"] for r in rows]),
            "100k_1M": statistics.mean([r["top5_jaccard_100k_1M"] for r in rows]),
            "10k_1M": statistics.mean([r["top5_jaccard_10k_1M"] for r in rows]),
        },
        "mean_auc": {
            "10k": statistics.mean([r["auc_10k"] for r in rows if r["auc_10k"] is not None]),
            "100k": statistics.mean([r["auc_100k"] for r in rows if r["auc_100k"] is not None]),
            "1M": statistics.mean([r["auc_1M"] for r in rows if r["auc_1M"] is not None]),
        },
    }

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
