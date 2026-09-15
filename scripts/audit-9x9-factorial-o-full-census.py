#!/usr/bin/env python3
"""Audit whether full O finite-population censuses can be reconstructed.

For each O comparison, the design population size is the pre-exclusion
eligible-orbit count (O_at_E0=801, O_at_E1=702). This run solves only the
unobserved eligible census. Historical already-observed parents are joined
only if both required child outcomes are present for the exact two moves.
"""
import csv
from pathlib import Path

# Pre-exclusion design counts from docs/9X9_PAIR_COMPONENT_FACTORIAL_HOLDOUT_DESIGN.md
DESIGN_N = {"O_at_E0": 801, "O_at_E1": 702}
COMP = {
    "O_at_E0": ("diff_O_at_E0", "top_T", "top_TO"),
    "O_at_E1": ("diff_O_at_E1", "top_TE", "top_raw"),
}
HIST_FILES = [
    "results/9x9/pair-vs-true-unique-first12.csv",
    "results/9x9/pair-vs-true-unique-smoke.csv",
]


def truthy(value):
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def normalize(row):
    out = dict(row)
    if "added_child_outcome" not in out and "other_child_outcome" in out:
        out["added_child_outcome"] = out["other_child_outcome"]
    if "added_top" not in out:
        for key in ("other_top", "true_unique_top", "added_top"):
            if key in out:
                out["added_top"] = out[key]
                break
    return out


def main():
    pop = read_csv("artifacts/9x9-factorial-population.csv")
    pop_by = {r["canonical_parent"]: r for r in pop}
    excl = {r["canonical_parent"] for r in read_csv("artifacts/exclusion-canonical-parents.csv")}
    holdout = read_csv("artifacts/9x9-factorial-holdout.csv")
    hold_by = {r["canonical_parent"]: r for r in holdout}

    hist = {}
    for path in HIST_FILES:
        for r in read_csv(path):
            r = normalize(r)
            if "pair_child_outcome" not in r or "added_child_outcome" not in r:
                continue
            parent = r["canonical_parent"]
            hist.setdefault(parent, []).append(
                {
                    "source": path,
                    "pair_top": int(r["pair_top"]),
                    "added_top": int(r["added_top"]),
                    "pair_outcome": r["pair_child_outcome"].strip().upper(),
                    "added_outcome": r["added_child_outcome"].strip().upper(),
                }
            )

    report = {
        "design_n": DESIGN_N,
        "historical_outcome_files": HIST_FILES,
        "historical_parents_with_outcomes": len(hist),
        "comparisons": {},
        "primary_results_unaffected": True,
    }

    for label, (member, left_col, right_col) in COMP.items():
        design_parents = [r["canonical_parent"] for r in pop if truthy(r[member])]
        assert len(design_parents) == DESIGN_N[label], (
            label,
            len(design_parents),
            DESIGN_N[label],
        )
        solved = {
            r["canonical_parent"]: normalize(r)
            for r in read_csv(f"artifacts/solve/merged/{label}.csv")
        }
        excluded_design = [p for p in design_parents if p in excl]
        missing_states = []
        reconstructed = []
        for parent in excluded_design:
            h = pop_by[parent]
            left_move = int(h[left_col])
            right_move = int(h[right_col])
            left_out = right_out = None
            srcs = []
            for rec in hist.get(parent, []):
                pair_move, added_move = rec["pair_top"], rec["added_top"]
                if pair_move == left_move:
                    left_out = rec["pair_outcome"]
                    srcs.append(rec["source"] + ":pair")
                if added_move == left_move:
                    left_out = rec["added_outcome"]
                    srcs.append(rec["source"] + ":added")
                if pair_move == right_move:
                    right_out = rec["pair_outcome"]
                    srcs.append(rec["source"] + ":pair")
                if added_move == right_move:
                    right_out = rec["added_outcome"]
                    srcs.append(rec["source"] + ":added")
            if left_out and right_out:
                reconstructed.append(parent)
            else:
                missing_states.append(
                    {
                        "canonical_parent": parent,
                        "left_move": left_move,
                        "right_move": right_move,
                        "left_outcome": left_out,
                        "right_outcome": right_out,
                        "sources": srcs,
                    }
                )
        report["comparisons"][label] = {
            "design_n": DESIGN_N[label],
            "solved_this_run": len(solved),
            "excluded_from_design": len(excluded_design),
            "excluded_reconstructable": len(reconstructed),
            "excluded_missing_child_outcomes": len(missing_states),
            "full_census_possible": len(missing_states) == 0,
            "missing_states": missing_states,
        }
        print(
            f"{label}: design={DESIGN_N[label]} solved={len(solved)} "
            f"excluded={len(excluded_design)} reconstructable={len(reconstructed)} "
            f"missing={len(missing_states)} full_census={len(missing_states)==0}"
        )

    out = Path("artifacts/solve/o-full-census-reconstruction-audit.json")
    import json

    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
