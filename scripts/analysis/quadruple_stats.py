#!/usr/bin/env python3
"""10×10盤の各点が含まれる「危険な4点組」(共円または共線) の数を数える。

整数行列式 | x^2+y^2  x  y  1 | が0になる4点組を列挙し、各点 id の出現回数を
カウントする。探索コストとの相関分析の入力にする。
"""
import itertools
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
N = 10
POINTS = N * N


def det3(m):
    """(n,3,3) int64 の行列式。"""
    return (
        m[:, 0, 0] * (m[:, 1, 1] * m[:, 2, 2] - m[:, 1, 2] * m[:, 2, 1])
        - m[:, 0, 1] * (m[:, 1, 0] * m[:, 2, 2] - m[:, 1, 2] * m[:, 2, 0])
        + m[:, 0, 2] * (m[:, 1, 0] * m[:, 2, 1] - m[:, 1, 1] * m[:, 2, 0])
    )


def det4(m):
    """(n,4,4) int64 行列式（余因子展開）。"""
    return (
        m[:, 0, 0] * det3(m[:, 1:, 1:])
        - m[:, 0, 1] * det3(m[:, [1, 2, 3]][:, :, [0, 2, 3]])
        + m[:, 0, 2] * det3(m[:, [1, 2, 3]][:, :, [0, 1, 3]])
        - m[:, 0, 3] * det3(m[:, 1:, :3])
    )


def main() -> None:
    import itertools

    combos = np.array(list(itertools.combinations(range(POINTS), 4)), dtype=np.int64)
    xs = combos % N
    ys = combos // N
    count = np.zeros(POINTS, dtype=np.int64)
    total_bad = 0
    CHUNK = 40_000
    for start in range(0, len(combos), CHUNK):
        c = combos[start : start + CHUNK]
        x = xs[start : start + CHUNK]
        y = ys[start : start + CHUNK]
        xx = x.astype(np.int64)
        yy = y.astype(np.int64)
        A = np.empty((len(c), 4, 4), dtype=np.int64)
        A[:, :, 0] = xx * xx + yy * yy
        A[:, :, 1] = x
        A[:, :, 2] = y
        A[:, :, 3] = 1
        det = det4(A)
        bad = det == 0
        nb = int(bad.sum())
        total_bad += nb
        if nb:
            np.add.at(count, c[bad], 1)

    print(f"total concyclic/collinear quadruples = {total_bad}")
    # ヒストグラムと top / bottom
    order = np.argsort(count)
    print("top 20 points by dangerous-quadruple count:")
    for i in order[-20:][::-1]:
        print(f"  id={i:2d} ({i%N},{i//N})  count={count[i]}")
    print("bottom 10:")
    for i in order[:10]:
        print(f"  id={i:2d} ({i%N},{i//N})  count={count[i]}")
    # 8石LOSSルート
    R = [90, 61, 2, 73, 69, 66, 13, 91]
    print("8石LOSSルート R の各点:")
    for i in sorted(R):
        print(f"  id={i:2d} ({i%N},{i//N})  count={count[i]}")
    print(f"  R の合計: {int(count[R].sum())}")


if __name__ == "__main__":
    main()