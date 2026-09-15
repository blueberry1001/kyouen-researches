#!/usr/bin/env python3
"""Sample random safe k-stone positions on an N×N board for solver input.

Usage: python sample-k-stone.py N K COUNT SEED OUT.csv
"""
from __future__ import annotations

import random
import sys
from itertools import combinations
from pathlib import Path


def make_forbidden(N: int):
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

    return is_forbidden4


def is_safe(stones: tuple[int, ...], is_forbidden4) -> bool:
    for quad in combinations(stones, 4):
        if is_forbidden4(*quad):
            return False
    return True


def main() -> None:
    N = int(sys.argv[1])
    K = int(sys.argv[2])
    target = int(sys.argv[3])
    seed = int(sys.argv[4])
    out = Path(sys.argv[5])
    V = N * N
    if K < 2:
        raise SystemExit("need K>=2 to split parent/move")
    rng = random.Random(seed)
    is_forbidden4 = make_forbidden(N)
    samples: list[tuple[int, ...]] = []
    seen: set[tuple[int, ...]] = set()
    attempts = 0
    max_attempts = target * 500
    while len(samples) < target and attempts < max_attempts:
        attempts += 1
        stones = tuple(sorted(rng.sample(range(V), K)))
        if stones in seen:
            continue
        if not is_safe(stones, is_forbidden4):
            continue
        seen.add(stones)
        samples.append(stones)

    # Solver reads canonical_parent (any length) + move; state = parent ∪ {move}.
    with out.open("w", encoding="utf-8", newline="") as f:
        f.write("canonical_parent,move,tag\n")
        for stones in samples:
            parent = stones[:-1]
            move = stones[-1]
            f.write(
                f"\"{','.join(str(x) for x in parent)}\",{move},random_safe{K}\n"
            )
    print(f"N={N} K={K} wrote {len(samples)} to {out} attempts={attempts} seed={seed}")


if __name__ == "__main__":
    main()
