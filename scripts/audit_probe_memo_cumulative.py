#!/usr/bin/env python3
"""Audit whether blind-probe `memo` is cumulative across sequential children.

The fixed 3-stone rule ranked by memo descending. If `memo` is the solver's
process-wide memo usage rather than a per-child statistic, the ranking leaks
execution order and is not a meaningful child feature.

This script is outcome-free with respect to the raw probe files themselves; it
also optionally reads blind-probe-rankings.csv to quantify how close the fixed
ranking is to exact reversal of solver-default order.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHILD_DIR = ROOT / "results" / "10x10" / "blind_probe_children"
RANKINGS = ROOT / "results" / "10x10" / "blind-probe-rankings.csv"
OUT = ROOT / "results" / "10x10" / "probe-memo-cumulative-audit.json"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def audit_probe_file(path: Path) -> dict:
    rows = read_csv(path)
    memos = [int(r["memo"]) for r in rows]
    visited = [int(r["visited"]) for r in rows]
    deltas = [memos[0]] + [b - a for a, b in zip(memos, memos[1:])]
    monotone = all(b >= a for a, b in zip(memos, memos[1:]))
    strictly = all(b > a for a, b in zip(memos, memos[1:]))
    # A cumulative counter should have each increment close to that row's work.
    # Probe memo insertions need not equal visited exactly, so use a loose ratio.
    ratios = [d / v if v else None for d, v in zip(deltas, visited)]
    close_to_row_work = all(r is not None and 0.90 <= r <= 1.05 for r in ratios)
    return {
        "path": str(path.relative_to(ROOT)),
        "rows": len(rows),
        "memo_first": memos[0] if memos else None,
        "memo_last": memos[-1] if memos else None,
        "memo_monotone": monotone,
        "memo_strictly_increasing": strictly,
        "delta_min": min(deltas) if deltas else None,
        "delta_max": max(deltas) if deltas else None,
        "delta_mean": (sum(deltas) / len(deltas)) if deltas else None,
        "visited_min": min(visited) if visited else None,
        "visited_max": max(visited) if visited else None,
        "all_delta_over_visited_ratio_0p90_to_1p05": close_to_row_work,
        "delta_over_visited_ratio_min": min(ratios) if ratios else None,
        "delta_over_visited_ratio_max": max(ratios) if ratios else None,
    }


def ranking_audit() -> dict:
    if not RANKINGS.exists():
        return {"available": False}
    rows = read_csv(RANKINGS)
    rows = [r for r in rows if int(r["stones"]) == 3]
    by_parent: dict[str, list[dict[str, str]]] = {}
    for r in rows:
        by_parent.setdefault(r["parent"], []).append(r)

    parents = []
    total = reverse_matches = 0
    for parent, group in sorted(by_parent.items()):
        n = len(group)
        matches = sum(
            int(r["fixed_rank"]) == n + 1 - int(r["solver_default_rank"])
            for r in group
        )
        total += n
        reverse_matches += matches
        parents.append({
            "parent": parent,
            "rows": n,
            "exact_reverse_matches": matches,
            "exact_reverse_fraction": matches / n if n else None,
        })
    return {
        "available": True,
        "rows": total,
        "exact_reverse_matches": reverse_matches,
        "exact_reverse_fraction": reverse_matches / total if total else None,
        "parents": parents,
    }


def main() -> None:
    # Blind 3-stone validation used budget 1,000,000.
    files = sorted(CHILD_DIR.glob("probe_*_batch*_1000000.csv"))
    audited = [audit_probe_file(p) for p in files]
    cumulative_files = [
        r for r in audited
        if r["memo_strictly_increasing"]
        and r["all_delta_over_visited_ratio_0p90_to_1p05"]
    ]
    result = {
        "interpretation": (
            "If memo is strictly increasing and each increment is approximately "
            "one row's probe work, memo is a process-wide cumulative counter and "
            "must not be used directly as a per-child ranking feature."
        ),
        "probe_files": len(audited),
        "cumulative_signature_files": len(cumulative_files),
        "cumulative_signature_fraction": (
            len(cumulative_files) / len(audited) if audited else None
        ),
        "files": audited,
        "ranking_reverse_audit": ranking_audit(),
        "recommended_corrected_feature": (
            "per_child_memo_delta = memo[i] - memo[i-1] within a fresh ordered probe process; "
            "preferably probe each child in a fresh process to remove cross-child memo reuse/order effects"
        ),
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "probe_files": result["probe_files"],
        "cumulative_signature_files": result["cumulative_signature_files"],
        "cumulative_signature_fraction": result["cumulative_signature_fraction"],
        "ranking_exact_reverse_fraction": result["ranking_reverse_audit"].get("exact_reverse_fraction"),
        "output": str(OUT.relative_to(ROOT)),
    }, indent=2))


if __name__ == "__main__":
    main()
