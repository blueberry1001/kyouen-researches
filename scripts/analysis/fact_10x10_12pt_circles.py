#!/usr/bin/env python3
"""10×10 上の 12 格子点円 9 個の幾何を記述する。"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "exploration"
N = 10


def main() -> None:
    pts = [(x, y) for y in range(N) for x in range(N)]

    def on_circle_set_from_quad(q):
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
            dx = x * det - ox_num
            dy = y * det - oy_num
            return dx * dx + dy * dy == r2

        lattice = tuple(sorted(p for p in pts if on(*p)))
        # center as rational
        from fractions import Fraction

        ox = Fraction(ox_num, det)
        oy = Fraction(oy_num, det)
        # radius^2 as Fraction
        # (x0-ox)^2+(y0-oy)^2
        r2f = (Fraction(x0) - ox) ** 2 + (Fraction(y0) - oy) ** 2
        return lattice, (ox, oy), r2f

    # Enumerate all circles by taking triples of points and collecting unique lattice sets of size 12
    seen = {}
    for i in range(N * N):
        for j in range(i + 1, N * N):
            for k in range(j + 1, N * N):
                a = (i % N, i // N)
                b = (j % N, j // N)
                c = (k % N, k // N)
                # collinear skip
                if (b[0] - a[0]) * (c[1] - a[1]) == (b[1] - a[1]) * (c[0] - a[0]):
                    continue
                got = on_circle_set_from_quad((a, b, c, a))
                if got is None:
                    continue
                lattice, center, r2 = got
                if len(lattice) == 12 and lattice not in seen:
                    seen[lattice] = {
                        "points": [list(p) for p in lattice],
                        "center": [str(center[0]), str(center[1])],
                        "center_half_int": (center[0].denominator == 2 and center[1].denominator == 2),
                        "center_int": (center[0].denominator == 1 and center[1].denominator == 1),
                        "r2": str(r2),
                        "r2_float": float(r2),
                        "bbox": [
                            min(p[0] for p in lattice),
                            min(p[1] for p in lattice),
                            max(p[0] for p in lattice),
                            max(p[1] for p in lattice),
                        ],
                    }

    print("n_12pt_circles", len(seen))
    from collections import Counter as C

    ch = C()
    for v in seen.values():
        ch[(v["center_half_int"], v["center_int"])] += 1
    print("center types", ch)
    r2s = sorted({v["r2"] for v in seen.values()})
    print("r2 values", r2s)
    for v in sorted(seen.values(), key=lambda z: z["r2_float"]):
        print(v["center"], "r2=", v["r2"], "bbox=", v["bbox"])

    payload = {
        "board": "10x10",
        "n_12pt_circles": len(seen),
        "circles": list(seen.values()),
    }
    path = OUT / "fact_10x10_12pt_circles.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    main()
