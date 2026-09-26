#!/usr/bin/env python3
"""n=6..10 の 12 点円・10 点円の族分解（F-AN の延長）。"""
from __future__ import annotations

import json
from collections import Counter
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "exploration"


def families(n: int, target_k: int) -> dict:
    pts = [(x, y) for y in range(n) for x in range(n)]
    seen = {}

    def from_quad(q):
        (x0, y0), (x1, y1), (x2, y2), _ = q
        A = (2 * (x1 - x0), 2 * (y1 - y0))
        B = (2 * (x2 - x0), 2 * (y2 - y0))
        rhs1 = x1 * x1 + y1 * y1 - x0 * x0 - y0 * y0
        rhs2 = x2 * x2 + y2 * y2 - x0 * x0 - y0 * y0
        det = A[0] * B[1] - A[1] * B[0]
        if det == 0:
            return None
        ox_num = rhs1 * B[1] - A[1] * rhs2
        oy_num = A[0] * rhs2 - rhs1 * B[0]
        r2 = (x0 * det - ox_num) ** 2 + (y0 * det - oy_num) ** 2

        def on(x, y):
            return (x * det - ox_num) ** 2 + (y * det - oy_num) ** 2 == r2

        lat = tuple(sorted(p for p in pts if on(*p)))
        ox = Fraction(ox_num, det)
        oy = Fraction(oy_num, det)
        r2f = (Fraction(x0) - ox) ** 2 + (Fraction(y0) - oy) ** 2
        return lat, (ox, oy), r2f

    for i in range(n * n):
        for j in range(i + 1, n * n):
            for k in range(j + 1, n * n):
                a = (i % n, i // n)
                b = (j % n, j // n)
                c = (k % n, k // n)
                if (b[0] - a[0]) * (c[1] - a[1]) == (b[1] - a[1]) * (c[0] - a[0]):
                    continue
                got = from_quad((a, b, c, a))
                if not got:
                    continue
                lat, cen, r2 = got
                if len(lat) == target_k and lat not in seen:
                    seen[lat] = {
                        "center": f"{cen[0]},{cen[1]}",
                        "r2": str(r2),
                    }
    by_r2 = Counter(v["r2"] for v in seen.values())
    return {
        "n": n,
        "k": target_k,
        "count": len(seen),
        "r2_hist": dict(by_r2),
    }


def main() -> None:
    rows = []
    for n in range(8, 12):
        for k in (10, 12):
            print(f"n={n} k={k}...", flush=True)
            r = families(n, k)
            print(r, flush=True)
            rows.append(r)
    path = OUT / "fact_circle_families_k10_k12.json"
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    main()
