#!/usr/bin/env python3
"""Retrospective R-external check of the early (3-stone) side of F-E.

This is NOT a preregistered population holdout. It reuses already-solved historical
3-stone states from search-cost-outcomes.csv that are outside the 8-stone root R.
The purpose is to test, at zero new solver cost, whether the previously observed
within-R early direction (lower Sigma d -> LOSS) is at least compatible with
independent historical labels.

Important limitation: the historical states were collected by several targeted
campaigns, so the sample is strongly selection-biased. The exact random-label p
reported below is therefore only descriptive conditional on this fixed set.
"""

from __future__ import annotations

import csv
import itertools
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "results" / "10x10" / "search-cost-outcomes.csv"
N = 10
POINTS = 100
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
    chunk: list[tuple[int, int, int, int]] = []

    def consume(items: list[tuple[int, int, int, int]]) -> None:
        c = np.asarray(items, dtype=np.int64)
        x, y = c % N, c // N
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
        if len(chunk) == 50_000:
            consume(chunk)
            chunk.clear()
    if chunk:
        consume(chunk)
    return counts


def canonical(points: tuple[int, ...]) -> tuple[int, ...]:
    best_mask: int | None = None
    best: tuple[int, ...] | None = None
    for k in range(8):
        out = []
        for p in points:
            x, y = p % N, p // N
            if k == 0:
                nx, ny = x, y
            elif k == 1:
                nx, ny = N - 1 - x, y
            elif k == 2:
                nx, ny = x, N - 1 - y
            elif k == 3:
                nx, ny = N - 1 - x, N - 1 - y
            elif k == 4:
                nx, ny = y, x
            elif k == 5:
                nx, ny = N - 1 - y, x
            elif k == 6:
                nx, ny = y, N - 1 - x
            else:
                nx, ny = N - 1 - y, N - 1 - x
            out.append(ny * N + nx)
        t = tuple(sorted(out))
        mask = sum(1 << p for p in t)
        if best_mask is None or mask < best_mask:
            best_mask, best = mask, t
    assert best is not None
    return best


def exact_lower_tail(scores: list[int], k: int, observed_sum: int) -> tuple[int, int, float]:
    dp = [defaultdict(int) for _ in range(k + 1)]
    dp[0][0] = 1
    for score in scores:
        for j in range(k - 1, -1, -1):
            for total, ways in list(dp[j].items()):
                dp[j + 1][total + score] += ways
    tail = sum(ways for total, ways in dp[k].items() if total <= observed_sum)
    denom = math.comb(len(scores), k)
    return tail, denom, tail / denom


def main() -> None:
    d = dangerous_counts()
    assert int(d.sum() // 4) == 54_441

    by_key: dict[tuple[int, ...], dict] = {}
    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            raw = tuple(int(x) for x in row["state"].split(",") if x)
            if len(raw) != 3:
                continue
            if set(raw) <= R:
                continue
            outcome = row["outcome"]
            if outcome not in {"WIN", "LOSS"}:
                continue

            key = canonical(raw)
            sigma = int(sum(d[p] for p in raw))
            old = by_key.get(key)
            if old is None:
                by_key[key] = {
                    "outcome": outcome,
                    "sigma": sigma,
                    "example": raw,
                    "source": row.get("source_file", ""),
                }
            else:
                if old["outcome"] != outcome:
                    raise RuntimeError(f"outcome conflict for {key}")
                if old["sigma"] != sigma:
                    raise RuntimeError(f"D4 sigma mismatch for {key}")

    vals = list(by_key.values())
    loss = [x for x in vals if x["outcome"] == "LOSS"]
    win = [x for x in vals if x["outcome"] == "WIN"]

    gt = eq = lt = 0
    for a in loss:
        for b in win:
            if a["sigma"] < b["sigma"]:
                lt += 1
            elif a["sigma"] == b["sigma"]:
                eq += 1
            else:
                gt += 1
    auc_low = (lt + 0.5 * eq) / (len(loss) * len(win))
    rank_biserial = 2 * auc_low - 1

    observed = sum(x["sigma"] for x in loss)
    tail, denom, p = exact_lower_tail([x["sigma"] for x in vals], len(loss), observed)

    print(f"unique R-external 3-stone states: {len(vals)}")
    print(f"LOSS/WIN: {len(loss)}/{len(win)}")
    print(f"mean Sigma d LOSS: {np.mean([x['sigma'] for x in loss]):.6f}")
    print(f"mean Sigma d WIN : {np.mean([x['sigma'] for x in win]):.6f}")
    print(f"mean diff LOSS-WIN: {np.mean([x['sigma'] for x in loss]) - np.mean([x['sigma'] for x in win]):.6f}")
    print(f"AUC(low Sigma d predicts LOSS): {auc_low:.12f}")
    print(f"rank-biserial: {rank_biserial:.12f}")
    print(f"exact lower-tail random-label p: {p:.12g} ({tail}/{denom})")
    print("LOSS states:")
    for x in sorted(loss, key=lambda z: z["sigma"]):
        print(f"  {x['example']} canonical={canonical(x['example'])} Sigma d={x['sigma']} source={x['source']}")

    assert (len(vals), len(loss), len(win)) == (480, 6, 474)
    assert abs(np.mean([x["sigma"] for x in loss]) - 5537.333333333333) < 1e-9
    assert abs(np.mean([x["sigma"] for x in win]) - 6195.459915611815) < 1e-9
    assert abs(auc_low - 0.90014064697609) < 1e-12
    assert (tail, denom) == (637_826_987, 16_462_322_007_600)


if __name__ == "__main__":
    main()
