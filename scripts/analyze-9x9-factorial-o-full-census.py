#!/usr/bin/env python3
"""Reconstruct full O finite-population census (801 / 702) and full 2x2 stats.

Joins frozen holdout census results with newly solved missing children.
Secondary / descriptive only. No new p-values.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import Counter
from pathlib import Path


def truthy(x) -> bool:
    return str(x).strip().lower() in {"1", "true", "yes", "y"}


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def outcome01(x) -> int:
    token = str(x).strip().upper()
    if token == "LOSS":
        return 1
    if token == "WIN":
        return 0
    raise SystemExit(f"bad outcome: {x!r}")


def normalize_result(row: dict) -> dict:
    out = dict(row)
    if "added_child_outcome" not in out and "other_child_outcome" in out:
        out["added_child_outcome"] = out["other_child_outcome"]
    if "added_top" not in out:
        for key in ("other_top", "true_unique_top", "added_top"):
            if key in out and out[key] != "":
                out["added_top"] = out[key]
                break
    return out


def right_move(row: dict) -> int:
    for col in ("added_top", "other_top", "true_unique_top"):
        if col in row and row[col] != "":
            return int(row[col])
    raise SystemExit("result row lacks added/other_top")


COMP = {
    "O_at_E0": ("diff_O_at_E0", "top_T", "top_TO"),
    "O_at_E1": ("diff_O_at_E1", "top_TE", "top_raw"),
}
DESIGN_N = {"O_at_E0": 801, "O_at_E1": 702}


def summarize_pairs(pairs: list[tuple[int, int]]) -> dict:
    n = len(pairs)
    both_loss = both_win = left_only = right_only = 0
    for left, right in pairs:
        if left == 1 and right == 1:
            both_loss += 1
        elif left == 0 and right == 0:
            both_win += 1
        elif left == 1 and right == 0:
            left_only += 1
        else:
            right_only += 1
    base = (both_loss + left_only) / n if n else float("nan")
    added = (both_loss + right_only) / n if n else float("nan")
    return {
        "n": n,
        "both_loss": both_loss,
        "both_win": both_win,
        "baseline_only_loss": left_only,
        "added_only_loss": right_only,
        "discordant": left_only + right_only,
        "baseline_loss_rate": base,
        "added_loss_rate": added,
        "delta_loss_rate": added - base,
        "change_rate": (left_only + right_only) / n if n else float("nan"),
        "net_count": right_only - left_only,
    }


def pattern_bits(h: dict) -> dict:
    tops = {
        "top_T": int(h["top_T"]),
        "top_TE": int(h["top_TE"]),
        "top_TO": int(h["top_TO"]),
        "top_raw": int(h["top_raw"]),
    }
    return {
        **tops,
        "diff_E_at_O0": int(h["diff_E_at_O0"]),
        "diff_O_at_E0": int(h["diff_O_at_E0"]),
        "diff_E_at_O1": int(h["diff_E_at_O1"]),
        "diff_O_at_E1": int(h["diff_O_at_E1"]),
        "distinct_moves": len(set(tops.values())),
        "top_T_eq_top_TO": int(tops["top_T"] == tops["top_TO"]),
        "top_TE_eq_top_raw": int(tops["top_TE"] == tops["top_raw"]),
        "top_T_eq_top_TE": int(tops["top_T"] == tops["top_TE"]),
        "top_TO_eq_top_raw": int(tops["top_TO"] == tops["top_raw"]),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout", default="artifacts/9x9-factorial-holdout.csv")
    ap.add_argument("--population", default="artifacts/9x9-factorial-population.csv")
    ap.add_argument("--gap", default="artifacts/9x9-pair-gap-population.csv")
    ap.add_argument("--O_at_E0", default="artifacts/solve/merged/O_at_E0.csv")
    ap.add_argument("--O_at_E1", default="artifacts/solve/merged/O_at_E1.csv")
    ap.add_argument("--E_at_O0", default="artifacts/solve/merged/E_at_O0.csv")
    ap.add_argument("--E_at_O1", default="artifacts/solve/merged/E_at_O1.csv")
    ap.add_argument(
        "--missing-children",
        default="artifacts/solve/o-missing-unique-children.out.csv",
    )
    ap.add_argument(
        "--outdir", default="results/9x9/factorial/effect-heterogeneity"
    )
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    hold = read_csv(Path(args.holdout))
    hold_by = {r["canonical_parent"]: r for r in hold}
    pop = read_csv(Path(args.population))
    pop_by = {r["canonical_parent"]: r for r in pop}
    gap_by = {}
    gap_path = Path(args.gap)
    if gap_path.exists():
        gap_by = {r["canonical_parent"]: r for r in read_csv(gap_path)}

    # Design parents from population flags (pre-exclusion finite population).
    design = {}
    for label, (member, left_col, right_col) in COMP.items():
        parents = [r["canonical_parent"] for r in pop if truthy(r[member])]
        if len(parents) != DESIGN_N[label]:
            raise SystemExit(
                f"{label}: design {len(parents)} != {DESIGN_N[label]}"
            )
        design[label] = parents

    frozen = {
        label: {
            r["canonical_parent"]: normalize_result(r)
            for r in read_csv(Path(path))
        }
        for label, path in {
            "O_at_E0": args.O_at_E0,
            "O_at_E1": args.O_at_E1,
            "E_at_O0": args.E_at_O0,
            "E_at_O1": args.E_at_O1,
        }.items()
    }

    missing_children = {
        (r["canonical_parent"], int(r["move"])): r["child_outcome"].strip().upper()
        for r in read_csv(Path(args.missing_children))
    }

    # Build full O pair outcomes for every design parent.
    full_pairs = {}
    full_rows = []
    missing_fail = []
    for label, parents in design.items():
        left_col, right_col = COMP[label][1], COMP[label][2]
        pairs = []
        for parent in parents:
            h = pop_by[parent]
            left = int(h[left_col])
            right = int(h[right_col])
            if parent in frozen[label]:
                r = frozen[label][parent]
                if int(r["pair_top"]) != left or right_move(r) != right:
                    raise SystemExit(f"{label} move mismatch frozen {parent}")
                lo = r["pair_child_outcome"].strip().upper()
                ro = r["added_child_outcome"].strip().upper()
                source = "holdout_census"
            else:
                lo = missing_children.get((parent, left))
                ro = missing_children.get((parent, right))
                source = "missing_exact_solve"
                if lo is None or ro is None:
                    missing_fail.append((label, parent, lo, ro))
                    continue
            pairs.append((outcome01(lo), outcome01(ro)))
            full_rows.append(
                {
                    "comparison": label,
                    "canonical_parent": parent,
                    "left_move": left,
                    "right_move": right,
                    "left_outcome": lo,
                    "right_outcome": ro,
                    "source": source,
                    "y_left": outcome01(lo),
                    "y_right": outcome01(ro),
                }
            )
        full_pairs[label] = pairs

    if missing_fail:
        raise SystemExit(f"still missing {len(missing_fail)} e.g. {missing_fail[:3]}")

    full_census = {label: summarize_pairs(pairs) for label, pairs in full_pairs.items()}

    # Compare with unobserved holdout census.
    holdout_census = {}
    for label, parents in design.items():
        left_col, right_col = COMP[label][1], COMP[label][2]
        pairs = []
        for parent in parents:
            if parent not in frozen[label]:
                continue
            r = frozen[label][parent]
            pairs.append(
                (
                    outcome01(r["pair_child_outcome"]),
                    outcome01(r["added_child_outcome"]),
                )
            )
        holdout_census[label] = summarize_pairs(pairs)

    # ---- full 2x2 interaction on parents with all four O outcomes ----
    # y00 top_T, y01 top_TO from O_at_E0; y10 top_TE, y11 top_raw from O_at_E1.
    o0_full = {}
    o1_full = {}
    for row in full_rows:
        if row["comparison"] == "O_at_E0":
            o0_full[row["canonical_parent"]] = row
        else:
            o1_full[row["canonical_parent"]] = row

    # Also pull E sample outcomes for interaction completeness where available.
    e0_map = {p: normalize_result(r) for p, r in frozen["E_at_O0"].items()}
    e1_map = {p: normalize_result(r) for p, r in frozen["E_at_O1"].items()}

    complete = []
    i_vals = []
    i_hist = Counter()
    for parent in sorted(set(o0_full) & set(o1_full)):
        a = o0_full[parent]
        b = o1_full[parent]
        y00 = a["y_left"]
        y01 = a["y_right"]
        y10 = b["y_left"]
        y11 = b["y_right"]
        I = y11 - y01 - y10 + y00
        if I not in (-2, -1, 0, 1, 2):
            raise SystemExit(f"bad I={I} for {parent}")
        i_hist[I] += 1
        i_vals.append(I)
        h = hold_by.get(parent) or pop_by[parent]
        rec = {
            "canonical_parent": parent,
            "y00_T": y00,
            "y01_TO": y01,
            "y10_TE": y10,
            "y11_raw": y11,
            "O_effect_E0": y01 - y00,
            "O_effect_E1": y11 - y10,
            "interaction": I,
            "in_holdout_census_O0": int(parent in frozen["O_at_E0"]),
            "in_holdout_census_O1": int(parent in frozen["O_at_E1"]),
        }
        rec.update(pattern_bits(h))
        g = gap_by.get(parent, {})
        for k in (
            "cause_class",
            "pair_T",
            "pair_E",
            "pair_O",
            "pair_raw",
            "true_T",
            "true_E",
            "true_O",
            "true_raw",
        ):
            rec[k] = g.get(k, "")
        complete.append(rec)

    # Direction flips on full 4-outcome set.
    flips = []
    for rec in complete:
        o_e0, o_e1 = rec["O_effect_E0"], rec["O_effect_E1"]
        cls = (
            "A_improve_then_worsen"
            if o_e0 < 0 and o_e1 > 0
            else "B_worsen_then_improve"
            if o_e0 > 0 and o_e1 < 0
            else "none"
        )
        rec_o = dict(rec)
        rec_o["O_flip_class"] = cls
        # E effects if available
        p = rec["canonical_parent"]
        if p in e0_map and p in e1_map:
            r0, r1 = e0_map[p], e1_map[p]
            ee0 = outcome01(r0["added_child_outcome"]) - outcome01(
                r0["pair_child_outcome"]
            )
            ee1 = outcome01(r1["added_child_outcome"]) - outcome01(
                r1["pair_child_outcome"]
            )
            rec_o["E_effect_O0"] = ee0
            rec_o["E_effect_O1"] = ee1
            rec_o["E_interaction"] = ee1 - ee0
            rec_o["E_flip_class"] = (
                "C_improve_then_worsen"
                if ee0 < 0 and ee1 > 0
                else "D_worsen_then_improve"
                if ee0 > 0 and ee1 < 0
                else "none"
            )
        else:
            rec_o["E_effect_O0"] = ""
            rec_o["E_effect_O1"] = ""
            rec_o["E_interaction"] = ""
            rec_o["E_flip_class"] = "not_in_E_intersection"
        flips.append(rec_o)

    # Structural comparison of newly solved vs holdout census O parents.
    def struct_summary(rows: list[dict]) -> dict:
        keys = [
            "diff_E_at_O0",
            "diff_O_at_E0",
            "diff_E_at_O1",
            "diff_O_at_E1",
            "distinct_moves",
            "top_T_eq_top_TO",
            "top_TE_eq_top_raw",
            "top_T_eq_top_TE",
            "top_TO_eq_top_raw",
        ]
        out = {"n": len(rows)}
        for k in keys:
            vals = [r[k] for r in rows]
            out[f"mean_{k}"] = sum(vals) / len(vals) if vals else None
        return out

    holdout_o0_parents = set(frozen["O_at_E0"])
    holdout_o1_parents = set(frozen["O_at_E1"])
    newly_solved_o0 = [p for p in design["O_at_E0"] if p not in holdout_o0_parents]
    newly_solved_o1 = [p for p in design["O_at_E1"] if p not in holdout_o1_parents]

    def parent_struct(parents: list[str]) -> list[dict]:
        rows = []
        for p in parents:
            h = hold_by.get(p) or pop_by[p]
            rec = {"canonical_parent": p}
            rec.update(pattern_bits(h))
            rows.append(rec)
        return rows

    structural = {
        "holdout_O0": struct_summary(parent_struct(list(holdout_o0_parents))),
        "newly_solved_O0": struct_summary(parent_struct(newly_solved_o0)),
        "holdout_O1": struct_summary(parent_struct(list(holdout_o1_parents))),
        "newly_solved_O1": struct_summary(parent_struct(newly_solved_o1)),
    }

    # write artifacts
    def write_csv(path: Path, rows: list[dict]) -> None:
        if not rows:
            path.write_text("", encoding="utf-8")
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    write_csv(outdir / "o-full-census-parents.csv", full_rows)
    write_csv(outdir / "o-full-4outcome.csv", complete)
    write_csv(outdir / "o-full-direction-flips.csv", flips)

    census_rows = []
    for label in ("O_at_E0", "O_at_E1"):
        c = full_census[label]
        h = holdout_census[label]
        census_rows.append(
            {
                "comparison": label,
                "population_type": "full_pre_exclusion_finite_census",
                **c,
                "holdout_unobserved_n": h["n"],
                "holdout_unobserved_delta": h["delta_loss_rate"],
                "holdout_unobserved_change_rate": h["change_rate"],
                "delta_minus_holdout_delta": c["delta_loss_rate"]
                - h["delta_loss_rate"],
            }
        )
    write_csv(outdir / "o-full-census-summary.csv", census_rows)

    def take(cls_field: str, cls: str, n: int = 20) -> list[dict]:
        sel = [r for r in flips if r[cls_field] == cls]
        sel.sort(
            key=lambda r: (
                abs(int(r.get("interaction") or 0)),
                abs(int(r.get("E_interaction") or 0))
                if r.get("E_interaction") != ""
                else 0,
                r["canonical_parent"],
            )
        )
        return sel[:n]

    def take_near(i_field: str, n: int = 20) -> list[dict]:
        sel = []
        for r in flips:
            raw = r.get(i_field)
            if raw == "" or raw is None:
                continue
            if int(raw) != 0:
                sel.append(r)
        sel.sort(
            key=lambda r: (-abs(int(r[i_field])), r["canonical_parent"])
        )
        return sel[:n]

    examples = {
        "A_O_improve_E0_worsen_E1": take("O_flip_class", "A_improve_then_worsen"),
        "B_O_worsen_E0_improve_E1": take("O_flip_class", "B_worsen_then_improve"),
        "C_E_improve_O0_worsen_O1": take("E_flip_class", "C_improve_then_worsen"),
        "D_E_worsen_O0_improve_O1": take("E_flip_class", "D_worsen_then_improve"),
        "O_near_nonzero_interaction": take_near("interaction"),
        "E_near_nonzero_interaction": take_near("E_interaction"),
    }
    for name, rows in examples.items():
        write_csv(outdir / f"examples-full-{name}.csv", rows)

    report = {
        "analysis_type": "secondary_descriptive_full_census",
        "new_p_values": False,
        "primary_holm_unchanged": True,
        "design_n": DESIGN_N,
        "missing_unique_children_solved": len(missing_children),
        "newly_solved_parents": {
            "O_at_E0": len(newly_solved_o0),
            "O_at_E1": len(newly_solved_o1),
        },
        "full_census": full_census,
        "holdout_unobserved_census": holdout_census,
        "delta_comparison": {
            label: {
                "full_delta": full_census[label]["delta_loss_rate"],
                "holdout_delta": holdout_census[label]["delta_loss_rate"],
                "diff": full_census[label]["delta_loss_rate"]
                - holdout_census[label]["delta_loss_rate"],
                "full_change_rate": full_census[label]["change_rate"],
                "holdout_change_rate": holdout_census[label]["change_rate"],
            }
            for label in DESIGN_N
        },
        "four_outcome_complete_n": len(complete),
        "interaction_histogram": {str(k): i_hist[k] for k in (-2, -1, 0, 1, 2)},
        "mean_I": statistics.mean(i_vals) if i_vals else None,
        "median_I": statistics.median(i_vals) if i_vals else None,
        "I_lt_0": i_hist[-2] + i_hist[-1],
        "I_eq_0": i_hist[0],
        "I_gt_0": i_hist[1] + i_hist[2],
        "abs_I_eq_2": i_hist[-2] + i_hist[2],
        "structural": structural,
        "counterexample_counts": {
            "A": sum(r["O_flip_class"] == "A_improve_then_worsen" for r in flips),
            "B": sum(r["O_flip_class"] == "B_worsen_then_improve" for r in flips),
            "C": sum(r.get("E_flip_class") == "C_improve_then_worsen" for r in flips),
            "D": sum(r.get("E_flip_class") == "D_worsen_then_improve" for r in flips),
        },
    }
    (outdir / "o-full-census-summary.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print("analysis_type=secondary_descriptive_full_census")
    for label in ("O_at_E0", "O_at_E1"):
        c = full_census[label]
        h = holdout_census[label]
        print(
            f"{label}: n={c['n']} both_loss={c['both_loss']} both_win={c['both_win']} "
            f"base_only={c['baseline_only_loss']} added_only={c['added_only_loss']} "
            f"delta={c['delta_loss_rate']:.9f} change={c['change_rate']:.9f} "
            f"net={c['net_count']} "
            f"| holdout_n={h['n']} holdout_delta={h['delta_loss_rate']:.9f} "
            f"diff={c['delta_loss_rate']-h['delta_loss_rate']:.9f}"
        )
    print(f"four_outcome_complete_n={len(complete)}")
    print(
        "I_hist="
        + ",".join(f"{k}:{i_hist[k]}" for k in (-2, -1, 0, 1, 2))
    )
    print(f"mean_I={report['mean_I']} median_I={report['median_I']}")
    print(
        f"I<0={report['I_lt_0']} I=0={report['I_eq_0']} "
        f"I>0={report['I_gt_0']} |I|=2={report['abs_I_eq_2']}"
    )
    print("counterexamples=" + json.dumps(report["counterexample_counts"]))
    print(f"outdir={outdir}")


if __name__ == "__main__":
    main()
