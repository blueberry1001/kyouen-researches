#!/usr/bin/env python3
"""Verify the sharp raw-circle norm bound N <= 2(n-1)^6.

Checks every noncollinear triple for n=2..10 and a primitive asymptotically
sharp family. No dependencies beyond the Python standard library.
"""
from __future__ import annotations

import argparse
from itertools import combinations
import json
from math import gcd
from pathlib import Path


def circle_data(points: tuple[tuple[int, int], ...]) -> dict:
    (x0, y0), (x1, y1), (x2, y2) = points
    ux, uy = x1 - x0, y1 - y0
    vx, vy = x2 - x0, y2 - y0
    area = ux * vy - uy * vx
    uu, vv = ux * ux + uy * uy, vx * vx + vy * vy
    fx, fy = uu * vy - vv * uy, ux * vv - vx * uu
    b, c = -2 * area * x0 - fx, -2 * area * y0 - fy
    e = area * (x0 * x0 + y0 * y0) + fx * x0 + fy * y0
    raw_norm = b * b + c * c - 4 * area * e
    edge_product = uu * vv * ((ux - vx) ** 2 + (uy - vy) ** 2)
    assert raw_norm == fx * fx + fy * fy == edge_product
    content = gcd(gcd(abs(area), abs(b)), gcd(abs(c), abs(e)))
    return {"A": area, "B": b, "C": c, "E": e,
            "raw_N": raw_norm, "content": content,
            "primitive_N": raw_norm // (content * content) if content else None}


def check_square(n: int) -> dict:
    side = n - 1
    raw_maximum = primitive_maximum = noncollinear = collinear = 0
    raw_witness = primitive_witness = None
    for points in combinations([(x, y) for x in range(n) for y in range(n)], 3):
        data = circle_data(points)
        if data["A"] == 0:
            collinear += 1
            continue
        noncollinear += 1
        assert 0 < data["raw_N"] <= 2 * side ** 6
        for x, y in points:
            assert data["A"] * (x * x + y * y) + data["B"] * x + data["C"] * y + data["E"] == 0
            assert (2 * data["A"] * x + data["B"]) ** 2 + (2 * data["A"] * y + data["C"]) ** 2 == data["raw_N"]
        if data["raw_N"] > raw_maximum:
            raw_maximum, raw_witness = data["raw_N"], points
        if data["primitive_N"] > primitive_maximum:
            primitive_maximum, primitive_witness = data["primitive_N"], points
    assert raw_maximum == 2 * side ** 6
    return {"n": n, "noncollinear_triples": noncollinear, "collinear_triples": collinear,
            "raw_N_maximum": raw_maximum, "raw_N_maximum_witness": raw_witness,
            "primitive_N_maximum": primitive_maximum,
            "primitive_N_maximum_witness": primitive_witness}


def check_primitive_family() -> dict:
    samples = []
    for side in range(3, 2002, 2):
        points = ((0, 0), (side, 1), (2, side))
        data = circle_data(points)
        assert data["content"] == 1
        expected = (side * side + 1) * (side * side + 4) * (2 * side * side - 6 * side + 5)
        assert data["raw_N"] == data["primitive_N"] == expected
        assert data["A"] == side * side - 2
        assert -data["B"] == side ** 3 - side * side + side - 4
        assert -data["C"] == side ** 3 - 2 * side * side + 4 * side - 2
        if side in (3, 5, 11, 101, 1001, 2001):
            samples.append({"side": side, "points": points, "primitive_N": expected,
                            "ratio_N_over_2side6": [expected, 2 * side ** 6]})
    return {"odd_sides_checked": 1000, "range": [3, 2001],
            "formula": "N=(L^2+1)(L^2+4)(2L^2-6L+5), odd L>=3",
            "all_coefficients_primitive": True, "asymptotic_N_over_L6": 2,
            "samples": samples}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    boards = [check_square(n) for n in range(2, 11)]
    result = {"status": "complete", "arithmetic": "exact integers only",
              "raw_norm_identity": "N=|u|^2 |v|^2 |u-v|^2",
              "sharp_bound": "N<=2(n-1)^6",
              "previous_bound": "N<=224(n-1)^6",
              "improvement_factor": 112,
              "total_noncollinear_triples": sum(row["noncollinear_triples"] for row in boards),
              "boards": boards, "primitive_asymptotic_family": check_primitive_family()}
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded)
        print(f"Verified sharp circle-norm bound; saved {args.output}")
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
