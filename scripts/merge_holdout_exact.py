#!/usr/bin/env python3
"""Merge per-worker holdout exact CSVs into blind_probe_children exact files.

Reads (untracked, sweep outputs):
  results/10x10/blind-probe-holdout/exact_outcomes_w*.csv
  results/10x10/blind-probe-holdout/exact_timeouts.csv (must be absent/empty)

Writes (one per parent batch, analyzer-compatible):
  results/10x10/blind_probe_children/exact_<safe>_batch<N>.csv
with columns: state,outcome,visited,maxdepth,memo,seconds

Fails unless every frozen task has exactly one non-timeout outcome row.
This script collects outcomes; it never ranks children or reads probes.
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from run_probe_holdout_independent import load_tasks  # noqa: E402

OUT_HOLDOUT = REPO_ROOT / "results" / "10x10" / "blind-probe-holdout"
CHILDREN_DIR = REPO_ROOT / "results" / "10x10" / "blind_probe_children"


def safe_parent(p: str) -> str:
    return p.replace(",", "_")


def main() -> None:
    timeouts = OUT_HOLDOUT / "exact_timeouts.csv"
    if timeouts.exists() and timeouts.stat().st_size > 0:
        rows = list(csv.DictReader(timeouts.open(encoding="utf-8")))
        if rows:
            raise SystemExit(f"refusing merge: {len(rows)} recorded timeouts in {timeouts}")
    tasks = load_tasks()
    outcomes: dict[tuple[str, str], dict[str, str]] = {}
    for path in sorted(OUT_HOLDOUT.glob("exact_outcomes_w*.csv")):
        with path.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                key = (r["parent"], r["state"].replace(",", "-"))
                if key in outcomes:
                    raise SystemExit(f"duplicate outcome row: {key}")
                if r["outcome"] not in ("WIN", "LOSS"):
                    raise SystemExit(f"non-exact outcome for {key}: {r['outcome']}")
                outcomes[key] = r
    missing = [(p, s) for (p, _b, _pos, s) in tasks
               if (p, s.replace(",", "-")) not in outcomes]
    if missing:
        raise SystemExit(f"incomplete: {len(missing)}/ {len(tasks)} tasks missing outcomes")
    extra = set(outcomes) - {(p, s.replace(",", "-")) for (p, _b, _pos, s) in tasks}
    if extra:
        raise SystemExit(f"{len(extra)} outcome rows outside frozen task set")
    by_batch: dict[tuple[str, int], list[dict[str, str]]] = defaultdict(list)
    for (parent, batch, _pos, state) in tasks:
        r = outcomes[(parent, state.replace(",", "-"))]
        by_batch[(parent, batch)].append(r)
    written = 0
    for (parent, batch), rows in sorted(by_batch.items()):
        out = CHILDREN_DIR / f"exact_{safe_parent(parent)}_batch{batch}.csv"
        if out.exists():
            raise SystemExit(f"refusing to overwrite existing {out}")
        with out.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["state", "outcome", "visited",
                                              "maxdepth", "memo", "seconds"])
            w.writeheader()
            for r in rows:
                w.writerow({"state": r["state"].replace(",", "-"),
                            "outcome": r["outcome"], "visited": r["visited"],
                            "maxdepth": r["maxdepth"], "memo": r["memo"],
                            "seconds": r["seconds"]})
        written += 1
    print(f"merged {len(outcomes)} outcomes into {written} batch files")


if __name__ == "__main__":
    main()
