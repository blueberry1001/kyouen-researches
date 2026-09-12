#!/usr/bin/env python3
"""Select and freeze the 10k top-11 shortlist per parent (no exact labels).

Ranking key (identical to V2 1M / 10k corrected key):
  1. probe-resolved LOSS first
  2. unresolved PROBE: memo_used ascending
  3. probe-resolved WIN last
  4. tie-break: 4th-move board index ascending
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
V3_DIR = REPO_ROOT / "results" / "10x10" / "staged-v3-holdout"
PROBE_CSV = V3_DIR / "independent_probe_10000.csv"
TASK_CSV = V3_DIR / "exact_task_list.csv"
OUT_CSV = V3_DIR / "top11_shortlist.csv"
OUT_JSON = V3_DIR / "top11_shortlist.manifest.json"
K = 11


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
    tasks = list(csv.DictReader(TASK_CSV.open(newline="", encoding="utf-8")))
    probes = list(csv.DictReader(PROBE_CSV.open(newline="", encoding="utf-8")))
    if len(probes) != len(tasks):
        raise RuntimeError(f"probe rows {len(probes)} != tasks {len(tasks)}")
    task_keys = {(t["parent"], t["state"]) for t in tasks}
    probe_keys = {(r["parent"], r["state"]) for r in probes}
    if task_keys != probe_keys:
        raise RuntimeError("probe/task set mismatch")

    by_parent: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in probes:
        by_parent[r["parent"]].append(r)

    shortlist_rows = []
    per_parent = {}
    for parent in sorted(by_parent):
        rows = by_parent[parent]
        ranked = sorted(rows, key=lambda r: corrected_key(r, parent))
        top = ranked[:K]
        loss_resolved = sum(1 for r in top if r["probe_outcome"].strip().upper() == "LOSS")
        per_parent[parent] = {
            "n_children": len(rows),
            "selected_k": len(top),
            "loss_resolved_in_topk": loss_resolved,
            "topk_states": [r["state"] for r in top],
            "topk_memo": [int(r["memo"]) for r in top],
        }
        for rank, r in enumerate(top, start=1):
            shortlist_rows.append(
                {
                    "parent": parent,
                    "rank": rank,
                    "state": r["state"],
                    "probe_outcome": r["probe_outcome"],
                    "visited": r["visited"],
                    "maxdepth": r["maxdepth"],
                    "memo": r["memo"],
                    "seconds": r["seconds"],
                    "move": move_of(parent, r["state"]),
                }
            )

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(shortlist_rows[0].keys()))
        w.writeheader()
        w.writerows(shortlist_rows)

    digest = hashlib.sha256()
    for r in shortlist_rows:
        payload = f"{r['parent']}|{r['rank']}|{r['state']}".encode()
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)

    manifest = {
        "k": K,
        "source_probe": str(PROBE_CSV.relative_to(REPO_ROOT)),
        "source_probe_sha256": hashlib.sha256(PROBE_CSV.read_bytes()).hexdigest(),
        "ranking_key": "probe LOSS first; unresolved memo_used ascending; probe WIN last; move ascending",
        "shortlist_rows": len(shortlist_rows),
        "shortlist_sha256": digest.hexdigest(),
        "per_parent": per_parent,
        "labels_used": "probe outcomes only; exact labels not consulted",
    }
    OUT_JSON.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_CSV} rows={len(shortlist_rows)} sha256={digest.hexdigest()}")
    for parent, info in per_parent.items():
        print(
            f"  {parent}: n={info['n_children']} k={info['selected_k']} "
            f"probe_loss_in_topk={info['loss_resolved_in_topk']} "
            f"memo_top={info['topk_memo'][:3]}..."
        )


if __name__ == "__main__":
    main()
