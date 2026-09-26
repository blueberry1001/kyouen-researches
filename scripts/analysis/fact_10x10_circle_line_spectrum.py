#!/usr/bin/env python3
"""10×10 円上格子点サイズ分布と直線ラン長。"""
from __future__ import annotations

import itertools
import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "exploration"


def main() -> None:
    N = 10
    pts = [(x, y) for y in range(N) for x in range(N)]

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
    print("forbidden", len(quads), flush=True)

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

    col_dirs = Counter()
    circle_size_hist = Counter()
    seen = set()
    n_col = n_circ = 0
    contrib = {}
    for q in quads:
        if is_col(q):
            n_col += 1
            (x0, y0), (x1, y1) = q[0], q[1]
            dx, dy = x1 - x0, y1 - y0
            g = math.gcd(abs(dx), abs(dy)) or 1
            dx, dy = dx // g, dy // g
            if dx < 0 or (dx == 0 and dy < 0):
                dx, dy = -dx, -dy
            col_dirs[(dx, dy)] += 1
        else:
            n_circ += 1
            key = circum_lattice(q)
            if key is None:
                continue
            if key not in seen:
                seen.add(key)
                circle_size_hist[len(key)] += 1
            contrib[key] = contrib.get(key, 0) + 1

    sum_c = 0
    complete_circles = 0
    partial_circles = 0
    size_complete = Counter()
    size_partial = Counter()
    for key, nq in contrib.items():
        k = len(key)
        full = math.comb(k, 4) if k >= 4 else 0
        sum_c += full
        if nq == full:
            complete_circles += 1
            size_complete[k] += 1
        else:
            partial_circles += 1
            size_partial[k] += 1

    payload = {
        "board": "10x10",
        "forbidden_total": len(quads),
        "collinear_quads": n_col,
        "concyclic_quads": n_circ,
        "collinear_by_dir": {f"{a},{b}": int(c) for (a, b), c in sorted(col_dirs.items())},
        "unique_circles": len(seen),
        "circle_lattice_size_hist": {str(k): int(v) for k, v in sorted(circle_size_hist.items())},
        "sum_C_k4_over_unique_circles": sum_c,
        "complete_circles": complete_circles,
        "partial_circles": partial_circles,
        "size_when_complete": {str(k): int(v) for k, v in sorted(size_complete.items())},
        "size_when_partial": {str(k): int(v) for k, v in sorted(size_partial.items())},
        "matches_concyclic_quads": sum_c == n_circ,
    }
    out = OUT / "fact_10x10_circle_line_spectrum.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print("wrote", out, flush=True)


if __name__ == "__main__":
    main()
