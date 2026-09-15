#!/usr/bin/env python3
"""Sample random safe 5-stone positions on 8x8 and write solver input.

Goal: estimate the population LOSS base rate independent of factorial selection.
"""
from __future__ import annotations

import random
import sys
from itertools import combinations
from pathlib import Path

N = 8
V = 64
OUT = Path(__file__).resolve().parents[1] / "artifacts" / "8x8-random-safe-5stone-sample.csv"


def xy(p: int) -> tuple[int, int]:
    return p % N, p // N


def det3(ax, ay, az, bx, by, bz, cx, cy, cz) -> int:
    return ax * (by * cz - bz * cy) - ay * (bx * cz - bz * cx) + az * (bx * cy - by * cx)


def is_forbidden4(a, b, c, d) -> bool:
    pts = [a, b, c, d]
    xs = [xy(p)[0] for p in pts]
    ys = [xy(p)[1] for p in pts]
    zs = [x * x + y * y for x, y in zip(xs, ys)]
    return det3(
        xs[1] - xs[0], ys[1] - ys[0], zs[1] - zs[0],
        xs[2] - xs[0], ys[2] - ys[0], zs[2] - zs[0],
        xs[3] - xs[0], ys[3] - ys[0], zs[3] - zs[0],
    ) == 0


def main() -> None:
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 20260915
    rng = random.Random(seed)

    # rejection sample: pick 5 distinct cells, reject if any 4-subset is forbidden
    samples = []
    seen = set()
    attempts = 0
    while len(samples) < target and attempts < target * 200:
        attempts += 1
        five = tuple(sorted(rng.sample(range(V), 5)))
        if five in seen:
            continue
        bad = False
        for quad in combinations(five, 4):
            if is_forbidden4(*quad):
                bad = True
                break
        if bad:
            continue
        seen.add(five)
        parent = list(five[:4])
        move = five[4]
        samples.append((parent, move))

    with OUT.open("w", encoding="utf-8", newline="") as f:
        f.write("canonical_parent,move,tag\n")
        for parent, move in samples:
            f.write(f"\"{parent[0]},{parent[1]},{parent[2]},{parent[3]}\",{move},random_safe5\n")

    print(f"wrote {len(samples)} samples to {OUT} (attempts={attempts}, seed={seed})")


if __name__ == "__main__":
    main()
