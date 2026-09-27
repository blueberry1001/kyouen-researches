#!/usr/bin/env python3
"""9×9 円サイズ分布（10×10 との比較用）。"""
from __future__ import annotations

import itertools
import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "exploration"


def spectrum(n: int) -> dict:
    pts = [(x, y) for y in range(n) for x in range(n)]

    def det3(r0, r1, r2):
        return (
            r0[0] * (r1[1] * r2[2] - r1[2] * r2[1])
            - r0[1] * (r1[0] * r2[2] - r1[2] * r2[0])
            + r0[2] * (r1[0] * r2[1] - r1[1] * r2[0])
        )

    quads = []
    for a, b, c, d in itertools.combinations(pts, 4):
        x0, y0 = a
        x1, y1 = b
        x2, y2 = c
        x3, y3 = d
        A = (
            (x0 * x0 + y0 * y0, x0, y0, 1),
            (x1 * x1 + y1 * y1, x1, y1, 1),
            (x2 * x2 + y2 * y2, x2, y2, 1),
            (x3 * x3 + y3 * y3, x3, y3, 1),
        )
        det = (
            A[0][0] * det3(A[1][1:], A[2][1:], A[3][1:])
            - A[0][1] * det3((A[1][0], A[1][2], A[1][3]), (A[2][0], A[2][2], A[2][3]), (A[3][0], A[3][2], A[3][3]))
            + A[0][2] * det3((A[1][0], A[1][1], A[1][3]), (A[2][0], A[2][1], A[2][3]), (A[3][0], A[3][1], A[3][3]))
            - A[0][3] * det3((A[1][0], A[1][1], A[1][2]), (A[2][0], A[2][1], A[2][2]), (A[3][0], A[3][1], A[3][2]))
        )
        if det == 0:
            quads.append((a, b, c, d))

    def is_col(q):
        (x0, y0), (x1, y1), (x2, y2), (x3, y3) = q
        return (x1 - x0) * (y2 - y0) == (y1 - y0) * (x2 - x0) and (x1 - x0) * (y3 - y0) == (y1 - y0) * (x3 - x0)

    def circum_lattice(q):
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

        return tuple(sorted(p for p in pts if on(*p)))

    n_col = n_circ = 0
    sizes = Counter()
    seen = set()
    for q in quads:
        if is_col(q):
            n_col += 1
        else:
            n_circ += 1
            key = circum_lattice(q)
            if key is not None and key not in seen:
                seen.add(key)
                sizes[len(key)] += 1
    return {
        "board": f"{n}x{n}",
        "forbidden_total": len(quads),
        "collinear_quads": n_col,
        "concyclic_quads": n_circ,
        "unique_circles": len(seen),
        "circle_lattice_size_hist": {str(k): int(v) for k, v in sorted(sizes.items())},
    }


def main() -> None:
    out = []
    for n in (8, 9, 10):
        print(f"n={n}...", flush=True)
        out.append(spectrum(n))
        print(out[-1], flush=True)
    path = OUT / "fact_circle_spectrum_n8_n9_n10.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    main()
