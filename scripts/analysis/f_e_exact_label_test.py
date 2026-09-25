#!/usr/bin/env python3
"""Exact within-R label test for finding F-E.

Recomputes d(p), the number of dangerous (concyclic/collinear) quadruples
containing point p, directly from 10x10 geometry. Then tests how strongly
Sigma d separates LOSS from WIN among all 70 four-stone subsets of the fixed
8-stone root R.

The p-value is an exact conditional random-label test: the 70 states and the
observed number of LOSS labels (12) are fixed, and all C(70,12) placements of
those labels are treated as exchangeable. This quantifies within-R separation;
it is not a population-level significance claim because R was selected and the
70 overlapping subsets are structurally dependent.
"""

from __future__ import annotations

import csv
import itertools
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "results" / "10x10" / "four-stone-subsets-of-medium-loss.csv"
N = 10
POINTS = N * N
R = frozenset({90, 61, 2, 73, 69, 66, 13, 91})


def det3_batch(m: np.ndarray) -> np.ndarray:
    return (
        m[:, 0, 0] * (m[:, 1, 1] * m[:, 2, 2] - m[:, 1, 2] * m[:, 2, 1])
        - m[:, 0, 1] * (m[:, 1, 0] * m[:, 2, 2] - m[:, 1, 2] * m[:, 2, 0])
        + m[:, 0, 2] * (m[:, 1, 0] * m[:, 2, 1] - m[:, 1, 1] * m[:, 2, 0])
    )


def det4_batch(m: np.ndarray) -> np.ndarray:
    return (
        m[:, 0, 0] * det3_batch(m[:, 1:, 1:])
        - m[:, 0, 1] * det3_batch(m[:, [1, 2, 3]][:, :, [0, 2, 3]])
        + m[:, 0, 2] * det3_batch(m[:, [1, 2, 3]][:, :, [0, 1, 3]])
        - m[:, 0, 3] * det3_batch(m[:, 1:, :3])
    )


def dangerous_counts() -> np.ndarray:
    counts = np.zeros(POINTS, dtype=np.int64)
    chunk_size = 50_000
    chunk: list[tuple[int, int, int, int]] = []

    def consume(items: list[tuple[int, int, int, int]]) -> None:
        if not items:
            return
        c = np.asarray(items, dtype=np.int64)
        x = c % N
        y = c // N
        a = np.empty((len(c), 4, 4), dtype=np.int64)
        a[:, :, 0] = x * x + y * y
        a[:, :, 1] = x
        a[:, :, 2] = y
        a[:, :, 3] = 1
        bad = det4_batch(a) == 0
        if bad.any():
            np.add.at(counts, c[bad], 1)

    for quad in itertools.combinations(range(POINTS), 4):
        chunk.append(quad)
        if len(chunk) == chunk_size:
            consume(chunk)
            chunk.clear()
    consume(chunk)
    return counts


def exact_upper_tail(scores: list[int], selected_n: int, observed_sum: int) -> tuple[int, int, float]:
    dp = [defaultdict(int) for _ in range(selected_n + 1)]
    dp[0][0] = 1
    for score in scores:
        for k in range(selected_n - 1, -1, -1):
            for total, ways in list(dp[k].items()):
                dp[k + 1][total + score] += ways

    tail = sum(ways for total, ways in dp[selected_n].items() if total >= observed_sum)
    denom = math.comb(len(scores), selected_n)
    return tail, denom, tail / denom


def main() -> None:
    d = dangerous_counts()

    rows: list[tuple[int, str, tuple[int, ...]]] = []
    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            state = tuple(int(x) for x in row["state"].split(","))
            if len(state) != 4 or not set(state) <= R:
                raise RuntimeError(f"unexpected state: {state}")
            rows.append((int(sum(d[p] for p in state)), row["outcome"], state))

    if len(rows) != 70:
        raise RuntimeError(f"expected 70 states, got {len(rows)}")

    loss = [score for score, outcome, _ in rows if outcome == "LOSS"]
    win = [score for score, outcome, _ in rows if outcome == "WIN"]
    if (len(loss), len(win)) != (12, 58):
        raise RuntimeError(f"expected 12 LOSS / 58 WIN, got {len(loss)} / {len(win)}")

    observed_sum = sum(loss)
    tail, denom, p = exact_upper_tail([score for score, _, _ in rows], len(loss), observed_sum)

    gt = eq = 0
    for a in loss:
        for b in win:
            if a > b:
                gt += 1
            elif a == b:
                eq += 1
    auc = (gt + 0.5 * eq) / (len(loss) * len(win))
    rank_biserial = 2.0 * auc - 1.0

    loss_arr = np.asarray(loss, dtype=float)
    win_arr = np.asarray(win, dtype=float)
    pooled_sd = math.sqrt(
        ((len(loss) - 1) * loss_arr.var(ddof=1) + (len(win) - 1) * win_arr.var(ddof=1))
        / (len(loss) + len(win) - 2)
    )
    cohen_d = (loss_arr.mean() - win_arr.mean()) / pooled_sd
    hedges_correction = 1.0 - 3.0 / (4.0 * (len(loss) + len(win)) - 9.0)
    hedges_g = hedges_correction * cohen_d

    print("R point d(p):", {p: int(d[p]) for p in sorted(R)})
    print(f"LOSS n={len(loss)} mean={loss_arr.mean():.6f} range=[{min(loss)},{max(loss)}]")
    print(f"WIN  n={len(win)} mean={win_arr.mean():.6f} range=[{min(win)},{max(win)}]")
    print(f"observed LOSS score sum={observed_sum}")
    print(f"exact upper-tail random-label p={p:.12g} ({tail}/{denom})")
    print(f"AUC=P(LOSS>WIN)+0.5*tie={auc:.9f}")
    print(f"rank-biserial={rank_biserial:.9f}")
    print(f"Cohen d={cohen_d:.9f}; Hedges g={hedges_g:.9f}")

    # Frozen regression checks for F-E.
    assert {p: int(d[p]) for p in R} == {
        90: 1515, 61: 2289, 2: 1927, 73: 2395,
        69: 2080, 66: 2499, 13: 2289, 91: 1730,
    }
    assert abs(loss_arr.mean() - 8732.833333333334) < 1e-9
    assert abs(win_arr.mean() - 8285.275862068966) < 1e-9
    assert (min(loss), max(loss), min(win), max(win)) == (8033, 9472, 7252, 9263)
    assert (tail, denom) == (16738278615, 10638894058520)


if __name__ == "__main__":
    main()
