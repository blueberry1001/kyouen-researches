#!/usr/bin/env python3
"""120 二石軌道ごとの合法手数（mobility）を計算する。"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys_path = ROOT / "scripts" / "analysis"
import sys

sys.path.insert(0, str(sys_path))
from fact_10x10_maximal_sample import Engine, build_forbidden, PTS  # noqa: E402

N = 10
OUT = ROOT / "research" / "exploration"


def xy(p: int):
    return (p % N, p // N)


def d4_canon_pair(p: int, q: int) -> int:
    def images(x, y):
        n = N - 1
        return (
            (x, y),
            (n - x, y),
            (x, n - y),
            (n - x, n - y),
            (y, x),
            (n - y, x),
            (y, n - x),
            (n - y, n - x),
        )

    x1, y1 = xy(p)
    x2, y2 = xy(q)
    best = None
    for a in images(x1, y1):
        for b in images(x2, y2):
            ia, ib = a[1] * N + a[0], b[1] * N + b[0]
            if ia == ib:
                continue
            key = (min(ia, ib) << 8) | max(ia, ib)
            if best is None or key < best:
                best = key
    return best


def mobility(eng: Engine, occ: list[int]) -> int:
    s = set(occ)
    return sum(1 for p in range(PTS) if p not in s and eng.safe_add(s, p))


def main() -> None:
    quads = build_forbidden()
    eng = Engine(quads)
    # load orbit reps
    orbits = json.loads((OUT / "fact_10x10_two_stone_orbits.json").read_text(encoding="utf-8"))["orbits"]
    rows = []
    for o in orbits:
        p, q = o["rep"]
        mob = mobility(eng, [p, q])
        rows.append(
            {
                "orbit_key": o["orbit_key"],
                "rep": [p, q],
                "sum_d": o["sum_d"],
                "quads_containing_pair": o["quads_containing_pair"],
                "mobility": mob,
                "chebyshev": o["chebyshev"],
            }
        )
    mobs = [r["mobility"] for r in rows]
    print("mobility min/max/mean", min(mobs), max(mobs), sum(mobs) / len(mobs))
    # correlation sum_d vs mobility
    xs = [r["sum_d"] for r in rows]
    ys = mobs
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** 0.5
    print("corr(sum_d, mobility)", num / den)
    # lowest mobility
    rows_sorted = sorted(rows, key=lambda r: r["mobility"])
    print("lowest mobility", rows_sorted[:5])
    print("highest mobility", rows_sorted[-5:])
    path = OUT / "fact_10x10_two_stone_mobility.json"
    path.write_text(json.dumps({"rows": rows, "corr_sum_d_mobility": num / den}, indent=2), encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    main()
