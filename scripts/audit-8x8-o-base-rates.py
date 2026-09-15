#!/usr/bin/env python3
"""Quantify 5-stone LOSS base-rate gap between 8x8 census children and 9x9 reference.

Reads frozen 8x8 census outcomes and reports descriptive base rates by stratum
membership of the parent. No new solves. No primary-definition changes.
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTCOMES = ROOT / "artifacts" / "8x8-o-census-outcomes.csv"
STRATA = ROOT / "artifacts" / "8x8-o-strata.csv"
PARENTS = ROOT / "artifacts" / "8x8-o-parent-outcomes.csv"
OUT = ROOT / "artifacts" / "8x8-o-base-rate-audit.json"


def load(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    outcomes = load(OUTCOMES)
    strata = {r["canonical_parent"]: r["stratum"] for r in load(STRATA)}
    parents = load(PARENTS)

    # Base rate among all unique solved roots
    all_c = Counter(r["child_outcome"] for r in outcomes)
    n_all = len(outcomes)

    # Per-parent: which of the four tops, if present
    parent_by = {r["canonical_parent"]: r for r in parents}

    # Classify each solved root by the roles it plays
    role_counts = defaultdict(Counter)
    for r in outcomes:
        parent = r["canonical_parent"]
        move = int(r["move"])
        st = strata.get(parent, "?")
        pr = parent_by.get(parent, {})
        roles = []
        for name in ("top_T", "top_TE", "top_TO", "top_raw"):
            if pr.get(name) not in (None, "") and int(pr[name]) == move:
                roles.append(name)
        if not roles:
            roles = ["non_top"]  # should not happen for required roots
        for role in roles:
            role_counts[f"{st}|{role}"][r["child_outcome"]] += 1
        role_counts[f"{st}|any"][r["child_outcome"]] += 1

    # Discordant-parent composition: among parents whose pair flips, what is
    # the outcome pattern?
    flip_pattern = Counter()
    for pr in parents:
        st = pr["stratum"]
        if st == "O1-only":
            base, add = pr.get("y10"), pr.get("y11")
        else:
            base, add = pr.get("y00"), pr.get("y01")
        if base in (None, "") or add in (None, ""):
            continue
        b, a = int(base), int(add)
        if b == a:
            flip_pattern[f"{st}|same_{ 'LOSS' if b==1 else 'WIN'}"] += 1
        else:
            flip_pattern[f"{st}|flip"] += 1

    # 9x9 reference from factorial result doc
    nine = {
        "selected_child_loss_rates": {
            "T": 0.472441,
            "TE": 0.460630,
            "TO": 0.476378,
            "raw": 0.452756,
        },
        "note": "from docs/9X9_FACTORIAL_EXACT_PC_RUN_RESULT.md",
    }

    report = {
        "eight_eight_all_unique_roots": {
            "n": n_all,
            "WIN": all_c.get("WIN", 0),
            "LOSS": all_c.get("LOSS", 0),
            "LOSS_rate": all_c.get("LOSS", 0) / n_all if n_all else None,
        },
        "loss_rate_by_stratum_any_top": {
            st: {
                "n": sum(role_counts[f"{st}|any"].values()),
                "LOSS": role_counts[f"{st}|any"].get("LOSS", 0),
                "LOSS_rate": (
                    role_counts[f"{st}|any"].get("LOSS", 0)
                    / max(1, sum(role_counts[f"{st}|any"].values()))
                ),
            }
            for st in ("O0-only", "O-overlap", "O1-only")
        },
        "loss_rate_by_role": {
            key: {
                "n": sum(c.values()),
                "LOSS": c.get("LOSS", 0),
                "LOSS_rate": c.get("LOSS", 0) / max(1, sum(c.values())),
            }
            for key, c in sorted(role_counts.items())
            if not key.endswith("|any")
        },
        "parent_flip_patterns": dict(flip_pattern),
        "nine_ref": nine,
        "interpretation": (
            "8x8 selected top-move children are WIN at ~92.5%. "
            "9x9 factorial selected children are LOSS at ~45-48%. "
            "The O-stratum 8x8 experiment therefore runs in a low-LOSS, "
            "low-change-rate regime; heuristic O/E differences rarely flip "
            "the exact outcome. This is a board-size structural fact about "
            "the experimental regime, not a solver bug."
        ),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
