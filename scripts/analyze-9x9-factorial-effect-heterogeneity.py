#!/usr/bin/env python3
"""Secondary / exploratory factorial effect-heterogeneity diagnostics.

Primary Holm family, holdout, scores, and decision rules are unchanged.
This script only reports descriptive decompositions.

Sections:
  1. O overlap/only decomposition with exact -24 identity check
  2. E overlap/only decomposition with expected +46/+32 check
  3. Outcome-free structural feature comparison by stratum
  8. Direction-flip counterexamples (top N each)
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import Counter, defaultdict
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


def parse_results(path: Path) -> dict[str, dict]:
    rows = [normalize_result(r) for r in read_csv(path)]
    out = {}
    for r in rows:
        p = r["canonical_parent"]
        if p in out:
            raise SystemExit(f"duplicate canonical_parent in {path}: {p}")
        out[p] = r
    return out


def right_move(row: dict) -> int:
    for col in ("added_top", "other_top", "true_unique_top"):
        if col in row and row[col] != "":
            return int(row[col])
    raise SystemExit("result row lacks added/other_top")


def summarize_effect(vals: list[int]) -> dict:
    n = len(vals)
    s = sum(vals)
    return {
        "n": n,
        "net_count": s,
        "delta_loss_rate": (s / n) if n else None,
        "better": sum(v > 0 for v in vals),
        "same": sum(v == 0 for v in vals),
        "worse": sum(v < 0 for v in vals),
        "change_rate": (sum(v != 0 for v in vals) / n) if n else None,
    }


def fmt_effect(x: dict) -> str:
    return (
        f"n={x['n']} net={x['net_count']} "
        f"delta={x['delta_loss_rate'] if x['delta_loss_rate'] is not None else 'nan'} "
        f"better={x['better']} same={x['same']} worse={x['worse']} "
        f"change_rate={x['change_rate'] if x['change_rate'] is not None else 'nan'}"
    )


def pattern_bits(h: dict) -> dict:
    tops = {
        "top_T": int(h["top_T"]),
        "top_TE": int(h["top_TE"]),
        "top_TO": int(h["top_TO"]),
        "top_raw": int(h["top_raw"]),
    }
    distinct = len(set(tops.values()))
    return {
        **tops,
        "diff_E_at_O0": int(h["diff_E_at_O0"]),
        "diff_O_at_E0": int(h["diff_O_at_E0"]),
        "diff_E_at_O1": int(h["diff_E_at_O1"]),
        "diff_O_at_E1": int(h["diff_O_at_E1"]),
        "distinct_moves": distinct,
        "top_T_eq_top_TO": int(tops["top_T"] == tops["top_TO"]),
        "top_TE_eq_top_raw": int(tops["top_TE"] == tops["top_raw"]),
        "top_T_eq_top_TE": int(tops["top_T"] == tops["top_TE"]),
        "top_TO_eq_top_raw": int(tops["top_TO"] == tops["top_raw"]),
        "pattern": (
            f"T{tops['top_T']}/TE{tops['top_TE']}/TO{tops['top_TO']}/R{tops['top_raw']}"
        ),
    }


FEATURE_KEYS = [
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


def mean_or_none(xs: list[float]):
    return (sum(xs) / len(xs)) if xs else None


def structural_summary(parents: list[str], hold_by: dict, gap_by: dict) -> dict:
    rows = [pattern_bits(hold_by[p]) for p in parents]
    out = {"n": len(rows)}
    for key in FEATURE_KEYS:
        vals = [r[key] for r in rows]
        out[f"mean_{key}"] = mean_or_none(vals)
        out[f"sum_{key}"] = sum(vals)
    out["top_pattern_counts"] = dict(Counter(r["pattern"] for r in rows))
    # gap/score metadata when available
    if gap_by:
        pair_T, pair_E, pair_O, pair_raw = [], [], [], []
        true_T, true_E, true_O, true_raw = [], [], [], []
        cause = Counter()
        for p in parents:
            g = gap_by.get(p)
            if not g:
                continue
            pair_T.append(float(g["pair_T"]))
            pair_E.append(float(g["pair_E"]))
            pair_O.append(float(g["pair_O"]))
            pair_raw.append(float(g["pair_raw"]))
            true_T.append(float(g["true_T"]))
            true_E.append(float(g["true_E"]))
            true_O.append(float(g["true_O"]))
            true_raw.append(float(g["true_raw"]))
            cause[g["cause_class"]] += 1
        out["mean_pair_T"] = mean_or_none(pair_T)
        out["mean_pair_E"] = mean_or_none(pair_E)
        out["mean_pair_O"] = mean_or_none(pair_O)
        out["mean_pair_raw"] = mean_or_none(pair_raw)
        out["mean_true_T"] = mean_or_none(true_T)
        out["mean_true_E"] = mean_or_none(true_E)
        out["mean_true_O"] = mean_or_none(true_O)
        out["mean_true_raw"] = mean_or_none(true_raw)
        out["cause_class_counts"] = dict(cause)
    return out


def load_outcomes(
    parent: str,
    o0: dict,
    o1: dict,
    e0: dict,
    e1: dict,
    hold_by: dict,
    require_all: bool,
) -> dict | None:
    h = hold_by[parent]
    y00 = y01 = y10 = y11 = None
    if parent in o0:
        r = o0[parent]
        y00 = outcome01(r["pair_child_outcome"])
        y01 = outcome01(r["added_child_outcome"])
        if int(r["pair_top"]) != int(h["top_T"]) or right_move(r) != int(h["top_TO"]):
            raise SystemExit(f"O_at_E0 move mismatch: {parent}")
    if parent in o1:
        r = o1[parent]
        y10 = outcome01(r["pair_child_outcome"])
        y11 = outcome01(r["added_child_outcome"])
        if int(r["pair_top"]) != int(h["top_TE"]) or right_move(r) != int(h["top_raw"]):
            raise SystemExit(f"O_at_E1 move mismatch: {parent}")
    if parent in e0:
        r = e0[parent]
        yy00 = outcome01(r["pair_child_outcome"])
        yy10 = outcome01(r["added_child_outcome"])
        if int(r["pair_top"]) != int(h["top_T"]) or right_move(r) != int(h["top_TE"]):
            raise SystemExit(f"E_at_O0 move mismatch: {parent}")
        if y00 is not None and y00 != yy00:
            raise SystemExit(f"y00 mismatch sources: {parent}")
        y00 = yy00
        y10 = yy10
    if parent in e1:
        r = e1[parent]
        yy01 = outcome01(r["pair_child_outcome"])
        yy11 = outcome01(r["added_child_outcome"])
        if int(r["pair_top"]) != int(h["top_TO"]) or right_move(r) != int(h["top_raw"]):
            raise SystemExit(f"E_at_O1 move mismatch: {parent}")
        if y01 is not None and y01 != yy01:
            raise SystemExit(f"y01 mismatch sources: {parent}")
        y01 = yy01
        y11 = yy11
    if require_all and None in (y00, y01, y10, y11):
        return None
    return {"y00": y00, "y01": y01, "y10": y10, "y11": y11}


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = fields or list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


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
        "--outdir", default="results/9x9/factorial/effect-heterogeneity"
    )
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    hold = read_csv(Path(args.holdout))
    hold_by = {r["canonical_parent"]: r for r in hold}
    if len(hold_by) != len(hold):
        raise SystemExit("duplicate canonical_parent in holdout")

    gap_by = {}
    gap_path = Path(args.gap)
    if gap_path.exists():
        gap_by = {r["canonical_parent"]: r for r in read_csv(gap_path)}

    o0 = parse_results(Path(args.O_at_E0))
    o1 = parse_results(Path(args.O_at_E1))
    e0 = parse_results(Path(args.E_at_O0))
    e1 = parse_results(Path(args.E_at_O1))

    expected0 = {p for p, r in hold_by.items() if truthy(r["census_O_at_E0"])}
    expected1 = {p for p, r in hold_by.items() if truthy(r["census_O_at_E1"])}
    sample_e0 = {p for p, r in hold_by.items() if truthy(r["sample_E_at_O0"])}
    sample_e1 = {p for p, r in hold_by.items() if truthy(r["sample_E_at_O1"])}

    if set(o0) != expected0:
        raise SystemExit(
            f"O0 parent-set mismatch missing={len(expected0-set(o0))} "
            f"extra={len(set(o0)-expected0)}"
        )
    if set(o1) != expected1:
        raise SystemExit(
            f"O1 parent-set mismatch missing={len(expected1-set(o1))} "
            f"extra={len(set(o1)-expected1)}"
        )

    overlap = sorted(expected0 & expected1)
    o0_only = sorted(expected0 - expected1)
    o1_only = sorted(expected1 - expected0)
    e_overlap = sorted(sample_e0 & sample_e1)
    e0_only = sorted(sample_e0 - sample_e1)
    e1_only = sorted(sample_e1 - sample_e0)

    report: dict = {
        "analysis_type": "secondary_exploratory",
        "primary_holm_unchanged": True,
        "new_p_values": False,
    }

    # ---- 1. O overlap/only ----
    o_rows = []
    overlap_e0, overlap_e1, interactions = [], [], []
    o0_only_vals, o1_only_vals = [], []
    for p in sorted(expected0 | expected1):
        h = hold_by[p]
        rec = {
            "canonical_parent": p,
            "stratum": (
                "overlap"
                if p in expected0 and p in expected1
                else "O0_only"
                if p in expected0
                else "O1_only"
            ),
            "y00_T": "",
            "y01_TO": "",
            "y10_TE": "",
            "y11_raw": "",
            "O_effect_E0": "",
            "O_effect_E1": "",
            "interaction": "",
        }
        if p in expected0:
            r0 = o0[p]
            y00 = outcome01(r0["pair_child_outcome"])
            y01 = outcome01(r0["added_child_outcome"])
            e0eff = y01 - y00
            rec["y00_T"] = y00
            rec["y01_TO"] = y01
            rec["O_effect_E0"] = e0eff
            if p in o0_only:
                o0_only_vals.append(e0eff)
        if p in expected1:
            r1 = o1[p]
            y10 = outcome01(r1["pair_child_outcome"])
            y11 = outcome01(r1["added_child_outcome"])
            e1eff = y11 - y10
            rec["y10_TE"] = y10
            rec["y11_raw"] = y11
            rec["O_effect_E1"] = e1eff
            if p in o1_only:
                o1_only_vals.append(e1eff)
        if p in expected0 and p in expected1:
            inter = rec["O_effect_E1"] - rec["O_effect_E0"]
            rec["interaction"] = inter
            overlap_e0.append(rec["O_effect_E0"])
            overlap_e1.append(rec["O_effect_E1"])
            interactions.append(inter)
        o_rows.append(rec)

    write_csv(outdir / "o-overlap-decomposition.csv", o_rows)

    s_ov0 = summarize_effect(overlap_e0)
    s_ov1 = summarize_effect(overlap_e1)
    s_o0 = summarize_effect(o0_only_vals)
    s_o1 = summarize_effect(o1_only_vals)
    hist = {v: sum(x == v for x in interactions) for v in (-2, -1, 0, 1, 2)}
    sum_interaction = sum(interactions)
    identity_lhs = sum_interaction + sum(o1_only_vals) - sum(o0_only_vals)
    identity_rhs = (sum(o1_only_vals) + sum(overlap_e1)) - (
        sum(o0_only_vals) + sum(overlap_e0)
    )
    # known overall: O0=+21, O1=-3, difference=-24
    known_o0_net = 169 - 148
    known_o1_net = 141 - 144
    known_diff = known_o1_net - known_o0_net

    report["o_decomposition"] = {
        "O0_n": len(expected0),
        "O1_n": len(expected1),
        "overlap_n": len(overlap),
        "O0_only_n": len(o0_only),
        "O1_only_n": len(o1_only),
        "overlap_O_effect_E0": s_ov0,
        "overlap_O_effect_E1": s_ov1,
        "O0_only_effect": s_o0,
        "O1_only_effect": s_o1,
        "interaction_histogram": {str(k): v for k, v in hist.items()},
        "mean_interaction": statistics.mean(interactions) if interactions else None,
        "median_interaction": statistics.median(interactions) if interactions else None,
        "interaction_positive": sum(x > 0 for x in interactions),
        "interaction_zero": sum(x == 0 for x in interactions),
        "interaction_negative": sum(x < 0 for x in interactions),
        "overlap_interaction_sum": sum_interaction,
        "O0_total_net_reconstructed": sum(overlap_e0) + sum(o0_only_vals),
        "O1_total_net_reconstructed": sum(overlap_e1) + sum(o1_only_vals),
        "known_O0_net": known_o0_net,
        "known_O1_net": known_o1_net,
        "known_diff_O1_minus_O0": known_diff,
        "decomposition_lhs": identity_lhs,
        "decomposition_rhs_from_parts": identity_rhs,
        "identity_holds": identity_lhs == known_diff,
    }

    # ---- 2. E overlap/only ----
    e_rows = []
    e_ov0, e_ov1, e_interactions = [], [], []
    e0_only_vals, e1_only_vals = [], []
    for p in sorted(sample_e0 | sample_e1):
        rec = {
            "canonical_parent": p,
            "stratum": (
                "overlap"
                if p in sample_e0 and p in sample_e1
                else "E0_only"
                if p in sample_e0
                else "E1_only"
            ),
            "y00_T": "",
            "y01_TO": "",
            "y10_TE": "",
            "y11_raw": "",
            "E_effect_O0": "",
            "E_effect_O1": "",
            "interaction": "",
        }
        if p in sample_e0:
            r0 = e0[p]
            y00 = outcome01(r0["pair_child_outcome"])
            y10 = outcome01(r0["added_child_outcome"])
            eff = y10 - y00
            rec["y00_T"] = y00
            rec["y10_TE"] = y10
            rec["E_effect_O0"] = eff
            if p in e0_only:
                e0_only_vals.append(eff)
        if p in sample_e1:
            r1 = e1[p]
            y01 = outcome01(r1["pair_child_outcome"])
            y11 = outcome01(r1["added_child_outcome"])
            eff = y11 - y01
            rec["y01_TO"] = y01
            rec["y11_raw"] = y11
            rec["E_effect_O1"] = eff
            if p in e1_only:
                e1_only_vals.append(eff)
        if p in sample_e0 and p in sample_e1:
            inter = rec["E_effect_O1"] - rec["E_effect_O0"]
            rec["interaction"] = inter
            e_ov0.append(rec["E_effect_O0"])
            e_ov1.append(rec["E_effect_O1"])
            e_interactions.append(inter)
        e_rows.append(rec)

    write_csv(outdir / "e-overlap-decomposition.csv", e_rows)

    s_e_ov0 = summarize_effect(e_ov0)
    s_e_ov1 = summarize_effect(e_ov1)
    s_e0 = summarize_effect(e0_only_vals)
    s_e1 = summarize_effect(e1_only_vals)
    e_hist = {v: sum(x == v for x in e_interactions) for v in (-2, -1, 0, 1, 2)}
    # known overall: E0=+43, E1=+26
    known_e0_net = 253 - 210
    known_e1_net = 239 - 213
    report["e_decomposition"] = {
        "E0_n": len(sample_e0),
        "E1_n": len(sample_e1),
        "overlap_n": len(e_overlap),
        "E0_only_n": len(e0_only),
        "E1_only_n": len(e1_only),
        "overlap_E_effect_O0": s_e_ov0,
        "overlap_E_effect_O1": s_e_ov1,
        "E0_only_effect": s_e0,
        "E1_only_effect": s_e1,
        "interaction_histogram": {str(k): v for k, v in e_hist.items()},
        "mean_interaction": (
            statistics.mean(e_interactions) if e_interactions else None
        ),
        "mean_E_effect_O0_on_overlap": s_e_ov0["delta_loss_rate"],
        "mean_E_effect_O1_on_overlap": s_e_ov1["delta_loss_rate"],
        "known_E0_net": known_e0_net,
        "known_E1_net": known_e1_net,
        "E0_net_reconstructed": sum(e_ov0) + sum(e0_only_vals),
        "E1_net_reconstructed": sum(e_ov1) + sum(e1_only_vals),
        "expected_overlap_E0_net": -3,
        "expected_overlap_E1_net": -6,
        "expected_E0_only_net": 46,
        "expected_E1_only_net": 32,
        "check_overlap_E0_net": sum(e_ov0) == -3,
        "check_overlap_E1_net": sum(e_ov1) == -6,
        "check_E0_only_net": sum(e0_only_vals) == 46,
        "check_E1_only_net": sum(e1_only_vals) == 32,
    }

    # ---- 3. structural features ----
    strata = {
        "O_overlap": overlap,
        "O0_only": o0_only,
        "O1_only": o1_only,
        "E_overlap": e_overlap,
        "E0_only": e0_only,
        "E1_only": e1_only,
    }
    struct_rows = []
    structural = {}
    for name, parents in strata.items():
        summary = structural_summary(parents, hold_by, gap_by)
        structural[name] = summary
        row = {
            "stratum": name,
            "n": summary["n"],
        }
        for key in FEATURE_KEYS:
            row[f"mean_{key}"] = summary.get(f"mean_{key}")
        if "mean_pair_T" in summary:
            row["mean_pair_T"] = summary["mean_pair_T"]
            row["mean_pair_E"] = summary["mean_pair_E"]
            row["mean_pair_O"] = summary["mean_pair_O"]
            row["mean_pair_raw"] = summary["mean_pair_raw"]
            row["mean_true_T"] = summary["mean_true_T"]
            row["mean_true_E"] = summary["mean_true_E"]
            row["mean_true_O"] = summary["mean_true_O"]
            row["mean_true_raw"] = summary["mean_true_raw"]
        struct_rows.append(row)
    write_csv(outdir / "structural-strata.csv", struct_rows)
    report["structural_strata"] = structural

    # ---- 8. counterexamples ----
    flip_rows = []
    for p in sorted(expected0 & expected1):
        y00 = outcome01(o0[p]["pair_child_outcome"])
        y01 = outcome01(o0[p]["added_child_outcome"])
        y10 = outcome01(o1[p]["pair_child_outcome"])
        y11 = outcome01(o1[p]["added_child_outcome"])
        o_e0 = y01 - y00
        o_e1 = y11 - y10
        h = hold_by[p]
        rec = {
            "canonical_parent": p,
            "top_T": h["top_T"],
            "top_TE": h["top_TE"],
            "top_TO": h["top_TO"],
            "top_raw": h["top_raw"],
            "y00_T": y00,
            "y01_TO": y01,
            "y10_TE": y10,
            "y11_raw": y11,
            "O_effect_E0": o_e0,
            "O_effect_E1": o_e1,
            "interaction": o_e1 - o_e0,
            "O_flip_class": (
                "A_improve_then_worsen"
                if o_e0 < 0 and o_e1 > 0
                else "B_worsen_then_improve"
                if o_e0 > 0 and o_e1 < 0
                else "none"
            ),
        }
        if p in sample_e0 and p in sample_e1:
            ee0 = outcome01(e0[p]["added_child_outcome"]) - outcome01(
                e0[p]["pair_child_outcome"]
            )
            ee1 = outcome01(e1[p]["added_child_outcome"]) - outcome01(
                e1[p]["pair_child_outcome"]
            )
            rec["E_effect_O0"] = ee0
            rec["E_effect_O1"] = ee1
            rec["E_interaction"] = ee1 - ee0
            rec["E_flip_class"] = (
                "C_improve_then_worsen"
                if ee0 < 0 and ee1 > 0
                else "D_worsen_then_improve"
                if ee0 > 0 and ee1 < 0
                else "none"
            )
        else:
            rec["E_effect_O0"] = ""
            rec["E_effect_O1"] = ""
            rec["E_interaction"] = ""
            rec["E_flip_class"] = "not_in_E_intersection"
        g = gap_by.get(p, {})
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
        for k in FEATURE_KEYS:
            rec[k] = pattern_bits(h)[k]
        flip_rows.append(rec)

    write_csv(outdir / "direction-flips.csv", flip_rows)

    def take(cls: str, key: str, n: int = 20) -> list[dict]:
        sel = [r for r in flip_rows if r[key] == cls]
        sel.sort(key=lambda r: (abs(int(r.get("interaction") or r.get("E_interaction") or 0)), r["canonical_parent"]))
        return sel[:n]

    examples = {
        "A_O_improve_E0_worsen_E1": take("A_improve_then_worsen", "O_flip_class"),
        "B_O_worsen_E0_improve_E1": take("B_worsen_then_improve", "O_flip_class"),
        "C_E_improve_O0_worsen_O1": take("C_improve_then_worsen", "E_flip_class"),
        "D_E_worsen_O0_improve_O1": take("D_worsen_then_improve", "E_flip_class"),
    }
    report["counterexample_counts"] = {
        "A": sum(r["O_flip_class"] == "A_improve_then_worsen" for r in flip_rows),
        "B": sum(r["O_flip_class"] == "B_worsen_then_improve" for r in flip_rows),
        "C": sum(r.get("E_flip_class") == "C_improve_then_worsen" for r in flip_rows),
        "D": sum(r.get("E_flip_class") == "D_worsen_then_improve" for r in flip_rows),
    }
    for name, rows in examples.items():
        write_csv(outdir / f"examples-{name}.csv", rows)

    report["outputs"] = {
        "o_overlap_decomposition": str(outdir / "o-overlap-decomposition.csv"),
        "e_overlap_decomposition": str(outdir / "e-overlap-decomposition.csv"),
        "structural_strata": str(outdir / "structural-strata.csv"),
        "direction_flips": str(outdir / "direction-flips.csv"),
    }

    (outdir / "effect-heterogeneity-summary.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # console summary
    print("analysis_type=secondary_exploratory")
    print("primary_holm_unchanged=1")
    print(f"O0_n={len(expected0)} O1_n={len(expected1)}")
    print(f"overlap_n={len(overlap)} O0_only_n={len(o0_only)} O1_only_n={len(o1_only)}")
    print("overlap_O_effect_E0 " + fmt_effect(s_ov0))
    print("overlap_O_effect_E1 " + fmt_effect(s_ov1))
    print("O0_only " + fmt_effect(s_o0))
    print("O1_only " + fmt_effect(s_o1))
    print("interaction_hist=" + ",".join(f"{k}:{v}" for k, v in hist.items()))
    print(f"mean_interaction={report['o_decomposition']['mean_interaction']}")
    print(f"median_interaction={report['o_decomposition']['median_interaction']}")
    print(f"identity_lhs={identity_lhs} known_diff={known_diff} ok={identity_lhs==known_diff}")
    print(
        f"E overlap_n={len(e_overlap)} E0_only_n={len(e0_only)} "
        f"E1_only_n={len(e1_only)}"
    )
    print("overlap_E_effect_O0 " + fmt_effect(s_e_ov0))
    print("overlap_E_effect_O1 " + fmt_effect(s_e_ov1))
    print("E0_only " + fmt_effect(s_e0))
    print("E1_only " + fmt_effect(s_e1))
    print(
        "E checks: "
        f"ov0={sum(e_ov0)} ov1={sum(e_ov1)} "
        f"e0only={sum(e0_only_vals)} e1only={sum(e1_only_vals)}"
    )
    print("counterexamples=" + json.dumps(report["counterexample_counts"]))
    print(f"outdir={outdir}")


if __name__ == "__main__":
    main()
