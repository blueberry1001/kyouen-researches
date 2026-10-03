#!/usr/bin/env python3
"""Independent checks of the strip theorem and all-center circle census.

This deliberately does not import either production census or strip verifier.
All arithmetic is integral.  The default strip check enumerates all parameter
residues directly; --census additionally checks every supplied witness and
compares sides 2..8 against an independent all-triples circle enumeration.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from itertools import combinations
import json
from math import gcd
from pathlib import Path


def direct_interval_bounds(modulus: int, width: int) -> list[int]:
    squares = {x * x % modulus for x in range(modulus)}
    best = [0] * (width + 1)
    for c in range(modulus):
        y_squares = [(2 * y + c) ** 2 % modulus for y in range(width)]
        for norm in range(modulus):
            count = 0
            for length, y_square in enumerate(y_squares, 1):
                count += (norm - y_square) % modulus in squares
                best[length] = max(best[length], count)
    return best


def large_masks(modulus: int, width: int, minimum: int) -> set[int]:
    squares = {x * x % modulus for x in range(modulus)}
    masks = set()
    for c in range(modulus):
        y_squares = [(2 * y + c) ** 2 % modulus for y in range(width)]
        for norm in range(modulus):
            mask = sum(1 << y for y, yy in enumerate(y_squares)
                       if (norm - yy) % modulus in squares)
            if mask.bit_count() >= minimum:
                masks.add(mask)
    return masks


def intersect_masks(width: int, moduli: tuple[int, ...]) -> dict:
    minimum = width // 2 + 1
    possible = {(1 << width) - 1}
    stages = []
    for modulus in moduli:
        masks = large_masks(modulus, width, minimum)
        possible = {a & b for a in possible for b in masks
                    if (a & b).bit_count() >= minimum}
        stages.append({"modulus": modulus, "remaining_masks": len(possible)})
    return {"stages": stages,
            "row_patterns": [[y for y in range(width) if mask >> y & 1]
                             for mask in sorted(possible)]}


def verify_strip() -> dict:
    mod9 = direct_interval_bounds(9, 5)
    assert mod9[5] == 4  # C denominator 2, after completing the square.
    mod441 = direct_interval_bounds(441, 31)
    elementary_widths = [16, 18, *range(20, 32)]
    assert all(2 * mod441[w] <= w for w in elementary_widths)
    width17_before43 = intersect_masks(17, (9, 49, 121))
    assert width17_before43["row_patterns"] == [[0, 2, 5, 7, 8, 9, 11, 14, 16]]
    width17 = intersect_masks(17, (9, 49, 121, 43))
    width19 = intersect_masks(19, (9, 49, 121))
    assert width17["row_patterns"] == width19["row_patterns"] == []
    # Every integer w >= 16 is a sum of widths in [16,31].
    for w in range(16, 10000):
        quotient, remainder = divmod(w, 16)
        assert quotient >= 1 and 16 <= 16 + remainder <= 31
        assert 16 * (quotient - 1) + 16 + remainder == w
    witness = [(x, y) for x in range(-5, 7) for y in range(-5, 7)
               if (2 * x - 1) ** 2 + (2 * y - 1) ** 2 == 130]
    assert len(witness) == 16
    assert max(y for x, y in witness) - min(y for x, y in witness) + 1 == 12
    return {"theorem": "All widths >=16, for arbitrary circle radii and horizontal extent",
            "mod9_H5": mod9[5],
            "mod441_bounds_16_to_31": mod441[16:],
            "width17_before_mod43": width17_before43,
            "width17": width17, "width19": width19,
            "width15_counterexample": witness}


def independent_all_triples(side: int) -> tuple[int, int]:
    points = [(x, y) for x in range(side) for y in range(side)]
    masks: dict[tuple[int, int, int, int], int] = defaultdict(int)
    for indices in combinations(range(side * side), 3):
        (x, y), (x1, y1), (x2, y2) = (points[i] for i in indices)
        u, v, U, V = x1 - x, y1 - y, x2 - x, y2 - y
        a = u * V - U * v
        if not a:
            continue
        s, S = u * u + v * v, U * U + V * V
        b = -(s * V - S * v) - 2 * a * x
        c = -(u * S - U * s) - 2 * a * y
        d = -a * (x * x + y * y) - b * x - c * y
        divisor = gcd(gcd(a, b), gcd(c, d))
        if a < 0:
            divisor = -divisor
        key = a // divisor, b // divisor, c // divisor, d // divisor
        masks[key] |= sum(1 << i for i in indices)
    return (max(mask.bit_count() for mask in masks.values()),
            max([2] + [mask.bit_count() for (a, b, c, d), mask in masks.items()
                       if b % a or c % a]))


def verify_census(path: Path) -> dict:
    data = json.loads(path.read_text())
    witness_count = 0
    for row in data["results"]:
        side = row["n"]
        for kind in ["all", "nonhalf"]:
            entry = row[kind]
            assert entry["anchor"][0] == 0
            ay = entry["anchor"][1]
            a, b, c = entry["equation"]
            assert a > 0 and gcd(a, gcd(b, c)) == 1
            count = sum(a * (x*x + (y-ay)**2) == b*x + c*(y-ay)
                        for x in range(side) for y in range(side))
            assert count == entry["count"], (side, kind, count, entry)
            if kind == "nonhalf":
                assert a > 1
            witness_count += 1
    small = []
    for side in range(2, min(8, data["max_side"]) + 1):
        independent = independent_all_triples(side)
        row = data["results"][side - 2]
        assert independent == (row["all"]["count"], row["nonhalf"]["count"])
        small.append({"n": side, "all": independent[0], "nonhalf": independent[1]})
    return {"max_side": data["max_side"], "exact_witnesses_checked": witness_count,
            "independent_all_triples": small}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--census", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = {"arithmetic": "exact integers", "strip": verify_strip()}
    if args.census:
        result["census"] = verify_census(args.census)
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded)
        print(f"All independent checks passed: {args.output}")
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
