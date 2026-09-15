#!/usr/bin/env python3
"""Secondary descriptive E×O interaction on the pre-registered E-sample intersection.

Targets parents with sample_E_at_O0 == 1 and sample_E_at_O1 == 1.
On each parent, encode LOSS=1 / WIN=0 for the four fixed rules:
  y00=top_T, y10=top_TE, y01=top_TO, y11=top_raw
and report I = y11 - y01 - y10 + y00.

This is descriptive only. It does not create p-values and does not join the
pre-registered Holm family of four primary tests.
"""
import argparse
import csv
import statistics
from pathlib import Path


def truthy(value):
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def normalize_result_row(row):
    out = dict(row)
    if "added_child_outcome" not in out and "other_child_outcome" in out:
        out["added_child_outcome"] = out["other_child_outcome"]
    if "added_top" not in out and "other_top" in out:
        out["added_top"] = out["other_top"]
    return out


def parse_result_map(path):
    rows = [normalize_result_row(r) for r in read_csv(path)]
    if not rows:
        raise SystemExit(f"empty solver result: {path}")
    required = {
        "canonical_parent",
        "pair_top",
        "added_top",
        "pair_child_outcome",
        "added_child_outcome",
    }
    missing = required - set(rows[0])
    if missing:
        raise SystemExit(f"solver result {path} missing columns: {sorted(missing)}")
    out = {}
    for r in rows:
        parent = r["canonical_parent"]
        if parent in out:
            raise SystemExit(f"duplicate canonical_parent in {path}: {parent}")
        out[parent] = r
    return out


def loss_bit(value):
    token = str(value).strip().upper()
    if token == "LOSS":
        return 1
    if token == "WIN":
        return 0
    raise SystemExit(f"bad outcome token: {value!r}")


def mean(xs):
    return (sum(xs) / len(xs)) if xs else ""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("holdout_csv")
    p.add_argument("--E_at_O0", required=True)
    p.add_argument("--O_at_E0", required=True)
    p.add_argument("--E_at_O1", required=True)
    p.add_argument("--O_at_E1", required=True)
    p.add_argument("summary_csv")
    args = p.parse_args()

    holdout = read_csv(args.holdout_csv)
    if not holdout:
        raise SystemExit("empty holdout CSV")
    by_parent = {r["canonical_parent"]: r for r in holdout}
    if len(by_parent) != len(holdout):
        raise SystemExit("duplicate canonical_parent in holdout CSV")

    intersection = [
        r["canonical_parent"]
        for r in holdout
        if truthy(r.get("sample_E_at_O0")) and truthy(r.get("sample_E_at_O1"))
    ]
    intersection_set = set(intersection)

    maps = {
        "T": parse_result_map(args.O_at_E0),
        "TE": parse_result_map(args.E_at_O0),
        "TO": parse_result_map(args.O_at_E1),
        "raw": parse_result_map(args.E_at_O1),
    }

    # Every intersection parent must appear in all four comparison outputs.
    for label, m in maps.items():
        missing = sorted(intersection_set - set(m))
        if missing:
            raise SystemExit(
                f"intersection parent missing from {label}: "
                f"{len(missing)} e.g. {missing[:5]}"
            )

    i_hist = {-2: 0, -1: 0, 0: 0, 1: 0, 2: 0}
    i_values = []
    e_at_o0 = []
    e_at_o1 = []
    rule_loss = {"y00": 0, "y10": 0, "y01": 0, "y11": 0}

    for parent in intersection:
        y00 = loss_bit(maps["T"][parent]["pair_child_outcome"])
        y10 = loss_bit(maps["TE"][parent]["added_child_outcome"])
        y01 = loss_bit(maps["TO"][parent]["added_child_outcome"])
        y11 = loss_bit(maps["raw"][parent]["added_child_outcome"])
        # y11 is also pair_child_outcome on E_at_O1 (baseline=top_TO vs added=top_raw).
        # Prefer the pair side when available so both sides are validated.
        y11_pair = loss_bit(maps["raw"][parent]["pair_child_outcome"])
        y01_pair = loss_bit(maps["TO"][parent]["pair_child_outcome"])
        y00_pair = loss_bit(maps["T"][parent]["pair_child_outcome"])
        y10_pair = loss_bit(maps["TE"][parent]["pair_child_outcome"])
        if y00 != y00_pair or y10 != y10_pair or y01 != y01_pair or y11 != y11_pair:
            raise SystemExit(f"cross-map outcome mismatch for {parent}")

        interaction = y11 - y01 - y10 + y00
        if interaction not in i_hist:
            raise SystemExit(f"unexpected I={interaction} for {parent}")
        i_hist[interaction] += 1
        i_values.append(interaction)
        e_at_o0.append(y10 - y00)
        e_at_o1.append(y11 - y01)
        rule_loss["y00"] += y00
        rule_loss["y10"] += y10
        rule_loss["y01"] += y01
        rule_loss["y11"] += y11

    n = len(i_values)
    summary = [
        {
            "metric": "intersection_n",
            "value": n,
        },
        {
            "metric": "I_hist_minus2",
            "value": i_hist[-2],
        },
        {
            "metric": "I_hist_minus1",
            "value": i_hist[-1],
        },
        {
            "metric": "I_hist_0",
            "value": i_hist[0],
        },
        {
            "metric": "I_hist_1",
            "value": i_hist[1],
        },
        {
            "metric": "I_hist_2",
            "value": i_hist[2],
        },
        {
            "metric": "I_lt_0",
            "value": i_hist[-2] + i_hist[-1],
        },
        {
            "metric": "I_eq_0",
            "value": i_hist[0],
        },
        {
            "metric": "I_gt_0",
            "value": i_hist[1] + i_hist[2],
        },
        {
            "metric": "abs_I_eq_2",
            "value": i_hist[-2] + i_hist[2],
        },
        {
            "metric": "mean_I",
            "value": mean(i_values),
        },
        {
            "metric": "median_I",
            "value": statistics.median(i_values) if i_values else "",
        },
        {
            "metric": "mean_E_effect_at_O0",
            "value": mean(e_at_o0),
        },
        {
            "metric": "mean_E_effect_at_O1",
            "value": mean(e_at_o1),
        },
        {
            "metric": "loss_rate_y00_top_T",
            "value": (rule_loss["y00"] / n) if n else "",
        },
        {
            "metric": "loss_rate_y10_top_TE",
            "value": (rule_loss["y10"] / n) if n else "",
        },
        {
            "metric": "loss_rate_y01_top_TO",
            "value": (rule_loss["y01"] / n) if n else "",
        },
        {
            "metric": "loss_rate_y11_top_raw",
            "value": (rule_loss["y11"] / n) if n else "",
        },
    ]

    with open(args.summary_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["metric", "value"])
        w.writeheader()
        w.writerows(summary)

    print("secondary_type=descriptive_interaction_only")
    print("holm_family_unchanged=1")
    print(f"intersection_n={n}")
    for row in summary:
        print(f"{row['metric']}={row['value']}")
    print(f"summary={Path(args.summary_csv)}")


if __name__ == "__main__":
    main()
