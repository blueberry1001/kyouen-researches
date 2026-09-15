#!/usr/bin/env python3
"""Independent brute-force WIN/LOSS for late 8x8 states (validation only).

Semantics: current player to move; WIN iff exists a legal move leading to a
LOSS for the opponent. Terminal (no legal moves) = LOSS.
D4-canonicalized memo to keep the tree tractable.
"""
from __future__ import annotations

import sys
from functools import lru_cache

N = 8
V = 64


def det3(a, b, c, d, e, f, g, h, i):
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def forbidden4(a, b, c, d):
    p = (a, b, c, d)
    xs = [q % N for q in p]
    ys = [q // N for q in p]
    zs = [x * x + y * y for x, y in zip(xs, ys)]
    return (
        det3(
            xs[1] - xs[0], ys[1] - ys[0], zs[1] - zs[0],
            xs[2] - xs[0], ys[2] - ys[0], zs[2] - zs[0],
            xs[3] - xs[0], ys[3] - ys[0], zs[3] - zs[0],
        ) == 0
    )


# Precompute completion[sorted triple] = bitmask of 4th points.
completion = [0] * (V * V * V)


def tidx(a, b, c):
    if a > b: a, b = b, a
    if b > c: b, c = c, b
    if a > b: a, b = b, a
    return (a * V + b) * V + c


forbidden_count = 0
for a in range(V):
    for b in range(a + 1, V):
        for c in range(b + 1, V):
            for d in range(c + 1, V):
                if not forbidden4(a, b, c, d):
                    continue
                forbidden_count += 1
                q = (a, b, c, d)
                for omit in range(4):
                    t = [q[j] for j in range(4) if j != omit]
                    completion[tidx(*t)] |= 1 << q[omit]


def d4_images(stones):
    images = []
    for g in range(8):
        q = []
        for v in stones:
            x, y = v % N, v // N
            nm1 = N - 1
            if g == 0: nx, ny = x, y
            elif g == 1: nx, ny = nm1 - y, x
            elif g == 2: nx, ny = nm1 - x, nm1 - y
            elif g == 3: nx, ny = y, nm1 - x
            elif g == 4: nx, ny = nm1 - x, y
            elif g == 5: nx, ny = x, nm1 - y
            elif g == 6: nx, ny = y, x
            else: nx, ny = nm1 - y, nm1 - x
            q.append(ny * N + nx)
        images.append(tuple(sorted(q)))
    return min(images)


@lru_cache(maxsize=None)
def danger_mask(stones: tuple[int, ...]) -> int:
    stones = tuple(stones)
    k = len(stones)
    m = 0
    for i in range(k):
        for j in range(i + 1, k):
            for l in range(j + 1, k):
                m |= completion[tidx(stones[i], stones[j], stones[l])]
    return m


@lru_cache(maxsize=None)
def is_win(stones: tuple[int, ...]) -> bool:
    stones = tuple(stones)
    key = d4_images(stones)
    if key != stones:
        # re-enter with canonical; results identical
        return is_win(key)
    occupied = 0
    for v in stones:
        occupied |= 1 << v
    legal = ((1 << V) - 1) & ~occupied & ~danger_mask(stones)
    if legal == 0:
        return False
    seen_canon = set()
    moves = legal
    while moves:
        v = (moves & -moves).bit_length() - 1
        moves &= moves - 1
        nxt = tuple(sorted(stones + (v,)))
        canon = d4_images(nxt)
        if canon in seen_canon:
            continue
        seen_canon.add(canon)
        if not is_win(canon):
            return True
    return False


def main():
    path = sys.argv[1]
    # rebuild completion already done at import
    print(f"forbidden_count={forbidden_count}", file=sys.stderr)
    with open(path, newline="") as f:
        header = f.readline()
        for line in f:
            line = line.strip()
            if not line:
                continue
            # "p0,p1,...",move,tag
            q1 = line.find('"')
            q2 = line.find('"', q1 + 1)
            parent = tuple(int(x) for x in line[q1 + 1 : q2].split(","))
            rest = line[q2 + 2 :]
            move = int(rest.split(",")[0])
            stones = tuple(sorted(parent + (move,)))
            w = is_win(stones)
            print(f"{','.join(map(str,parent))},{move},{ 'WIN' if w else 'LOSS' }")


if __name__ == "__main__":
    main()
