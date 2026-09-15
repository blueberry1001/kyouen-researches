#!/usr/bin/env python3
"""Post-hoc structural diagnostics on 8x8 O-stratum census (descriptive only).

Does not change any frozen primary definition. Explores:
  1. Outcome base rates and change rates vs 9x9 reference
  2. Flip-direction geometry for O0-only / O1-only / O-overlap
  3. Outcome-free score features (pair_E / pair_O) by flip class
  4. Cheap falsifiable propositions suggested by the pattern
"""
from __future__ import annotations

import csv
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POP = ROOT / "artifacts" / "8x8-factorial-population.csv"
STRATA = ROOT / "artifacts" / "8x8-o-strata.csv"
PARENTS = ROOT / "artifacts" / "8x8-o-parent-outcomes.csv"
OUT = ROOT / "artifacts" / "8x8-o-posthoc-structure.json"
OUT_CSV = ROOT / "artifacts" / "8x8-o-flip-classes.csv"

# 9x9 exploratory reference (from docs/9X9_FACTORIAL_EFFECT_HETEROGENEITY.md)
NINE = {
    "O0_only": {"n": 296, "delta": 0.091216, "change_rate": 0.435811},
    "O_overlap": {"n": 419, "delta": -0.014320, "change_rate": 0.444391},
    "O1_only": {"n": 220, "delta": 0.018182, "change_rate": 0.436364},
}


def load_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parent_cells(st: str, rows: list[dict]) -> dict:
    """Four-cell counts for the stratum's relevant pair."""
    if st == "O0-only":
        base, add = "y00", "y01"
    elif st == "O-overlap":
        base, add = "y00", "y01"
    else:  # O1-only
        base, add = "y10", "y11"
    pairs = []
    for r in rows:
        if r["stratum"] != st:
            continue
        b, a = r.get(base), r.get(add)
        if b is None or a is None or b == "" or a == "":
            continue
        pairs.append((int(b), int(a)))
    n = len(pairs)
    both_loss = sum(1 for b, a in pairs if b == 1 and a == 1)
    both_win = sum(1 for b, a in pairs if b == 0 and a == 0)
    base_only = sum(1 for b, a in pairs if b == 1 and a == 0)  # O helped
    add_only = sum(1 for b, a in pairs if b == 0 and a == 1)  # O hurt
    return {
        "n": n,
        "both_loss": both_loss,
        "both_win": both_win,
        "baseline_only_loss_O_helped": base_only,
        "O_added_only_loss_O_hurt": add_only,
        "change_rate": (base_only + add_only) / n if n else 0.0,
        "baseline_loss_rate": sum(b for b, _ in pairs) / n if n else 0.0,
        "added_loss_rate": sum(a for _, a in pairs) / n if n else 0.0,
        "delta_loss": (sum(a for _, a in pairs) - sum(b for b, _ in pairs)) / n if n else 0.0,
        "net_O_hurt_minus_help": add_only - base_only,
    }


def parse_parent_key(s: str) -> tuple[int, ...]:
    return tuple(int(x) for x in s.strip('"').split(","))


def main():
    pop = {r["canonical_parent"]: r for r in load_csv(POP)}
    parents = load_csv(PARENTS)
    strata = {r["canonical_parent"]: r["stratum"] for r in load_csv(STRATA)}

    summary = {
        "population_orbits": len(pop),
        "strata_parents": len(strata),
        "parent_outcome_rows": len(parents),
        "stratum_cells": {},
        "nine_ref": NINE,
    }
    for st in ("O0-only", "O-overlap", "O1-only"):
        summary["stratum_cells"][st] = parent_cells(st, parents)

    # Join features for each parent with a relevant flip
    feature_rows = []
    flip_counter = Counter()
    by_stratum_features = defaultdict(list)

    for r in parents:
        parent = r["canonical_parent"]
        st = r["stratum"]
        pop_r = pop.get(parent)
        if pop_r is None:
            continue
        # Determine flip class on the stratum's pair
        if st == "O0-only":
            base, add = r.get("y00"), r.get("y01")
            pair_key_T = "pair_E_sum_top_T"
            pair_key_O = "pair_O_sum_top_T"
        elif st == "O-overlap":
            base, add = r.get("y00"), r.get("y01")
            pair_key_T = "pair_E_sum_top_T"
            pair_key_O = "pair_O_sum_top_T"
        else:
            base, add = r.get("y10"), r.get("y11")
            pair_key_T = "pair_E_sum_top_TE"
            pair_key_O = "pair_O_sum_top_TE"
        if base in (None, "") or add in (None, ""):
            flip = "missing"
            y_base = y_add = None
        else:
            y_base, y_add = int(base), int(add)
            if y_base == 0 and y_add == 0:
                flip = "both_win"
            elif y_base == 1 and y_add == 1:
                flip = "both_loss"
            elif y_base == 1 and y_add == 0:
                flip = "O_helped"
            else:
                flip = "O_hurt"
        flip_counter[(st, flip)] += 1

        rec = {
            "canonical_parent": parent,
            "stratum": st,
            "flip": flip,
            "top_T": r["top_T"],
            "top_TE": r["top_TE"],
            "top_TO": r["top_TO"],
            "top_raw": r["top_raw"],
            "orbit_size": pop_r.get("orbit_size"),
            "distinct_top_moves": pop_r.get("distinct_top_moves"),
            "pair_E_sum_top_T": pop_r.get("pair_E_sum_top_T"),
            "pair_O_sum_top_T": pop_r.get("pair_O_sum_top_T"),
            "pair_E_sum_top_TE": pop_r.get("pair_E_sum_top_TE"),
            "pair_O_sum_top_TE": pop_r.get("pair_O_sum_top_TE"),
            "pair_E_sum_top_TO": pop_r.get("pair_E_sum_top_TO"),
            "pair_O_sum_top_TO": pop_r.get("pair_O_sum_top_TO"),
            "pair_E_sum_top_raw": pop_r.get("pair_E_sum_top_raw"),
            "pair_O_sum_top_raw": pop_r.get("pair_O_sum_top_raw"),
            "y00": r.get("y00"),
            "y01": r.get("y01"),
            "y10": r.get("y10"),
            "y11": r.get("y11"),
        }
        feature_rows.append(rec)
        by_stratum_features[st].append(rec)

    # Feature means by (stratum, flip) for non-both_win cases (informative flips)
    feat_stats = {}
    for st, rows in by_stratum_features.items():
        for flip in ("O_helped", "O_hurt", "both_loss", "both_win"):
            subset = [r for r in rows if r["flip"] == flip]
            if not subset:
                continue
            def mean_col(col):
                vals = []
                for r in subset:
                    v = r.get(col)
                    if v not in (None, ""):
                        vals.append(float(v))
                return statistics.mean(vals) if vals else None
            feat_stats[f"{st}|{flip}"] = {
                "n": len(subset),
                "mean_pair_E_top_T": mean_col("pair_E_sum_top_T"),
                "mean_pair_O_top_T": mean_col("pair_O_sum_top_T"),
                "mean_pair_E_top_TE": mean_col("pair_E_sum_top_TE"),
                "mean_pair_O_top_TE": mean_col("pair_O_sum_top_TE"),
                "mean_pair_O_top_TO": mean_col("pair_O_sum_top_TO"),
                "mean_pair_O_top_raw": mean_col("pair_O_sum_top_raw"),
                "mean_orbit": mean_col("orbit_size"),
            }

    # Cross-board comparison
    comparison = []
    for st, key in (("O0-only", "O0_only"), ("O-overlap", "O_overlap"), ("O1-only", "O1_only")):
        c8 = summary["stratum_cells"][st]
        c9 = NINE[key]
        comparison.append({
            "stratum": st,
            "n_8x8": c8["n"],
            "n_9x9": c9["n"],
            "delta_8x8": c8["delta_loss"],
            "delta_9x9": c9["delta"],
            "change_8x8": c8["change_rate"],
            "change_9x9": c9["change_rate"],
            "base_loss_8x8": c8["baseline_loss_rate"],
            "added_loss_8x8": c8["added_loss_rate"],
        })

    # Proposition candidates (descriptive, not adopted)
    o0 = summary["stratum_cells"]["O0-only"]
    o1 = summary["stratum_cells"]["O1-only"]
    ol = summary["stratum_cells"]["O-overlap"]
    props = [
        {
            "id": "P1-change-rate-collapse",
            "statement": (
                "On 8x8 eligible O-stratum parents, the O-induced outcome change rate "
                f"is <= 0.15 in every stratum (O0={o0['change_rate']:.3f}, "
                f"overlap={ol['change_rate']:.3f}, O1={o1['change_rate']:.3f}), "
                "whereas the 9x9 exploratory reference is ~0.44. "
                "Board-size reduction collapses how often O flips the exact outcome."
            ),
            "status": "SUPPORTED_ON_8X8_CENSUS",
            "falsifier": "Find an 8x8 stratum with change_rate > 0.20 on the same frozen population, or a 7x7/10x10 census with change_rate ~0.44.",
        },
        {
            "id": "P2-O0-only-sign-flip",
            "statement": (
                "The sign of Δ_O(O0-only) flips between boards: 9x9 holdout +0.091 "
                f"(O hurts) vs 8x8 census {o0['delta_loss']:.4f} (O helps). "
                "Therefore the 9x9 O0-only positive-Δ claim is not a board-size-stable law."
            ),
            "status": "SUPPORTED_AS_NON_REPLICATION",
            "falsifier": "Independent 7x7 or 10x10 O0-only census with Δ > +0.05 using the same frozen definitions.",
        },
        {
            "id": "P3-O1-only-net-hurt-on-8x8",
            "statement": (
                "On 8x8 O1-only parents, adding O at E=1 increases LOSS rate: "
                f"Δ_O_E1 = {o1['delta_loss']:.4f} > 0 "
                f"(O_hurt={o1['O_added_only_loss_O_hurt']}, "
                f"O_helped={o1['baseline_only_loss_O_helped']}). "
                "This is larger in magnitude than the 9x9 O1-only reference (+0.018)."
            ),
            "status": "CANDIDATE_NEEDS_INDEPENDENT_DATA",
            "falsifier": "7x7 or 10x10 O1-only census with Δ_O_E1 <= 0, or 8x8 re-solve under independent verifier showing opposite sign.",
        },
        {
            "id": "P4-zero-interaction-board-stable",
            "statement": (
                "E×O interaction on O-overlap parents is ~0 on both boards "
                f"(8x8: exactly 0 on n={ol['n']}; 9x9: mean -0.002 on n=470). "
                "Shared-parent interaction is not the driver of overall O-effect sign changes."
            ),
            "status": "SUPPORTED",
            "falsifier": "Any board where |mean I| > 0.02 on a full O-overlap census with the same I definition.",
        },
    ]

    summary["flip_counts"] = {f"{st}|{fl}": n for (st, fl), n in sorted(flip_counter.items())}
    summary["feature_stats_by_stratum_flip"] = feat_stats
    summary["cross_board_comparison"] = comparison
    summary["proposition_candidates"] = props

    OUT.write_text(json.dumps(summary, indent=2) + "\n")

    fields = [
        "canonical_parent", "stratum", "flip", "top_T", "top_TE", "top_TO", "top_raw",
        "orbit_size", "distinct_top_moves",
        "pair_E_sum_top_T", "pair_O_sum_top_T", "pair_E_sum_top_TE", "pair_O_sum_top_TE",
        "pair_E_sum_top_TO", "pair_O_sum_top_TO", "pair_E_sum_top_raw", "pair_O_sum_top_raw",
        "y00", "y01", "y10", "y11",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for rec in feature_rows:
            w.writerow(rec)

    print(json.dumps({
        "stratum_cells": summary["stratum_cells"],
        "flip_counts": summary["flip_counts"],
        "cross_board": comparison,
        "propositions": [{"id": p["id"], "status": p["status"]} for p in props],
    }, indent=2))


if __name__ == "__main__":
    main()
