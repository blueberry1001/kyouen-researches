#!/usr/bin/env python3
"""Re-rank frozen 10k top-11 shortlist using fresh 1M probe rows."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
V3_DIR = REPO_ROOT / "results" / "10x10" / "staged-v3-holdout"
SHORTLIST = V3_DIR / "top11_shortlist.csv"
PROBE_1M = V3_DIR / "independent_probe_1000000_top11.csv"
OUT_CSV = V3_DIR / "top11_rank_1m.csv"
OUT_JSON = V3_DIR / "top11_rank_1m.manifest.json"


def move_of(parent: str, child: str) -> int:
    p = {int(x) for x in parent.split(",")}
    c = {int(x) for x in child.split(",")}
    extra = c - p
    if len(extra) != 1:
        raise RuntimeError(f"not a child: {parent} -> {child}")
    return next(iter(extra))


def corrected_key(row: dict[str, str], parent: str) -> tuple:
    outcome = row["probe_outcome"].strip().upper()
    memo = int(row["memo"])
    move = move_of(parent, row["state"])
    if outcome == "LOSS":
        tier = 0
    elif outcome == "WIN":
        tier = 2
    else:
        tier = 1
    return (tier, memo, move)


def main() -> None:
    shortlist = list(csv.DictReader(SHORTLIST.open(newline="", encoding="utf-8")))
    probes = list(csv.DictReader(PROBE_1M.open(newline="", encoding="utf-8")))
    probe_map = {(r["parent"], r["state"]): r for r in probes}
    if len(probe_map) != len(shortlist):
        raise RuntimeError(f"1M rows {len(probe_map)} != shortlist {len(shortlist)}")

    by_parent: dict[str, list[dict[str, str]]] = defaultdict(list)
    for s in shortlist:
        key = (s["parent"], s["state"])
        if key not in probe_map:
            raise RuntimeError(f"missing 1M row for {key}")
        row = dict(probe_map[key])
        row["rank_10k"] = s["rank"]
        row["memo_10k"] = s["memo"]
        by_parent[s["parent"]].append(row)

    out_rows = []
    for parent in sorted(by_parent):
        ranked = sorted(by_parent[parent], key=lambda r: corrected_key(r, parent))
        for rank, r in enumerate(ranked, start=1):
            out_rows.append(
                {
                    "parent": parent,
                    "rank_1m": rank,
                    "rank_10k": r["rank_10k"],
                    "state": r["state"],
                    "probe_outcome_1m": r["probe_outcome"],
                    "visited_1m": r["visited"],
                    "maxdepth_1m": r["maxdepth"],
                    "memo_1m": r["memo"],
                    "seconds_1m": r["seconds"],
                    "memo_10k": r["memo_10k"],
                    "move": move_of(parent, r["state"]),
                }
            )

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)

    digest = hashlib.sha256()
    for r in out_rows:
        payload = f"{r['parent']}|{r['rank_1m']}|{r['state']}".encode()
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)

    manifest = {
        "source_shortlist_sha256": hashlib.sha256(SHORTLIST.read_bytes()).hexdigest(),
        "source_1m_probe_sha256": hashlib.sha256(PROBE_1M.read_bytes()).hexdigest(),
        "ranking_key": "probe LOSS first; unresolved memo_used ascending; probe WIN last; move ascending",
        "rows": len(out_rows),
        "ranking_sha256": digest.hexdigest(),
        "labels_used": "1M probe outcomes only; exact labels not consulted",
    }
    OUT_JSON.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_CSV} rows={len(out_rows)} sha256={digest.hexdigest()}")


if __name__ == "__main__":
    main()
