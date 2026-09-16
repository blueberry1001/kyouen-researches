#!/usr/bin/env python3
"""9x9 O1-only structure census from existing population (no outcomes)."""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    with (ROOT / "artifacts/9x9-factorial-population.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print("9x9 population orbits:", len(rows))
    print("cols:", list(rows[0].keys()))

    st = Counter()
    force_I = 0
    for r in rows:
        t, te, to, raw = r["top_T"], r["top_TE"], r["top_TO"], r["top_raw"]
        o_e0 = t != to
        o_e1 = te != raw
        if o_e0 and not o_e1:
            st["O0-only"] += 1
        elif o_e0 and o_e1:
            st["O-overlap"] += 1
            if t == te and to == raw:
                force_I += 1
        elif (not o_e0) and o_e1:
            st["O1-only"] += 1
        else:
            st["no-O-change"] += 1
    print("strata:", dict(st))
    print("O-overlap with forced I=0 (T==TE & TO==raw):", force_I)

    # required roots estimate for O1-only replication on 9x9
    o1 = [r for r in rows if r["top_T"] == r["top_TO"] and r["top_TE"] != r["top_raw"]]
    print("O1-only n:", len(o1))
    roots = set()
    for r in o1:
        p = r["canonical_parent"]
        roots.add((p, r["top_TE"]))
        roots.add((p, r["top_raw"]))
    print("unique O1-only required (parent,move) roots:", len(roots))

    # compare: 8x8 was 102 orbits / 204 roots / 848 total multi-stratum
    # holdout may already have some outcomes?
    with (ROOT / "artifacts/9x9-factorial-holdout.csv").open(newline="", encoding="utf-8") as f:
        hold = list(csv.DictReader(f))
    print("holdout rows:", len(hold), "cols:", list(hold[0].keys()))
    # any outcome-like columns?
    sample_cols = [c for c in hold[0] if "sample" in c.lower() or "out" in c.lower() or "loss" in c.lower() or "win" in c.lower()]
    print("holdout outcome-like cols:", sample_cols)


if __name__ == "__main__":
    main()
