#!/usr/bin/env python3
"""Audit the 3-stone blind-probe `memo desc` feature.

Checks two things:
1. `memo` in probe CSVs is cumulative across tasks and therefore monotone.
2. The resulting fixed ranking is exactly the reverse of solver input order.

Also computes an exact conditional permutation p-value for the observed
sum of first-LOSS positions across evaluated LOSS parents, conditioning on
(parent child_count, loss_child_count) for each parent.
"""

import csv
import math
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "10x10"
CHILDREN = RESULTS / "blind_probe_children"
RANKINGS = RESULTS / "blind-probe-rankings.csv"
SUMMARY = RESULTS / "blind-probe-results.csv"


def first_loss_dist(m: int, l: int) -> dict[int, Fraction]:
    """Exact distribution of first marked position in random permutation."""
    if not (1 <= l <= m):
        raise ValueError((m, l))
    den = math.comb(m, l)
    return {
        r: Fraction(math.comb(m - r, l - 1), den)
        for r in range(1, m - l + 2)
    }


def convolve(a: dict[int, Fraction], b: dict[int, Fraction]) -> dict[int, Fraction]:
    out = defaultdict(Fraction)
    for x, px in a.items():
        for y, py in b.items():
            out[x + y] += px * py
    return dict(out)


def main() -> None:
    with SUMMARY.open(newline="") as f:
        summary = list(csv.DictReader(f))
    with RANKINGS.open(newline="") as f:
        rankings = list(csv.DictReader(f))

    rank_by_parent = defaultdict(list)
    for r in rankings:
        rank_by_parent[r["parent"]].append(r)

    audited = []
    for row in summary:
        if int(row["stones"]) != 3:
            continue
        parent = row["parent"]
        safe = parent.replace(",", "_")
        probe = CHILDREN / f"probe_{safe}_batch0_1000000.csv"
        if not probe.exists():
            continue
        with probe.open(newline="") as f:
            prows = list(csv.DictReader(f))
        memos = [int(r["memo"]) for r in prows]
        strict_inc = all(a < b for a, b in zip(memos, memos[1:]))

        rr = rank_by_parent[parent]
        reverse_exact = bool(rr) and all(
            int(r["fixed_rank"]) + int(r["solver_default_rank"]) == len(rr) + 1
            for r in rr
        )
        audited.append((parent, len(prows), strict_inc, reverse_exact,
                        memos[0] if memos else None,
                        memos[-1] if memos else None))

    print("parent,n,strictly_increasing_memo,fixed_is_exact_reverse,first_memo,last_memo")
    for rec in audited:
        print(",".join(map(str, rec)))

    # Main blind report excludes parents with zero observed LOSS in batch0.
    eval_rows = [
        r for r in summary
        if int(r["stones"]) == 3
        and str(r["lopo_source_used"]).lower() == "false"
        and int(r["loss_child_count"]) > 0
    ]
    obs = sum(int(r["fixed_first_loss_position"]) for r in eval_rows)
    dist = {0: Fraction(1)}
    expected = 0.0
    for r in eval_rows:
        m = int(r["child_count"])
        l = int(r["loss_child_count"])
        d = first_loss_dist(m, l)
        dist = convolve(dist, d)
        expected += (m + 1) / (l + 1)
    p_le = sum(prob for total, prob in dist.items() if total <= obs)

    print()
    print(f"evaluated_loss_parents={len(eval_rows)}")
    print(f"observed_sum_first_loss={obs}")
    print(f"null_expected_sum_first_loss={expected:.6f}")
    print(f"exact_one_sided_p_sum_le_observed={float(p_le):.12f}")

    if audited and all(x[2] and x[3] for x in audited):
        print("AUDIT_RESULT: 3-stone memo-desc ranking is an input-order reversal artifact")
    else:
        print("AUDIT_RESULT: mixed; inspect rows above")


if __name__ == "__main__":
    main()
