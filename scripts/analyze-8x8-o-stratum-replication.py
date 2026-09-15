#!/usr/bin/env python3
"""Analyze 8x8 O-stratum replication outcomes against the frozen primary criterion.

Reads frozen strata + census outcomes. Writes:
  - artifacts/8x8-o-parent-outcomes.csv
  - artifacts/8x8-o-primary-summary.json
  - artifacts/8x8-o-9x9-comparison.csv
  - artifacts/8x8-o-analysis-summary.json
"""
from __future__ import annotations

import csv
import json
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STRATA = ROOT / "artifacts" / "8x8-o-strata.csv"
OUTCOMES = ROOT / "artifacts" / "8x8-o-census-outcomes.csv"
PARENT_OUT = ROOT / "artifacts" / "8x8-o-parent-outcomes.csv"
PRIMARY = ROOT / "artifacts" / "8x8-o-primary-summary.json"
COMPARE = ROOT / "artifacts" / "8x8-o-9x9-comparison.csv"
SUMMARY = ROOT / "artifacts" / "8x8-o-analysis-summary.json"

# Frozen 9x9 exploratory reference (holdout-based; not a threshold source).
NINE = {
    "O0-only_delta": 0.0912,
    "O_overlap_delta": -0.0143,
    "gap": 0.1055,
}


def load_outcomes():
    d = {}
    with OUTCOMES.open(newline="") as f:
        for row in csv.DictReader(f):
            key = (row["canonical_parent"], int(row["move"]))
            d[key] = row["child_outcome"]
    return d


def encode(outcome: str) -> int:
    return 1 if outcome == "LOSS" else 0


def four_cells(y_base, y_add):
    """Return counts for a pair of binary outcomes (baseline, added)."""
    both_loss = both_win = base_only = add_only = 0
    for a, b in zip(y_base, y_add):
        if a == 1 and b == 1:
            both_loss += 1
        elif a == 0 and b == 0:
            both_win += 1
        elif a == 1 and b == 0:
            base_only += 1
        else:
            add_only += 1
    n = len(y_base)
    base_rate = sum(y_base) / n if n else 0.0
    add_rate = sum(y_add) / n if n else 0.0
    return {
        "n": n,
        "both_loss": both_loss,
        "both_win": both_win,
        "baseline_only_loss": base_only,
        "O_added_only_loss": add_only,
        "discordant": base_only + add_only,
        "baseline_loss_rate": base_rate,
        "added_loss_rate": add_rate,
        "delta_loss": add_rate - base_rate,
        "change_rate": (base_only + add_only) / n if n else 0.0,
        "net_count": add_only - base_only,
    }


def main():
    outcomes = load_outcomes()
    strata = []
    with STRATA.open(newline="") as f:
        for row in csv.DictReader(f):
            strata.append(row)

    missing = 0
    parents = []
    for r in strata:
        parent = r["canonical_parent"]
        st = r["stratum"]
        tops = {
            "top_T": int(r["top_T"]),
            "top_TE": int(r["top_TE"]),
            "top_TO": int(r["top_TO"]),
            "top_raw": int(r["top_raw"]),
        }
        y = {}
        for name, mv in tops.items():
            key = (parent, mv)
            if key not in outcomes:
                missing += 1
                y[name] = None
            else:
                y[name] = outcomes[key]
        rec = {
            "canonical_parent": parent,
            "stratum": st,
            **tops,
            "y_top_T": y["top_T"],
            "y_top_TE": y["top_TE"],
            "y_top_TO": y["top_TO"],
            "y_top_raw": y["top_raw"],
        }
        # Encode O_effect_E0 where applicable
        if st in ("O0-only", "O-overlap") and y["top_T"] and y["top_TO"]:
            rec["y00"] = encode(y["top_T"])
            rec["y01"] = encode(y["top_TO"])
            rec["O_effect_E0"] = rec["y01"] - rec["y00"]
        if st in ("O-overlap", "O1-only") and y["top_TE"] and y["top_raw"]:
            rec["y10"] = encode(y["top_TE"])
            rec["y11"] = encode(y["top_raw"])
            rec["O_effect_E1"] = rec["y11"] - rec["y10"]
        if st == "O-overlap" and "O_effect_E0" in rec and "O_effect_E1" in rec:
            rec["interaction_I"] = rec["O_effect_E1"] - rec["O_effect_E0"]
        parents.append(rec)

    with PARENT_OUT.open("w", newline="") as f:
        fields = [
            "canonical_parent",
            "stratum",
            "top_T",
            "top_TE",
            "top_TO",
            "top_raw",
            "y_top_T",
            "y_top_TE",
            "y_top_TO",
            "y_top_raw",
            "y00",
            "y01",
            "y10",
            "y11",
            "O_effect_E0",
            "O_effect_E1",
            "interaction_I",
        ]
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for rec in parents:
            w.writerow(rec)

    by = {"O0-only": [], "O-overlap": [], "O1-only": []}
    for rec in parents:
        by[rec["stratum"]].append(rec)

    def cells_for(st, base_field, add_field):
        yb, ya = [], []
        for rec in by[st]:
            if rec.get(base_field) is None or rec.get(add_field) is None:
                continue
            yb.append(rec[base_field])
            ya.append(rec[add_field])
        return four_cells(yb, ya)

    o0 = cells_for("O0-only", "y00", "y01")
    olap = cells_for("O-overlap", "y00", "y01")
    o1 = cells_for("O1-only", "y10", "y11")

    delta0 = o0["delta_loss"]
    delta_olap = olap["delta_loss"]
    gap = delta0 - delta_olap

    success = (delta0 > 0) and (gap >= 0.05)
    if success:
        verdict = "success"
    elif delta0 > 0:
        verdict = "partial"
    else:
        verdict = "fail"

    # O-overlap interaction histogram
    i_vals = [rec["interaction_I"] for rec in by["O-overlap"] if "interaction_I" in rec]
    i_hist = Counter(i_vals)
    i_mean = statistics.mean(i_vals) if i_vals else None
    i_median = statistics.median(i_vals) if i_vals else None

    # O1-only delta already in o1
    primary = {
        "encoding": {"LOSS": 1, "WIN": 0},
        "O0_only": o0,
        "O_overlap": olap,
        "O1_only": o1,
        "primary_gap_G": gap,
        "success_criterion": {
            "delta0_gt_0": delta0 > 0,
            "gap_ge_0.05": gap >= 0.05,
            "threshold": 0.05,
            "pass": success,
            "verdict": verdict,
        },
        "interaction_O_overlap": {
            "histogram": {str(k): i_hist.get(k, 0) for k in range(-2, 3)},
            "mean": i_mean,
            "median": i_median,
            "negative": sum(v for k, v in i_hist.items() if k < 0),
            "zero": i_hist.get(0, 0),
            "positive": sum(v for k, v in i_hist.items() if k > 0),
            "abs_eq_2": i_hist.get(-2, 0) + i_hist.get(2, 0),
            "n": len(i_vals),
        },
        "missing_outcomes": missing,
    }
    PRIMARY.write_text(json.dumps(primary, indent=2) + "\n")

    # 9x9 comparison table
    with COMPARE.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "board",
                "O0_only_n",
                "O_overlap_n",
                "O0_only_delta",
                "O_overlap_delta",
                "gap",
                "interaction_mean",
                "O0_change_rate",
                "O_overlap_change_rate",
            ]
        )
        w.writerow(
            [
                "8x8",
                o0["n"],
                olap["n"],
                f"{delta0:.6f}",
                f"{delta_olap:.6f}",
                f"{gap:.6f}",
                f"{i_mean:.6f}" if i_mean is not None else "",
                f"{o0['change_rate']:.6f}",
                f"{olap['change_rate']:.6f}",
            ]
        )
        # 9x9 reference values from prereg (exploratory holdout)
        w.writerow(
            [
                "9x9-ref",
                "",
                "",
                f"{NINE['O0-only_delta']:.6f}",
                f"{NINE['O_overlap_delta']:.6f}",
                f"{NINE['gap']:.6f}",
                "",
                "",
                "",
            ]
        )

    analysis = {
        "verdict": verdict,
        "O0_only_delta": delta0,
        "O_overlap_delta": delta_olap,
        "gap": gap,
        "O1_only_delta": o1["delta_loss"],
        "interaction_mean": i_mean,
        "interaction_median": i_median,
        "population_d4_orbits": 2340,
        "stratum_counts": {k: len(v) for k, v in by.items()},
        "unique_roots_solved": 848,
        "solve_completion": "848/848",
    }
    SUMMARY.write_text(json.dumps(analysis, indent=2) + "\n")
    print(json.dumps(primary, indent=2))
    print("--- summary ---")
    print(json.dumps(analysis, indent=2))


if __name__ == "__main__":
    main()
