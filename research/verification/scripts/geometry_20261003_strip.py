#!/usr/bin/env python3
"""Exact modular certificates for lattice circles in horizontal strips.

Pure Python / standard library.  No bounded search over circle radii is used.
The finite congruence checks support the all-radii proof in
research/geometry-20261003.md.
"""
from __future__ import annotations

import argparse
from collections import deque
import json
from itertools import combinations
from math import isqrt
from pathlib import Path


def square_residues(modulus: int) -> set[int]:
    return {x * x % modulus for x in range(modulus)}


def interval_bounds(modulus: int, maximum_length: int) -> dict:
    """H_M(L), exhaustively over every pair C,N modulo odd M.

Because 2 is invertible, the sequence 2*i covers every possible C; rotations
of one period are exactly the M possible starting residues, not a sample.
"""
    assert modulus % 2 == 1
    squares = square_residues(modulus)
    best = [0] * (maximum_length + 1)
    witnesses: list[dict | None] = [None] * (maximum_length + 1)
    for n in range(modulus):
        period = [int((n - (2 * i) ** 2) % modulus in squares)
                  for i in range(modulus)]
        # Explicitly repeat: this also handles maximum_length > modulus.
        repeated = [period[i % modulus]
                    for i in range(modulus + maximum_length)]
        window = sum(repeated[i] << i for i in range(maximum_length))
        for start in range(modulus):
            for length in range(1, maximum_length + 1):
                count = (window & ((1 << length) - 1)).bit_count()
                if count > best[length]:
                    best[length] = count
                    witnesses[length] = {"C": 2 * start % modulus, "N": n}
            window = (window >> 1) | (
                repeated[start + maximum_length] << (maximum_length - 1)
            )
    # A direct implementation independently verifies each maximizing witness.
    for length in range(1, maximum_length + 1):
        witness = witnesses[length]
        assert witness is not None
        assert best[length] == sum(
            (witness["N"] - (witness["C"] + 2 * y) ** 2) % modulus in squares
            for y in range(length)
        )
    return {
        "modulus": modulus,
        "residue_pairs_checked": modulus * modulus,
        "bounds": [
            {"width": length, "maximum_allowed_rows": best[length],
             "witness": witnesses[length]}
            for length in range(1, maximum_length + 1)
        ],
    }


def residue_masks(modulus: int, width: int) -> set[int]:
    """Direct C,N enumeration, deliberately separate from interval_bounds."""
    squares = square_residues(modulus)
    masks = set()
    for c in range(modulus):
        bases = [(c + 2 * y) ** 2 % modulus for y in range(width)]
        for n in range(modulus):
            masks.add(sum(1 << y for y, base in enumerate(bases)
                          if (n - base) % modulus in squares))
    return masks


def maximal_masks(masks: set[int]) -> list[int]:
    """Discard masks contained in another: preserves every possible subset."""
    kept: list[int] = []
    for mask in sorted(masks, key=lambda value: (-value.bit_count(), value)):
        if not any(mask & other == mask for other in kept):
            kept.append(mask)
    return kept


def intersect_obstructions(width: int, required_rows: int,
                           moduli: tuple[int, ...]) -> dict:
    candidates = [(1 << width) - 1]
    stages = []
    for modulus in moduli:
        masks = maximal_masks({mask for mask in residue_masks(modulus, width)
                               if mask.bit_count() >= required_rows})
        candidates = maximal_masks({left & right
                                    for left in candidates for right in masks
                                    if (left & right).bit_count() >= required_rows})
        stages.append({"modulus": modulus,
                       "individual_maximal_masks": len(masks),
                       "remaining_maximal_intersections": len(candidates)})
    return {
        "width": width,
        "required_rows": required_rows,
        "moduli": list(moduli),
        "stages": stages,
        "remaining_row_patterns": [
            [y for y in range(width) if mask >> y & 1] for mask in candidates
        ],
    }


def counterexample() -> dict:
    # Circle (x-1/2)^2 + (y-1/2)^2 = 65/2, in 12 consecutive rows.
    points = [(x, y) for y in range(-5, 7) for x in range(-5, 7)
              if (2 * x - 1) ** 2 + (2 * y - 1) ** 2 == 130]
    assert len(points) == 16
    assert len({y for _, y in points}) == 8
    # Independently check all lifted 4x4 determinants by translation.
    for quad in combinations(points, 4):
        x0, y0 = quad[0]
        rows = [(dx * dx + dy * dy, dx, dy)
                for x, y in quad[1:] for dx, dy in [(x - x0, y - y0)]]
        (a, b, c), (d, e, f), (g, h, i) = rows
        assert a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g) == 0
    return {"circle_equation": "(2x-1)^2+(2y-1)^2=130",
            "points": points, "point_count": 16, "strip_width": 12,
            "also_refutes_widths": [12, 13, 14, 15]}


def small_strip_extrema(modular_rows: list[dict]) -> list[dict]:
    """Matching all-radii modular upper bounds and explicit circle witnesses."""
    expected = [2, 4, 6, 8, 8, 8, 10, 12, 12, 12, 14, 16, 16, 16, 16]
    circles = {
        n: [(x, y) for x in range(-10, 11) for y in range(-10, 11)
            if (2 * x - 1) ** 2 + (2 * y - 1) ** 2 == n]
        for n in (10, 50, 130)
    }
    result = []
    for width, maximum in enumerate(expected, 1):
        allowed_rows = modular_rows[width - 1]["maximum_allowed_rows"]
        # A non-integral C denominator gives <=2 ceil(w/2) for w<9,
        # and <=w for w>=9 by the denominator lemma in the note.
        denominator_bound = 2 * ((width + 1) // 2) if width < 9 else width
        upper = max(width, denominator_bound, 2 * allowed_rows)
        assert upper == maximum
        candidates = []
        for n, points in circles.items():
            for start in range(-10, 11):
                selected = [(x, y) for x, y in points if start <= y < start + width]
                candidates.append((len(selected), n, start, selected))
        count, n, start, points = max(candidates)
        assert count == maximum
        shift_x = -min(x for x, _ in points)
        points = sorted((x + shift_x, y - start) for x, y in points)
        a, b = 1 + 2 * shift_x, 1 - 2 * start
        # Reconstruct *all* lattice points in the infinite horizontal strip,
        # not just points in the finite witness search box.
        reconstructed = set()
        for y in range(width):
            square = n - (2 * y - b) ** 2
            if square < 0:
                continue
            root = isqrt(square)
            if root * root == square:
                for signed in {root, -root}:
                    if (a + signed) % 2 == 0:
                        reconstructed.add(((a + signed) // 2, y))
        assert reconstructed == set(points)
        result.append({"width": width, "exact_maximum_circle_points": maximum,
                       "mod441_row_bound": allowed_rows,
                       "circle": {"equation": "(2x-a)^2+(2y-b)^2=N",
                                  "a": a, "b": b, "N": n},
                       "points": points})
    return result


def periodic_density_certificate() -> dict:
    """All cyclic intervals modulo441, using exact prefix sums and a deque.

    Weight +26 on an allowed row and -16 otherwise.  The weight of a length-r
    interval with h allowed rows is 42h-16r.  This computes the maximum over
    every N, every starting C and every length 1..441 in O(441^2) time.
    """
    modulus = 441
    squares = square_residues(modulus)
    maximum_period_count = maximum_weight = 0
    period_witness = interval_witness = None
    for n in range(modulus):
        allowed = [int((n - (2 * y) ** 2) % modulus in squares)
                   for y in range(modulus)]
        period_count = sum(allowed)
        if period_count > maximum_period_count:
            maximum_period_count = period_count
            period_witness = n
        prefix = [0]
        for i in range(2 * modulus - 1):
            prefix.append(prefix[-1] + 42 * allowed[i % modulus] - 16)
        minimum_starts: deque[int] = deque()
        for end in range(1, 2 * modulus):
            start = end - 1
            if start < modulus:
                while minimum_starts and prefix[minimum_starts[-1]] >= prefix[start]:
                    minimum_starts.pop()
                minimum_starts.append(start)
            while minimum_starts and minimum_starts[0] < end - modulus:
                minimum_starts.popleft()
            if not minimum_starts:
                continue
            start = minimum_starts[0]
            weight = prefix[end] - prefix[start]
            if weight > maximum_weight:
                maximum_weight = weight
                interval_witness = {"C": 2 * start % modulus, "N": n,
                                    "width": end - start,
                                    "allowed_rows": sum(allowed[i % modulus]
                                                        for i in range(start, end))}
    assert maximum_period_count == 168
    assert maximum_weight == 144
    assert interval_witness is not None
    assert interval_witness["width"] == 12
    assert interval_witness["allowed_rows"] == 8
    return {
        "modulus": modulus,
        "period_maximum_allowed_rows": maximum_period_count,
        "period_witness_N": period_witness,
        "all_cyclic_intervals_checked": modulus ** 3,
        "maximum_42h_minus_16r": maximum_weight,
        "maximizing_interval": interval_witness,
        "point_bound_if_horizontal_lattice_pair_exists": "floor((16*w+144)/21)",
        "stronger_sufficient_condition": "2*center_x is an integer; no horizontal pair need be present",
        "scope_warning": "Does not give this bound for arbitrary non-half-integral center_x",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    mod9 = interval_bounds(9, 6)
    assert mod9["bounds"][4]["maximum_allowed_rows"] == 4
    mod441 = interval_bounds(441, 39)
    expected_tail = [10, 10, 10, 10, 11, 11, 12, 12, 12, 13,
                     13, 13, 14, 14, 14, 15, 15, 16, 16, 16]
    assert [row["maximum_allowed_rows"] for row in mod441["bounds"][19:]] == expected_tail
    assert all(2 * row["maximum_allowed_rows"] <= row["width"]
               for row in mod441["bounds"][19:])
    assert mod441["bounds"][15]["maximum_allowed_rows"] == 8
    assert mod441["bounds"][17]["maximum_allowed_rows"] == 9
    width19 = intersect_obstructions(19, 10, (9, 49, 121))
    assert width19["remaining_row_patterns"] == []
    width17_intermediate = intersect_obstructions(17, 9, (9, 49, 121))
    assert width17_intermediate["remaining_row_patterns"] == [[0, 2, 5, 7, 8, 9, 11, 14, 16]]
    width17 = intersect_obstructions(17, 9, (9, 49, 121, 43))
    assert width17["remaining_row_patterns"] == []
    remaining_pattern = width17_intermediate["remaining_row_patterns"][0]
    squares43 = square_residues(43)
    assert not any(all((n - (c + 2 * y) ** 2) % 43 in squares43
                       for y in remaining_pattern)
                   for c in range(43) for n in range(43))
    result = {
        "status": "complete",
        "arithmetic": "exact integers only",
        "theorem": "Every circle has at most w lattice points in w consecutive rows for every w>=16",
        "smallest_eventual_threshold": 16,
        "mod9": mod9,
        "mod441": mod441,
        "width19_certificate": width19,
        "width17_intermediate_pattern": width17_intermediate,
        "width17_certificate": width17,
        "small_strip_exact_extrema": small_strip_extrema(mod441["bounds"]),
        "conditional_periodic_density": periodic_density_certificate(),
        "lower_width_counterexample": counterexample(),
    }
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded)
        print(f"Verified strip theorem; saved {args.output}")
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
