#!/usr/bin/env python3
"""3石局面の探索コストと、危険4点組数・合法手数との相関を分析する。

- d(p): 点 p を含む危険4点組の数
- legal(s): 状態 s での合法手数 (共円を作らない空き点の数)
"""
import csv
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "results" / "10x10"
N = 10


def det3(m):
    return (
        m[0, 0] * (m[1, 1] * m[2, 2] - m[1, 2] * m[2, 1])
        - m[0, 1] * (m[1, 0] * m[2, 2] - m[1, 2] * m[2, 0])
        + m[0, 2] * (m[1, 0] * m[2, 1] - m[1, 1] * m[2, 0])
    )


def det4(a):
    return (
        a[0, 0] * det3(a[1:, 1:])
        - a[0, 1] * det3(a[[1, 2, 3]][:, [0, 2, 3]])
        + a[0, 2] * det3(a[[1, 2, 3]][:, [0, 1, 3]])
        - a[0, 3] * det3(a[1:, :3])
    )


def dangerous(p, q, r, s):
    P = np.array([[p % N, p // N], [q % N, q // N], [r % N, r // N], [s % N, s // N]], dtype=np.int64)
    A = np.empty((4, 4), dtype=np.int64)
    A[:, 0] = P[:, 0] ** 2 + P[:, 1] ** 2
    A[:, 1] = P[:, 0]
    A[:, 2] = P[:, 1]
    A[:, 3] = 1
    return det4(A) == 0


def legal_moves(stones):
    """状態 stones (frozenset) での合法手数。"""
    n = 0
    for p in range(100):
        if p in stones:
            continue
        ok = True
        # 既存3石との組で共円になるか
        s = list(stones)
        for i in range(len(s)):
            for j in range(i + 1, len(s)):
                if dangerous(s[i], s[j], s[len(s) - 1], p) if False else False:
                    pass
        # 全3点組でチェック
        for i in range(len(s)):
            for j in range(i + 1, len(s)):
                for k in range(j + 1, len(s)):
                    if dangerous(s[i], s[j], s[k], p):
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                break
        if ok:
            n += 1
    return n


def main() -> None:
    # 危険4点組数 d(p) を再計算 (軽量版は組み合わせ数が多いので事前計算ファイルから)
    dfile = ROOT / "scratch" / "d_per_point.npy"
    if dfile.exists():
        d = np.load(dfile)
    else:
        import itertools

        combos = np.array(list(itertools.combinations(range(100), 4)), dtype=np.int64)
        xs = combos % N
        ys = combos // N
        d = np.zeros(100, dtype=np.int64)
        CH = 20_000
        for st in range(0, len(combos), CH):
            c = combos[st : st + CH]
            x = xs[st : st + CH].astype(np.int64)
            y = ys[st : st + CH].astype(np.int64)
            A = np.empty((len(c), 4, 4), dtype=np.int64)
            A[:, :, 0] = x * x + y * y
            A[:, :, 1] = x
            A[:, :, 2] = y
            A[:, :, 3] = 1
            # det4 を numpy で
            m = A
            det = (
                m[:, 0, 0] * (m[:, 1, 1] * m[:, 2, 2] * m[:, 3, 3] + m[:, 1, 2] * m[:, 2, 3] * m[:, 3, 1] + m[:, 1, 3] * m[:, 2, 1] * m[:, 3, 2]
                             - m[:, 1, 3] * m[:, 2, 2] * m[:, 3, 1] - m[:, 1, 1] * m[:, 2, 3] * m[:, 3, 2] - m[:, 1, 2] * m[:, 2, 1] * m[:, 3, 3])
                - m[:, 0, 1] * (m[:, 1, 0] * m[:, 2, 2] * m[:, 3, 3] + m[:, 1, 2] * m[:, 2, 3] * m[:, 3, 0] + m[:, 1, 3] * m[:, 2, 0] * m[:, 3, 2]
                             - m[:, 1, 3] * m[:, 2, 2] * m[:, 3, 0] - m[:, 1, 0] * m[:, 2, 3] * m[:, 3, 2] - m[:, 1, 2] * m[:, 2, 0] * m[:, 3, 3])
                + m[:, 0, 2] * (m[:, 1, 0] * m[:, 2, 1] * m[:, 3, 3] + m[:, 1, 1] * m[:, 2, 3] * m[:, 3, 0] + m[:, 1, 3] * m[:, 2, 0] * m[:, 3, 1]
                             - m[:, 1, 3] * m[:, 2, 1] * m[:, 3, 0] - m[:, 1, 0] * m[:, 2, 3] * m[:, 3, 1] - m[:, 1, 1] * m[:, 2, 0] * m[:, 3, 3])
                - m[:, 0, 3] * (m[:, 1, 0] * m[:, 2, 1] * m[:, 3, 2] + m[:, 1, 1] * m[:, 2, 2] * m[:, 3, 0] + m[:, 1, 2] * m[:, 2, 0] * m[:, 3, 1]
                             - m[:, 1, 2] * m[:, 2, 1] * m[:, 3, 0] - m[:, 1, 0] * m[:, 2, 2] * m[:, 3, 1] - m[:, 1, 1] * m[:, 2, 0] * m[:, 3, 2])
            )
            bad = det == 0
            if bad.any():
                np.add.at(d, c[bad], 1)
        dfile.parent.mkdir(parents=True, exist_ok=True)
        np.save(dfile, d)

    print(f"d(p) 保存済み: {dfile}")
    print("各点の d(p):")
    for i in range(100):
        print(f"  id={i:2d} ({i%N},{i//N}) d={d[i]}")

    # 3石の visited と Σd, 合法手数の相関
    rows = []
    with open(RES / "three-stone-subsets-of-medium-loss.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["classification_source"] != "EXACT_INDEPENDENT_SEARCH":
                continue
            if not r["visited"]:
                continue
            stones = frozenset(int(x) for x in r["state"].split(","))
            rows.append((int(r["visited"]), stones, r["outcome"]))

    print("\nvisited / Σd / 合法手数 (上位12):")
    data = []
    for visited, stones, out in rows:
        sd = int(sum(d[i] for i in stones))
        legal = legal_moves(stones)
        data.append((visited, sd, legal, sorted(stones), out))
    data.sort(reverse=True)
    for visited, sd, legal, stones, out in data[:12]:
        print(f"  visited={visited:>12,}  Σd={sd:5d}  legal={legal:2d}  {stones}  {out}")

    v = np.array([x[0] for x in data], dtype=float)
    sd = np.array([x[1] for x in data], dtype=float)
    lg = np.array([x[2] for x in data], dtype=float)
    print("\nピアソン相関:")
    print(f"  log10(visited) vs Σd : {np.corrcoef(np.log10(v), sd)[0,1]:+.3f}")
    print(f"  log10(visited) vs legal: {np.corrcoef(np.log10(v), lg)[0,1]:+.3f}")
    print(f"  log10(visited) vs log(legal): {np.corrcoef(np.log10(v), np.log10(lg))[0,1]:+.3f}")
    print(f"  legal vs Σd: {np.corrcoef(lg, sd)[0,1]:+.3f}")


if __name__ == "__main__":
    main()