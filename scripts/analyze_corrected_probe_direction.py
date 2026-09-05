#!/usr/bin/env python3
"""Exploratory direction check for the corrected 10x10 independent probe.

The confirmatory audit established that memo-desc is invalid/worse after
per-candidate memo isolation.  This script asks a separate, explicitly
POST-HOC question: does the same stored probe carry signal with the opposite
sign?

No solver is rerun.  It joins the already stored independent 1M-probe rows
against the already stored exact batch0 outcomes for the seven LOSS parents.

Rankings compared:
  memo_desc          larger independent memo first (the originally intended sign)
  memo_asc           smaller independent memo first
  outcome_aware_asc  probe-solved LOSS first, unresolved by memo ascending,
                     probe-solved WIN last

Random medians are exact order-statistic medians, not Monte-Carlo estimates.
This analysis is exploratory because the ascending direction was proposed only
after observing that descending performed badly.
"""

import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORR = ROOT / "results" / "10x10" / "blind-probe-corrected"
CHILD = ROOT / "results" / "10x10" / "blind_probe_children"
PARENTS = [
    "2,9,33", "4,9,33", "9,12,33", "9,19,33",
    "9,23,33", "0,31,36", "0,36,44",
]


def safe(s: str) -> str:
    return s.replace(",", "_")


def load_csv(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def q_first_loss_leq(r: int, m: int, l: int) -> float:
    if l <= 0:
        return 0.0
    if r >= m - l + 1:
        return 1.0
    return 1.0 - math.comb(m - r, l) / math.comb(m, l)


def exact_random_median(m: int, l: int) -> int:
    for r in range(1, m + 1):
        if q_first_loss_leq(r, m, l) >= 0.5:
            return r
    raise AssertionError((m, l))


def first_loss(order, exact):
    for i, state in enumerate(order, 1):
        if exact[state] == "LOSS":
            return i
    return len(order) + 1


def sign_test_two_sided(wins: int, losses: int):
    n = wins + losses
    if n == 0:
        return None
    k = min(wins, losses)
    p = 2 * sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, p)


def main():
    rows_out = []
    for parent in PARENTS:
        probe_rows = load_csv(CORR / f"independent_probe_{safe(parent)}.csv")
        exact_rows = load_csv(CHILD / f"exact_{safe(parent)}_batch0.csv")
        exact = {r["state"]: r["outcome"] for r in exact_rows}
        assert len(probe_rows) == 20
        assert set(r["state"] for r in probe_rows) == set(exact)

        file_pos = {r["state"]: i for i, r in enumerate(probe_rows)}
        memo = {r["state"]: int(r["memo"]) for r in probe_rows}
        probe_outcome = {r["state"]: r["outcome_probe"] for r in probe_rows}
        states = list(file_pos)
        m = len(states)
        l = sum(exact[s] == "LOSS" for s in states)

        desc = sorted(states, key=lambda s: (-memo[s], file_pos[s]))
        asc = sorted(states, key=lambda s: (memo[s], file_pos[s]))

        # If the bounded probe itself proves a child, use that proof directly.
        # For the remaining unresolved children, smaller memo means more revisits /
        # transposition hits under the fixed visited budget and is the exploratory
        # score tested here.
        bucket = {"LOSS": 0, "PROBE": 1, "WIN": 2}
        aware = sorted(
            states,
            key=lambda s: (bucket.get(probe_outcome[s], 1), memo[s], file_pos[s]),
        )

        r_desc = first_loss(desc, exact)
        r_asc = first_loss(asc, exact)
        r_aware = first_loss(aware, exact)
        random_med = exact_random_median(m, l)

        rows_out.append({
            "parent": parent,
            "m": m,
            "l": l,
            "memo_desc_rank": r_desc,
            "memo_asc_rank": r_asc,
            "outcome_aware_asc_rank": r_aware,
            "exact_random_median": random_med,
            "q_aware": q_first_loss_leq(r_aware, m, l),
            "probe_solved_win": sum(probe_outcome[s] == "WIN" for s in states),
            "probe_solved_loss": sum(probe_outcome[s] == "LOSS" for s in states),
        })

    fieldnames = list(rows_out[0])
    out_path = CORR / "probe-direction-analysis.csv"
    with out_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows_out)

    def compare(key):
        wins = sum(r[key] < r["exact_random_median"] for r in rows_out)
        losses = sum(r[key] > r["exact_random_median"] for r in rows_out)
        ties = len(rows_out) - wins - losses
        return wins, losses, ties, sign_test_two_sided(wins, losses)

    for key in ("memo_desc_rank", "memo_asc_rank", "outcome_aware_asc_rank"):
        w, l, t, p = compare(key)
        print(f"{key}: better={w} worse={l} tie={t} sign_test_two_sided_p={p}")
    print("ranks:")
    for r in rows_out:
        print(r)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
