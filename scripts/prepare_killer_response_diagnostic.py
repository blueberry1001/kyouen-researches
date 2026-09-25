#!/usr/bin/env python3
"""Prepare the preregistered killer-response diagnostic without opening response values.

Reads the frozen blind ranking, reconstructs v_fixed from fixed_rank=1, asks
kyouen-query for the legal opponent responses, and writes a deterministic CSV
manifest containing response states and immediate unique-gain ranks.  It does
NOT solve any response state.

Build query tool first, e.g.:
  c++ -std=c++20 -O2 cpp/tools/kyouen_query.cpp -o build/kyouen-query

Usage:
  python scripts/prepare_killer_response_diagnostic.py \
      --query build/kyouen-query \
      --output results/10x10/killer-response-manifest.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RANKINGS = ROOT / "results/10x10/blind-probe-rankings.csv"
FRESH = {"2,9,33", "9,12,33", "9,23,33", "0,31,36", "0,36,44"}
CALIBRATION = {"4,9,33", "9,19,33"}
EXPECTED = FRESH | CALIBRATION


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--query", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    return p.parse_args()


def query(exe: Path, ids: list[int]) -> dict:
    proc = subprocess.run(
        [str(exe), "--size", "10", "--ids", ",".join(map(str, ids)), "--format", "json"],
        check=True, text=True, capture_output=True,
    )
    return json.loads(proc.stdout)


def main() -> None:
    args = parse_args()
    fixed: dict[str, int] = {}
    with RANKINGS.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            parent = row["parent"]
            if parent in EXPECTED and int(row["fixed_rank"]) == 1:
                if parent in fixed:
                    raise SystemExit(f"duplicate fixed_rank=1 for {parent}")
                fixed[parent] = int(row["move_index"])
    if set(fixed) != EXPECTED:
        raise SystemExit(f"fixed reconstruction mismatch: got={sorted(fixed)} expected={sorted(EXPECTED)}")

    rows: list[dict] = []
    for parent in sorted(EXPECTED, key=lambda s: tuple(map(int, s.split(",")))):
        parent_ids = list(map(int, parent.split(",")))
        v_fixed = fixed[parent]
        s1 = sorted(parent_ids + [v_fixed])
        q1 = query(args.query, s1)
        if not q1.get("valid", False):
            raise SystemExit(f"fixed child is invalid: {parent} + {v_fixed}")
        legal = [int(x) for x in q1["legal_ids"]]
        before = len(legal)
        tmp = []
        for response in legal:
            s2 = sorted(s1 + [response])
            q2 = query(args.query, s2)
            if not q2.get("valid", False):
                raise SystemExit(f"response unexpectedly invalid: {s2}")
            after = len(q2["legal_ids"])
            gain = before - 1 - after
            if gain < 0:
                raise SystemExit(f"negative unique gain: {s2} gain={gain}")
            tmp.append((response, s2, gain))

        ordered = sorted(tmp, key=lambda x: (-x[2], x[0]))
        distinct_gains = sorted({x[2] for x in tmp}, reverse=True)
        tier = {g: i + 1 for i, g in enumerate(distinct_gains)}
        for move_rank, (response, s2, gain) in enumerate(ordered, 1):
            competition_rank = 1 + sum(1 for _, _, g in tmp if g > gain)
            rows.append({
                "cohort": "fresh" if parent in FRESH else "calibration",
                "parent": parent,
                "v_fixed": v_fixed,
                "fixed_child": ",".join(map(str, s1)),
                "response": response,
                "response_state": ",".join(map(str, s2)),
                "unique_gain": gain,
                "move_rank": move_rank,
                "gain_competition_rank": competition_rank,
                "gain_tier_rank": tier[gain],
                "exact_outcome": "",
            })

    fields = list(rows[0])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} unsolved response rows to {args.output}")
    print("exact_outcome intentionally blank: manifest preparation does not open confirmatory values")


if __name__ == "__main__":
    main()
