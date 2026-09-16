#!/usr/bin/env python3
"""Compare 5x5 first-move D4 orbits with partial 9x9 absolute classes.

5x5 uses center-relative (da,db) with 0<=db<=da<=2.
9x9 classes in first-moves-9x9.csv are absolute (a,b) with 0<=b<=a<=4.
Map 9x9 absolute -> center-relative via (|a-4|,|b-4|) then D4-normalize.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent

# Complete 5x5 first moves from cargo log: id = y*5+x, WIN set
WIN5 = {
    (2, 0),
    (1, 1),
    (3, 1),
    (0, 2),
    (2, 2),
    (4, 2),
    (1, 3),
    (3, 3),
    (2, 4),
}


def d4_center_rel_5(x: int, y: int, cx: int = 2, cy: int = 2) -> tuple[int, int]:
    da, db = abs(x - cx), abs(y - cy)
    a, b = max(da, db), min(da, db)
    return a, b


def d4_abs_9(a: int, b: int) -> tuple[int, int]:
    return max(a, b), min(a, b)


def main() -> None:
    # Build 5x5 orbit table
    orbits5: dict[tuple[int, int], dict] = {}
    for y in range(5):
        for x in range(5):
            key = d4_center_rel_5(x, y)
            ent = orbits5.setdefault(key, {"size": 0, "win": 0, "loss": 0, "examples": []})
            ent["size"] += 1
            if (x, y) in WIN5:
                ent["win"] += 1
            else:
                ent["loss"] += 1
            if len(ent["examples"]) < 2:
                ent["examples"].append([x, y, "W" if (x, y) in WIN5 else "L"])

    # Load 9x9 partial
    csv_path = ROOT / "first-moves-9x9.csv"
    nine: list[dict] = []
    if csv_path.exists():
        with csv_path.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                a, b = int(row["a"]), int(row["b"])
                nine.append(
                    {
                        "abs": [a, b],
                        "verdict": row["verdict"],
                        "center_rel": [
                            max(abs(a - 4), abs(b - 4)),
                            min(abs(a - 4), abs(b - 4)),
                        ],
                        "seconds": row.get("seconds", ""),
                        "states": row.get("states", ""),
                    }
                )

    # Known: empty board 9x9 is first-player win; center classified separately.
    # Center of 9x9 = (4,4) => center_rel (0,0), documented as winning first move.
    center_known = {"abs": [4, 4], "verdict": "FIRST_WIN", "center_rel": [0, 0], "note": "documented"}

    # Transfer table: for each center-rel orbit, 5x5 outcome vs 9x9 if known
    transfer = []
    for key in sorted(orbits5.keys(), reverse=True):
        ent = orbits5[key]
        outcome5 = "WIN" if ent["loss"] == 0 else ("LOSS" if ent["win"] == 0 else "MIXED")
        nine_hit = None
        if center_known["center_rel"] == list(key):
            nine_hit = center_known["verdict"].replace("FIRST_", "")
        for row in nine:
            if row["center_rel"] == list(key):
                nine_hit = row["verdict"].replace("FIRST_", "")
        transfer.append(
            {
                "center_rel": list(key),
                "orbit_size_5": ent["size"],
                "outcome_5": outcome5,
                "win_count_5": ent["win"],
                "loss_count_5": ent["loss"],
                "outcome_9": nine_hit,
                "match": None if nine_hit is None or outcome5 == "MIXED" else (outcome5 == nine_hit),
                "examples_5": ent["examples"],
            }
        )

    # Absolute-position falsifier already available:
    abs_falsifier = []
    for row in nine:
        a, b = row["abs"]
        # 5x5 even-sum-minus-corners rule on absolute coords (NOT a valid transfer,
        # recorded only to document why absolute rule fails across sizes).
        s = a + b
        pred = (s % 2 == 0) and not (
            (a, b) in {(0, 0), (0, 4), (4, 0), (4, 4)}
            or (a in (0, 4) and b in (0, 4))
        )
        # On 9x9 absolute corners are (0,0) only in the canonical quadrant.
        is_corner_abs = a in (0, 8) and b in (0, 8)
        pred_5rule = (s % 2 == 0) and not is_corner_abs
        actual = row["verdict"] == "FIRST_WIN"
        abs_falsifier.append(
            {
                "abs": [a, b],
                "actual": row["verdict"],
                "pred_5rule_even_minus_corners": "WIN" if pred_5rule else "LOSS",
                "agrees": pred_5rule == actual,
            }
        )

    # Count completed
    n_win = sum(1 for r in nine if r["verdict"] == "FIRST_WIN")
    n_loss = sum(1 for r in nine if r["verdict"] == "FIRST_LOSS")

    out = {
        "five_by_five_orbits": [
            {
                "center_rel": list(k),
                "size": orbits5[k]["size"],
                "win": orbits5[k]["win"],
                "loss": orbits5[k]["loss"],
                "examples": orbits5[k]["examples"],
            }
            for k in sorted(orbits5.keys(), reverse=True)
        ],
        "nine_partial": nine,
        "center_documented": center_known,
        "transfer": transfer,
        "absolute_5rule_check": abs_falsifier,
        "nine_completed": len(nine),
        "nine_win": n_win,
        "nine_loss": n_loss,
        "nine_remaining_classes": [
            [0, 4],
            [1, 4],
            [2, 2],
            [2, 3],
            [2, 4],
            [3, 3],
            [3, 4],
        ],
        "notes": [
            "5x5 center-rel (a,b) outcomes from complete cargo classification.",
            "9x9 absolute classes mapped via (|a-4|,|b-4|) then max/min.",
            "Absolute even-sum-minus-corners is a 5x5-only characterization; testing it on 9x9 absolute coords is a negative control, not the embedding transfer test.",
            "Embedding transfer test asks whether the SAME center-rel orbit keeps outcome when embedded in a larger board.",
        ],
    }
    dest = ROOT / "cycle2-5x5-vs-9x9-transfer.json"
    dest.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"written": str(dest), "nine_completed": len(nine), "win": n_win, "loss": n_loss}))
    print("\nTRANSFER TABLE (center-rel):")
    for t in transfer:
        m = t["match"]
        ms = "?" if m is None else ("MATCH" if m else "FLIP")
        print(
            f"  (a,b)={tuple(t['center_rel'])}  5x5={t['outcome_5']:4s}  "
            f"9x9={str(t['outcome_9']):4s}  {ms}"
        )


if __name__ == "__main__":
    main()
