#!/usr/bin/env python3
"""Cycle 3: update 5x5 vs 9x9 center-relative orbit transfer with new CSV rows."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NIGHT = ROOT / "night-research"
CSV_PATH = NIGHT / "first-moves-9x9.csv"

# 5x5 center-relative D4 orbits from complete cargo classification.
ORBITS_5 = {
    (0, 0): ("WIN", 1, [(2, 2, "W")]),
    (1, 0): ("LOSS", 4, [(2, 1, "L"), (1, 2, "L")]),
    (1, 1): ("WIN", 4, [(1, 1, "W"), (3, 1, "W")]),
    (2, 0): ("WIN", 4, [(2, 0, "W"), (0, 2, "W")]),
    (2, 1): ("LOSS", 8, [(1, 0, "L"), (3, 0, "L")]),
    (2, 2): ("LOSS", 4, [(0, 0, "L"), (4, 0, "L")]),
}

# Absolute even-sum-minus-corners (5x5 rule applied to 9x9 absolute coords).
def pred_5rule(a: int, b: int) -> str:
    if (a + b) % 2 != 0:
        return "LOSS"
    if (a, b) in {(0, 0), (0, 8), (8, 0), (8, 8)}:
        return "LOSS"
    return "WIN"


def main() -> None:
    rows = []
    with CSV_PATH.open(newline="") as f:
        for row in csv.DictReader(f):
            a, b = int(row["a"]), int(row["b"])
            rows.append(
                {
                    "abs": [a, b],
                    "verdict": row["verdict"],
                    "seconds": row.get("seconds", ""),
                    "states": row.get("states", ""),
                }
            )

    center = {"abs": [4, 4], "verdict": "FIRST_WIN", "note": "documented"}

    transfer = []
    matches = flips = unresolved = 0
    for orbit, (outcome_5, size, examples) in sorted(ORBITS_5.items()):
        # Representative absolute coordinate on 9x9 with this center-rel orbit.
        # Use (4-da, 4-db) clipped into [0,8].
        da, db = orbit
        abs_rep = [4 - da, 4 - db]
        actual = None
        for row in rows:
            if row["abs"] == abs_rep:
                actual = row["verdict"]
                break
        # Also accept any absolute cell whose center-rel orbit matches.
        if actual is None:
            for row in rows:
                ca = abs(row["abs"][0] - 4)
                cb = abs(row["abs"][1] - 4)
                key = (max(ca, cb), min(ca, cb))
                if key == orbit:
                    actual = row["verdict"]
                    abs_rep = row["abs"]
                    break
        if orbit == (0, 0):
            actual = "FIRST_WIN"
            abs_rep = [4, 4]
        outcome_9 = None
        match = None
        if actual is not None:
            outcome_9 = "WIN" if actual == "FIRST_WIN" else "LOSS"
            match = outcome_9 == outcome_5
            if match:
                matches += 1
            else:
                flips += 1
        else:
            unresolved += 1
        transfer.append(
            {
                "center_rel": list(orbit),
                "orbit_size_5": size,
                "outcome_5": outcome_5,
                "abs_rep_9": abs_rep,
                "outcome_9": outcome_9,
                "verdict_9": actual,
                "match": match,
                "examples_5": examples,
            }
        )

    abs_check = []
    agree = disagree = 0
    for row in rows + [center]:
        a, b = row["abs"]
        actual = row["verdict"]
        pred = "WIN" if pred_5rule(a, b) == "WIN" else "LOSS"
        actual_out = "WIN" if actual == "FIRST_WIN" else "LOSS"
        ok = pred == actual_out
        agree += int(ok)
        disagree += int(not ok)
        abs_check.append(
            {
                "abs": [a, b],
                "actual": actual,
                "pred_5rule_even_minus_corners": pred,
                "agrees": ok,
            }
        )

    payload = {
        "nine_completed_absolute_classes": len(rows),
        "nine_win": sum(1 for r in rows if r["verdict"] == "FIRST_WIN"),
        "nine_loss": sum(1 for r in rows if r["verdict"] != "FIRST_WIN"),
        "center_documented": center,
        "transfer": transfer,
        "transfer_summary": {
            "matches": matches,
            "flips": flips,
            "unresolved": unresolved,
            "h_embed_status": (
                "REJECTED"
                if flips > 0 and unresolved == 0
                else "WEAKENED"
                if flips > 0
                else "OPEN"
            ),
        },
        "absolute_5rule_check": abs_check,
        "absolute_5rule_summary": {
            "agree": agree,
            "disagree": disagree,
            "status": "REJECTED" if disagree else "OPEN",
        },
        "notes": [
            "H-embed asks whether the SAME center-rel D4 orbit keeps outcome 5x5->9x9.",
            "A FLIP is one orbit with different outcome; even one flip weakens locality.",
            "Absolute even-sum-minus-corners is a 5x5-only rule; 9x9 absolute test is negative control.",
        ],
    }
    out = NIGHT / "cycle3-5x5-vs-9x9-transfer.json"
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {out}")
    print(
        f"transfer matches={matches} flips={flips} unresolved={unresolved} "
        f"H-embed={payload['transfer_summary']['h_embed_status']}"
    )
    for t in transfer:
        print(
            f"  orbit {tuple(t['center_rel'])}: 5x5={t['outcome_5']} "
            f"9x9={t['outcome_9']} match={t['match']}"
        )


if __name__ == "__main__":
    main()
