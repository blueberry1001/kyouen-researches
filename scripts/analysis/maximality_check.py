#!/usr/bin/env python3
"""4石局面でも Σd と探索コストの負相関が再現するか確認する。

あわせて、8石LOSSルート R の極大性 (R+任意の1点が安全でない) をチェックする。
"""
import csv
import itertools
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "results" / "10x10"
N = 10
R = {90, 61, 2, 73, 69, 66, 13, 91}


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


def main() -> None:
    d = np.load(ROOT / "scratch" / "d_per_point.npy")

    # 4石の相関
    rows = []
    with open(RES / "four-stone-subsets-of-medium-loss.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["classification_source"] != "EXACT_INDEPENDENT_SEARCH":
                continue
            if not r["visited"]:
                continue
            stones = [int(x) for x in r["state"].split(",")]
            rows.append((int(r["visited"]), stones, r["outcome"]))
    v = np.array([x[0] for x in rows], dtype=float)
    sd = np.array([sum(int(d[i]) for i in x[1]) for x in rows], dtype=float)
    print(f"4石: n={len(rows)}  log10(visited) vs Σd = {np.corrcoef(np.log10(v), sd)[0,1]:+.3f}")
    # LOSS のみでも
    vL = np.array([x[0] for x in rows if x[2] == "LOSS"], dtype=float)
    sdL = np.array([sum(int(d[i]) for i in x[1]) for x in rows if x[2] == "LOSS"], dtype=float)
    if len(vL) >= 4:
        print(f"4石LOSSのみ: n={len(vL)} 相関 = {np.corrcoef(np.log10(vL), sdL)[0,1]:+.3f}")

    # 3石: 90/91 の有無で分割したときの visited 差
    rows3 = []
    with open(RES / "three-stone-subsets-of-medium-loss.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["classification_source"] != "EXACT_INDEPENDENT_SEARCH":
                continue
            if not r["visited"]:
                continue
            stones = [int(x) for x in r["state"].split(",")]
            rows3.append((int(r["visited"]), stones, r["outcome"]))
    with90 = [x[0] for x in rows3 if 90 in x[1]]
    with91 = [x[0] for x in rows3 if 91 in x[1]]
    withBoth = [x[0] for x in rows3 if 90 in x[1] and 91 in x[1]]
    neither = [x[0] for x in rows3 if 90 not in x[1] and 91 not in x[1]]
    import statistics
    print("\n3石 visited の分割 (90/91 の有無):")
    print(f"  90を含む   n={len(with90)}  中央値={statistics.median(with90):,}  最大={max(with90):,}")
    print(f"  91を含む   n={len(with91)}  中央値={statistics.median(with91):,}  最大={max(with91):,}")
    print(f"  両方含む   n={len(withBoth)}  中央値={statistics.median(withBoth):,}  最大={max(withBoth):,}")
    print(f"  含まない   n={len(neither)}  中央値={statistics.median(neither):,}  最大={max(neither):,}")
    # 4石でも 90/91 で分割
    with90_4 = [x[0] for x in rows if 90 in x[1]]
    neither_4 = [x[0] for x in rows if 90 not in x[1] and 91 not in x[1]]
    print("\n4石 visited の分割:")
    print(f"  90/91含む   n={len(rows)-len(neither_4)}  中央値={statistics.median([x[0] for x in rows if 90 in x[1] or 91 in x[1]]):,}")
    print(f"  含まない   n={len(neither_4)}  中央値={statistics.median(neither_4):,}")

    # 8石LOSSルート R の極大性: R ∪ {p} が安全か
    safe_ext = []
    for p in range(100):
        if p in R:
            continue
        S = sorted(R | {p})
        ok = True
        for q in itertools.combinations(S, 4):
            if dangerous(*q):
                ok = False
                break
        if ok:
            safe_ext.append(p)
    print(f"R に追加しても安全な1点: {safe_ext}")
    if safe_ext:
        for p in safe_ext:
            print(f"  R ∪ {{{p}}} は安全配置 (9石)")
    else:
        print("R は極大安全配置 (どの1点を加えても共円/共線が発生)")


if __name__ == "__main__":
    main()