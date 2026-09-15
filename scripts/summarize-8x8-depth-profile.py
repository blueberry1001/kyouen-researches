#!/usr/bin/env python3
import csv
import statistics as st
from collections import Counter
from pathlib import Path

root = Path(r"D:\ghq\github.com\yuubinnkyoku\kyouen-1-to-9-classification\artifacts")
rows_out = []
for name in ["3stone", "4stone", "5stone", "6stone"]:
    p = root / f"8x8-random-safe-{name}-out.csv"
    with p.open(newline="") as f:
        rows = list(csv.DictReader(f))
    c = Counter(r["child_outcome"] for r in rows)
    vis = [int(r["visited"]) for r in rows]
    rec = {
        "stones": name,
        "n": len(rows),
        "LOSS": c.get("LOSS", 0),
        "WIN": c.get("WIN", 0),
        "LOSS_rate": c.get("LOSS", 0) / len(rows),
        "visited_median": st.median(vis),
        "visited_mean": st.mean(vis),
        "visited_max": max(vis),
    }
    rows_out.append(rec)
    print(rec)

out = root / "8x8-random-depth-profile.json"
import json
out.write_text(json.dumps(rows_out, indent=2) + "\n")
print("wrote", out)
