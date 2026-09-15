#!/usr/bin/env python3
import csv
import json
import statistics
from collections import Counter
from pathlib import Path

ART = Path(r"D:\ghq\github.com\yuubinnkyoku\kyouen-1-to-9-classification\artifacts")
known_empty = {
    "6x6": "WIN",   # first-player win
    "7x7": "LOSS",  # second-player win
    "8x8": "LOSS",
    "9x9": "WIN",
}
rows = []
for board in ["6x6", "7x7", "8x8", "9x9"]:
    for k in ["4stone", "5stone", "6stone"]:
        p = ART / f"{board}-random-safe-{k}-out.csv"
        if not p.exists() or p.stat().st_size == 0:
            print(board, k, "missing")
            continue
        with p.open(newline="") as f:
            rs = list(csv.DictReader(f))
        c = Counter(r["child_outcome"] for r in rs)
        vis = [int(r["visited"]) for r in rs]
        rec = {
            "board": board,
            "stones": k,
            "n": len(rs),
            "LOSS": c.get("LOSS", 0),
            "WIN": c.get("WIN", 0),
            "LOSS_rate": c.get("LOSS", 0) / max(1, len(rs)),
            "visited_median": statistics.median(vis) if vis else None,
            "empty_outcome": known_empty[board],
        }
        rows.append(rec)
        print(
            f"{board} {k}: n={rec['n']} LOSS={rec['LOSS']} "
            f"rate={rec['LOSS_rate']:.4f} med={rec['visited_median']}"
        )

out = ART / "cross-board-depth-profile-6789.json"
out.write_text(
    json.dumps(
        {
            "rows": rows,
            "known_empty": known_empty,
            "winners": {
                "6x6": "first",
                "7x7": "second",
                "8x8": "second",
                "9x9": "first",
            },
        },
        indent=2,
    )
    + "\n"
)
print("wrote", out)
