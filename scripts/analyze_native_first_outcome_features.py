#!/usr/bin/env python3
"""Audit cheap deployable signals for whether native root child #1 is WIN.

This is intentionally a small-cohort hypothesis audit, not a classifier fit.
Labels come from the existing exact parent benchmark. Features are recomputed
from *all* legal root children using only game geometry, so they are available
before any exact child search or 10k probe.

The main post-hoc candidate reported here is an "isolated minimum" in the
legal-move-count spectrum:

  - the global minimum is attained by exactly one legal child; and
  - no child has min+1 legal moves; and
  - the next occupied level is min+2.

Because only two of the 12 existing parents have native-first WIN, an in-sample
perfect split must be treated only as a hypothesis for blind validation.
"""

from __future__ import annotations

import json
from collections import Counter
from itertools import combinations
from pathlib import Path

SUMMARY = Path("results/10x10/parent-benchmark/loss_proof_cost_summary.json")
N = 10


def det3(m):
    return (
        m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
        - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
        + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
    )


def forbidden4(ids):
    pts = [(v % N, v // N) for v in ids]
    xd, yd = pts[3]
    qd = xd * xd + yd * yd
    m = []
    for x, y in pts[:3]:
        m.append([x * x + y * y - qd, x - xd, y - yd])
    return det3(m) == 0


def legal_after(state, move):
    if move in state:
        return False
    return all(not forbidden4((*triple, move)) for triple in combinations(state, 3))


def child_legal_count(child):
    occupied = set(child)
    return sum(
        1
        for move in range(N * N)
        if move not in occupied and legal_after(child, move)
    )


def all_child_legal_counts(parent):
    out = []
    for move in range(N * N):
        if move in parent or not legal_after(parent, move):
            continue
        child = tuple(sorted((*parent, move)))
        out.append((move, child_legal_count(child)))
    return out


def spectrum_features(rows):
    counts = Counter(v for _, v in rows)
    levels = sorted(counts)
    m = levels[0]
    next_gap = levels[1] - m if len(levels) > 1 else None
    return {
        "n_children": len(rows),
        "min": m,
        "n_min": counts[m],
        "n_min1": counts.get(m + 1, 0),
        "n_min2": counts.get(m + 2, 0),
        "next_gap": next_gap,
    }


def isolated_min_rule(f):
    return f["n_min"] == 1 and f["n_min1"] == 0 and f["next_gap"] == 2


def main():
    rows = json.loads(SUMMARY.read_text(encoding="utf-8"))["selected_loss"]

    tp = fp = tn = fn = 0
    print("native-first outcome / all-child legal-count spectrum audit")
    print("parent,label,n_children,min,n_min,n_min+1,n_min+2,next_gap,isolated_min_rule")
    for row in rows:
        parent_s = row["parent"]
        parent = tuple(map(int, parent_s.split(",")))
        f = spectrum_features(all_child_legal_counts(parent))
        label = row["a_first_loss_pos"] > 1  # native child #1 was WIN
        pred = isolated_min_rule(f)

        if pred and label:
            tp += 1
        elif pred and not label:
            fp += 1
        elif not pred and label:
            fn += 1
        else:
            tn += 1

        print(
            f"{parent_s},{'WIN' if label else 'LOSS'},"
            f"{f['n_children']},{f['min']},{f['n_min']},{f['n_min1']},"
            f"{f['n_min2']},{f['next_gap']},{int(pred)}"
        )

    print()
    print(f"isolated-min confusion: TP={tp} FP={fp} TN={tn} FN={fn}")
    print(
        "Interpretation: this feature is fully deployable and exactly separates "
        "the two native-first-WIN parents in the existing 12-parent cohort."
    )
    print(
        "WARNING: the rule was noticed post-hoc with only two positive examples. "
        "Do not use it as a production gate until it is frozen and tested on a "
        "new exact parent cohort."
    )
    print(
        "Recommended blind test: freeze isolated_min_rule as written; select new "
        "LOSS parents independently of this feature; record the feature before "
        "exact root-child outcomes; then report precision/recall plus the cost-"
        "weighted prefix of any probe strategy triggered by the rule."
    )


if __name__ == "__main__":
    main()
