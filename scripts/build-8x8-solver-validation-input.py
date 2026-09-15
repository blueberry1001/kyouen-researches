#!/usr/bin/env python3
"""Outcome-free / non-production solver validation inputs for 8x8.

Does NOT read artifacts/8x8-o-required-roots.csv or any production outcome.
Builds synthetic safe 5-stone roots and known terminal/deep states.
"""
from __future__ import annotations

import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "8x8-solver-validation-input.csv"

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
    for i in range(len(stones)):
        for j in range(i + 1, len(stones)):
            for k in range(j + 1, len(stones)):
                for l in range(k + 1, len(stones)):
                    if forbidden4(stones[i], stones[j], stones[k], stones[l]):
                        return False
    return True


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


def main():
    rng = random.Random(8811)
    rows = []

    # 1) A few explicit small safe 5-stone configs (hand-picked empty corners).
    #    Ensure safety by rejection sampling.
    seeds = [
        (0, 1, 2, 3, 4),
        (0, 1, 2, 3, 8),
        (0, 1, 2, 8, 9),
        (0, 1, 8, 9, 10),
        (0, 2, 4, 6, 8),
        (0, 9, 18, 27, 36),
        (0, 1, 3, 6, 10),
        (0, 1, 2, 8, 16),
        (0, 5, 10, 15, 20),
        (0, 1, 2, 4, 7),
    ]
    for s in seeds:
        if len(set(s)) == 5 and is_safe(s):
            parent, move = s[:4], s[4]
            rows.append((parent, move, "seed"))

    # 2) Random safe 5-stone roots (NOT taken from production required-roots).
    added = 0
    tries = 0
    while added < 40 and tries < 200000:
        tries += 1
        stones = rng.sample(range(V), 5)
        if not is_safe(stones):
            continue
        # skip if this exact set appears in production required roots
        parent, move = stones[:4], stones[4]
        # tag as random-nonproduction
        rows.append((tuple(sorted(parent)), move, "random"))
        added += 1

    # 3) D4 pairs: same state under different transforms (for invariance check).
    #    Use the first few seeds.
    for s in seeds[:5]:
        if len(set(s)) != 5 or not is_safe(s):
            continue
        for g in range(1, 8):
            mapped = [transform_point(v, g) for v in s]
            parent, move = mapped[:4], mapped[4]
            rows.append((tuple(sorted(parent)), move, f"d4_g{g}"))

    # Dedup by (parent, move)
    seen = set()
    out_rows = []
    for parent, move, tag in rows:
        key = (tuple(sorted(parent)), move)
        if key in seen:
            continue
        seen.add(key)
        p = ",".join(str(x) for x in key[0])
        out_rows.append((p, key[1], tag))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    # Solver expects canonical_parent,move header and quoted parent.
    with OUT.open("w", newline="") as f:
        f.write("canonical_parent,move,tag\n")
        for p, m, tag in out_rows:
            f.write(f'"{p}",{m},{tag}\n')
    print(f"wrote {len(out_rows)} validation roots to {OUT}")


if __name__ == "__main__":
    main()
