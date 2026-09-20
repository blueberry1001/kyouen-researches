#!/usr/bin/env python3
"""Audit whether 10k root-order effects depend on memo ties.

For each parent benchmark strategy-B run, inspect exactly the root-order prefix
that the exact solve entered before stopping.  The probe order is frozen as
(memo_used, move id); if memo values tie inside this decisive prefix, the raw
move-id tie-break can affect the observed benchmark.  We also report the
smallest adjacent memo gap as a crude near-tie sensitivity diagnostic.

This analysis uses only already-recorded parent benchmark artifacts and does
not rerun any solver.
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "results" / "10x10" / "parent-benchmark"
PROBES = BENCH / "probe_rows.csv"
RAW = BENCH / "parent_benchmark_raw.csv"
ORDERS = BENCH / "root_orders"


def load_probes() -> dict[tuple[str, str], int]:
    out: dict[tuple[str, str], int] = {}
    with PROBES.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[(r["parent"].strip(), r["state"].strip())] = int(r["memo"])
    return out


def load_b_rows() -> list[dict[str, str]]:
    with RAW.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    rows = [r for r in rows if r["strategy"].strip() == "B"]
    # Resume-safe raw files should contain one completed B row per parent.
    by_parent: dict[str, dict[str, str]] = {}
    for r in rows:
        p = r["parent"].strip()
        if p in by_parent:
            raise RuntimeError(f"duplicate strategy-B row for {p}")
        by_parent[p] = r
    return [by_parent[p] for p in sorted(by_parent)]


def load_order(parent: str) -> list[str]:
    p = ORDERS / f"order_{parent.replace(',', '_')}.txt"
    return [s.strip() for s in p.read_text(encoding="utf-8").splitlines() if s.strip()]


def main() -> None:
    probes = load_probes()
    rows = load_b_rows()

    print("parent,root_entered,prefix_memos,has_prefix_tie,min_adjacent_gap")
    tie_parents = 0
    for r in rows:
        parent = r["parent"].strip()
        entered = int(r["root_entered"])
        order = load_order(parent)
        assert 0 <= entered <= len(order), (parent, entered, len(order))
        prefix = order[:entered]
        memos = [probes[(parent, s)] for s in prefix]
        has_tie = len(set(memos)) != len(memos)
        if has_tie:
            tie_parents += 1
        gaps = [b - a for a, b in zip(memos, memos[1:])]
        min_gap = min(gaps) if gaps else "NA"
        memo_text = ";".join(map(str, memos))
        print(f'{parent},{entered},"{memo_text}",{int(has_tie)},{min_gap}')

    print(
        f"summary parents={len(rows)} decisive_prefix_tie_parents={tie_parents} "
        f"tie_free={len(rows)-tie_parents}"
    )


if __name__ == "__main__":
    main()
