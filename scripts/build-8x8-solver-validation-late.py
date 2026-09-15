#!/usr/bin/env python3
"""Build late-game 8x8 validation roots (many stones) for cheap exact checks."""
from __future__ import annotations

import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "8x8-solver-validation-late.csv"
N = 8
V = 64


def det3(a, b, c, d, e, f, g, h, i):
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def forbidden4(a, b, c, d):
    p = [a, b, c, d]
    xs, ys, zs = [], [], []
    for q in p:
        x, y = q % N, q // N
        xs.append(x)
        ys.append(y)
        zs.append(x * x + y * y)
    return (
        det3(
            xs[1] - xs[0],
            ys[1] - ys[0],
            zs[1] - zs[0],
            xs[2] - xs[0],
            ys[2] - ys[0],
            zs[2] - zs[0],
            xs[3] - xs[0],
            ys[3] - ys[0],
            zs[3] - zs[0],
        )
        == 0
    )


def is_safe(stones):
    k = len(stones)
    for i in range(k):
        for j in range(i + 1, k):
            for a in range(j + 1, k):
                for b in range(a + 1, k):
                    if forbidden4(stones[i], stones[j], stones[a], stones[b]):
                        return False
    return True


def greedy_safe_fill(rng, target):
    stones = []
    cells = list(range(V))
    rng.shuffle(cells)
    for v in cells:
        trial = stones + [v]
        if is_safe(trial):
            stones.append(v)
            if len(stones) >= target:
                break
    return stones


def main():
    rng = random.Random(4242)
    rows = []
    # Late states: greedy fill reaches ~10-13 stones on 8x8.
    for target in range(8, 14):
        for rep in range(4):
            stones = greedy_safe_fill(rng, target)
            if len(stones) < target:
                continue
            parent = tuple(sorted(stones[:-1]))
            move = stones[-1]
            rows.append((parent, move, f"late{len(stones)}"))

    # D4 invariance pairs on a few late states.
    def transform_point(v, g):
        x, y = v % N, v // N
        nm1 = N - 1
        table = [
            (x, y),
            (nm1 - y, x),
            (nm1 - x, nm1 - y),
            (y, nm1 - x),
            (nm1 - x, y),
            (x, nm1 - y),
            (y, x),
            (nm1 - y, nm1 - x),
        ]
        nx, ny = table[g]
        return ny * N + nx

    base_late = greedy_safe_fill(rng, 12)
    if len(base_late) >= 12:
        for g in range(8):
            mapped = [transform_point(v, g) for v in base_late]
            parent = tuple(sorted(mapped[:-1]))
            move = mapped[-1]
            rows.append((parent, move, f"d4g{g}_late12"))

    seen = set()
    out = []
    for parent, move, tag in rows:
        key = (parent, move)
        if key in seen:
            continue
        seen.add(key)
        out.append((parent, move, tag))

    with OUT.open("w", newline="") as f:
        f.write("canonical_parent,move,tag\n")
        for parent, move, tag in out:
            f.write(f'"{",".join(map(str, parent))}",{move},{tag}\n')
    print(f"wrote {len(out)} late validation roots to {OUT}")


if __name__ == "__main__":
    main()
