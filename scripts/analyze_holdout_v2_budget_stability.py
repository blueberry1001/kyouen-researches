#!/usr/bin/env python3
"""P4: compare frozen V2 ranking at 10k, 100k, and primary 1M budgets."""

from __future__ import annotations

import csv
import json
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from analyze_probe_holdout_v2 import corrected_key, first_loss_rank, auc_from_order, load_unique_rows, verify_coverage  # noqa: E402
from holdout_v2_common import legal_children, load_parents, load_tasks  # noqa: E402

ROOT = REPO_ROOT / "results" / "10x10" / "blind-probe-holdout-v2"
SEC = ROOT / "secondary"
OUT_CSV = ROOT / "secondary_budget_stability.csv"
OUT_JSON = ROOT / "secondary_budget_stability_summary.json"


def load_secondary(budget: int) -> dict[tuple[str, str], dict[str, str]]:
    paths = sorted(SEC.glob(f"independent_probe_{budget}_w*-of-*.csv"))
    if not paths:
        raise RuntimeError(f"missing secondary {budget} probe shards")
    out: dict[tuple[str, str], dict[str, str]] = {}
    indices: set[int] = set()
    for path in paths:
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                key = (row["parent"], row["state"].replace("-", ",")); gi = int(row["global_index"])
                if key in out or gi in indices: raise RuntimeError(f"duplicate secondary row: {key} i={gi}")
                out[key] = row; indices.add(gi)
    expected = {(p, s): i for i, (p, _b, _pos, s) in enumerate(load_tasks())}
    if set(out) != set(expected):
        raise RuntimeError(f"secondary {budget} coverage mismatch: missing={len(set(expected)-set(out))} extra={len(set(out)-set(expected))}")
    return out


def main() -> None:
    primary = load_unique_rows("independent_probe_1000000_w*-of-*.csv", "probe_outcome")
    exact = load_unique_rows("exact_outcomes_w*-of-*.csv", "outcome")
    verify_coverage(primary, exact)
    probes = {10_000: load_secondary(10_000), 100_000: load_secondary(100_000), 1_000_000: primary}
    rows: list[dict[str, object]] = []
    for parent in load_parents():
        children = legal_children(parent)
        exact_map = {s: exact[(parent, s)]["outcome"].strip().upper() for s in children}
        item: dict[str, object] = {"parent": parent}
        for budget in (10_000, 100_000, 1_000_000):
            pmap = {s: probes[budget][(parent, s)] for s in children}
            order = sorted(children, key=lambda s: corrected_key(parent, s, pmap[s]))
            item[f"first_loss_{budget}"] = first_loss_rank(order, exact_map)
            item[f"auc_{budget}"] = auc_from_order(order, exact_map)
            item[f"proved_loss_{budget}"] = sum(pmap[s]["probe_outcome"].upper() == "LOSS" for s in children)
            item[f"proved_win_{budget}"] = sum(pmap[s]["probe_outcome"].upper() == "WIN" for s in children)
        item["rank_10k_eq_1m"] = item["first_loss_10000"] == item["first_loss_1000000"]
        item["rank_100k_eq_1m"] = item["first_loss_100000"] == item["first_loss_1000000"]
        rows.append(item)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    summary = {
        "parents": len(rows),
        "rank_10k_equal_1m": sum(bool(r["rank_10k_eq_1m"]) for r in rows),
        "rank_100k_equal_1m": sum(bool(r["rank_100k_eq_1m"]) for r in rows),
        "median_abs_rank_delta_10k_vs_1m": statistics.median(abs(int(r["first_loss_10000"])-int(r["first_loss_1000000"])) for r in rows),
        "median_abs_rank_delta_100k_vs_1m": statistics.median(abs(int(r["first_loss_100000"])-int(r["first_loss_1000000"])) for r in rows),
        "mean_auc_10k": statistics.fmean(float(r["auc_10000"]) for r in rows if r["auc_10000"] is not None),
        "mean_auc_100k": statistics.fmean(float(r["auc_100000"]) for r in rows if r["auc_100000"] is not None),
        "mean_auc_1m": statistics.fmean(float(r["auc_1000000"]) for r in rows if r["auc_1000000"] is not None),
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
