#!/usr/bin/env python3
"""n=13 の禁止4点組数と dens*n^2 延長。"""
import math
from itertools import combinations
import numpy as np

def det3(m):
    return (
        m[:, 0, 0] * (m[:, 1, 1] * m[:, 2, 2] - m[:, 1, 2] * m[:, 2, 1])
        - m[:, 0, 1] * (m[:, 1, 0] * m[:, 2, 2] - m[:, 1, 2] * m[:, 2, 0])
        + m[:, 0, 2] * (m[:, 1, 0] * m[:, 2, 1] - m[:, 1, 1] * m[:, 2, 0])
    )

def count_bad(n):
    V = n * n
    xs = (np.arange(V) % n).astype(np.int64)
    ys = (np.arange(V) // n).astype(np.int64)
    total = 0
    buf = []

    def flush():
        nonlocal total
        if not buf:
            return
        c = np.array(buf, dtype=np.int64)
        x, y = xs[c], ys[c]
        A = np.empty((len(c), 4, 4), dtype=np.int64)
        A[:, :, 0] = x * x + y * y
        A[:, :, 1] = x
        A[:, :, 2] = y
        A[:, :, 3] = 1
        m1 = A[:, 1:, 1:]
        m2 = A[:, 1:, :][:, :, [0, 2, 3]]
        m3 = A[:, 1:, :][:, :, [0, 1, 3]]
        m4 = A[:, 1:, :3]
        det = A[:, 0, 0] * det3(m1) - A[:, 0, 1] * det3(m2) + A[:, 0, 2] * det3(m3) - A[:, 0, 3] * det3(m4)
        total += int((det == 0).sum())
        buf.clear()

    for comb in combinations(range(V), 4):
        buf.append(comb)
        if len(buf) >= 80000:
            flush()
    flush()
    return total

for n in (13,):
    f = count_bad(n)
    dens = f / math.comb(n * n, 4)
    print(f"n={n} forbidden={f} dens*n2={dens*n*n:.4f} F/n6={f/n**6:.5f}", flush=True)
