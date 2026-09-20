#!/usr/bin/env python3
"""Exploratory comparison of child-local probe features on the seven known-LOSS parents.

This script is deliberately limited to already-revealed batch0 exact labels.  It
must not be used to select or reveal a new holdout.  Candidate feature families
are fixed here before the fresh 1M isolated-probe results are inspected:

  memo, maxdepth, mean_depth, deep_fraction(d>=15)

Each is evaluated in both directions.  Ties use the original child-file order,
which is also reported as the solver-default baseline.  A deterministic random
baseline is summarized by exact expected first-LOSS position for the observed
number of LOSS children: (n + 1) / (k + 1).
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import median

KNOWN = (
    "2_9_33",
    "4_9_33",
    "9_12_33",
    "9_19_33",
    "9_23_33",
    "0_31_36",
    "0_36_44",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def state_key(s: str) -> tuple[int, ...]:
    return tuple(sorted(map(int, s.replace(",", "-").split("-"))))


def add_features(row: dict[str, str]) -> dict[str, float]:
    visited = int(row["visited"])
    if visited <= 0:
        raise ValueError("visited must be positive")
    depths = []
    for key, value in row.items():
        if key.startswith("depth_visited_"):
            d = int(key.removeprefix("depth_visited_"))
            depths.append((d, int(value)))
    total_depth_visits = sum(v for _, v in depths)
    # For a cutoff probe this should equal visited; do not silently assume it.
    if total_depth_visits != visited:
        raise ValueError(
            f"depth histogram sum {total_depth_visits} != visited {visited} for {row['state']}"
        )
    return {
        "memo": float(row["memo"]),
        "maxdepth": float(row["maxdepth"]),
        "mean_depth": sum(d * v for d, v in depths) / visited,
        "deep_fraction": sum(v for d, v in depths if d >= 15) / visited,
    }


def first_loss(order: list[dict]) -> int:
    for i, row in enumerate(order, start=1):
        if row["is_loss"]:
            return i
    return len(order) + 1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("probe_dir", type=Path)
    ap.add_argument("--exact-dir", type=Path, default=Path("results/10x10/blind_probe_children"))
    ap.add_argument("--json-out", type=Path)
    ap.add_argument("--csv-out", type=Path)
    args = ap.parse_args()

    per_parent = []
    candidate_positions: dict[str, list[int]] = defaultdict(list)
    baseline_positions = []
    random_expected_positions = []

    for safe in KNOWN:
        probe = args.probe_dir / f"probe_isolated_{safe}_batch0_1000000.csv"
        exact = args.exact_dir / f"exact_{safe}_batch0.csv"
        if not probe.exists():
            raise SystemExit(f"missing isolated probe: {probe}")
        if not exact.exists():
            raise SystemExit(f"missing exact labels: {exact}")

        probes = read_csv(probe)
        labels = {state_key(r["state"]): r["outcome"] for r in read_csv(exact)}
        rows = []
        for idx, r in enumerate(probes):
            key = state_key(r["state"])
            if key not in labels:
                raise SystemExit(f"no exact label for {r['state']} in {safe}")
            feat = add_features(r)
            rows.append({
                "state": r["state"],
                "index": idx,
                "is_loss": labels[key] == "LOSS",
                **feat,
            })

        n = len(rows)
        k = sum(r["is_loss"] for r in rows)
        if k == 0:
            raise SystemExit(f"known parent unexpectedly has no LOSS in batch0: {safe}")
        default_pos = first_loss(rows)
        baseline_positions.append(default_pos)
        random_expected = (n + 1) / (k + 1)
        random_expected_positions.append(random_expected)

        rec = {
            "parent": safe.replace("_", ","),
            "children": n,
            "losses": k,
            "solver_default": default_pos,
            "random_expected": random_expected,
        }
        for feature in ("memo", "maxdepth", "mean_depth", "deep_fraction"):
            for direction, reverse in (("asc", False), ("desc", True)):
                name = f"{feature}_{direction}"
                ordered = sorted(
                    rows,
                    key=lambda x: ((-x[feature] if reverse else x[feature]), x["index"]),
                )
                pos = first_loss(ordered)
                rec[name] = pos
                candidate_positions[name].append(pos)
        per_parent.append(rec)

    summary = {
        "parents": len(per_parent),
        "scope": "exploratory_known_labels_only",
        "solver_default_median_first_loss": median(baseline_positions),
        "random_expected_median_first_loss": median(random_expected_positions),
        "candidates": {},
    }
    for name, positions in sorted(candidate_positions.items()):
        summary["candidates"][name] = {
            "positions": positions,
            "median_first_loss": median(positions),
            "wins_vs_solver_default": sum(p < b for p, b in zip(positions, baseline_positions)),
            "ties_vs_solver_default": sum(p == b for p, b in zip(positions, baseline_positions)),
            "losses_vs_solver_default": sum(p > b for p, b in zip(positions, baseline_positions)),
        }

    # Rank by median first-LOSS, then by number of parent-wise wins, then name.
    ranked = sorted(
        summary["candidates"].items(),
        key=lambda kv: (kv[1]["median_first_loss"], -kv[1]["wins_vs_solver_default"], kv[0]),
    )
    summary["exploratory_ranking"] = [name for name, _ in ranked]

    print(json.dumps(summary, indent=2, sort_keys=True))

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps({"summary": summary, "per_parent": per_parent}, indent=2, sort_keys=True) + "\n")
    if args.csv_out:
        args.csv_out.parent.mkdir(parents=True, exist_ok=True)
        fields = list(per_parent[0])
        with args.csv_out.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(per_parent)


if __name__ == "__main__":
    main()
