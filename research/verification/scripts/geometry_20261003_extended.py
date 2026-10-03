#!/usr/bin/env python3
"""Exact strip extrema under a center condition and an all-center rectangle transfer.

For widths16..31 this verifies a full-radius conditional extremum table and
proves the same table for arbitrary centers through a finite, very large
horizontal width. It does NOT claim the unrestricted infinite-strip values
for widths17..31 are settled.
"""
from __future__ import annotations

import argparse
from functools import cache
import json
from math import isqrt, prod
from pathlib import Path

from geometry_20261003_strip import interval_bounds, maximal_masks, residue_masks

LOWER = {**dict.fromkeys(range(16, 22), 16), 22: 18, 23: 20, 24: 20,
         25: 22, **dict.fromkeys(range(26, 32), 24)}
CENTER_MODULI = (9, 49, 121, 43, 19)
DENOMINATOR_MODULI = ((3, 9), (7, 49), (11, 121), (19, 19),
                      (23, 23), (31, 31), (43, 43))


@cache
def masks(modulus: int, width: int) -> frozenset[int]:
    return frozenset(residue_masks(modulus, width))


def center_certificate(width: int, count: int) -> dict:
    needed = count // 2 + 1
    candidates = [(1 << width) - 1]
    stages = []
    for modulus in CENTER_MODULI:
        family = maximal_masks({mask for mask in masks(modulus, width)
                                if mask.bit_count() >= needed})
        candidates = maximal_masks({left & right
                                    for left in candidates for right in family
                                    if (left & right).bit_count() >= needed})
        stages.append({"modulus": modulus,
                       "remaining_maximal_row_masks": len(candidates)})
        if not candidates:
            break
    assert not candidates, (width, candidates)
    return {"required_rows_for_more_than_bound": needed,
            "stages": stages, "remaining_row_masks": 0}


def witness(width: int, count: int) -> dict:
    a = b = 11 if width <= 21 else 25
    n = 130 if width <= 21 else 650
    points = set()
    for y in range(width):
        remainder = n - (2 * y - b) ** 2
        if remainder < 0:
            continue
        root = isqrt(remainder)
        if root * root != remainder:
            continue
        for signed in {root, -root}:
            if (a + signed) % 2 == 0:
                points.add(((a + signed) // 2, y))
    assert len(points) == count
    assert min(x for x, _ in points) == 0
    return {"circle_equation": "(2x-a)^2+(2y-b)^2=N",
            "a": a, "b": b, "N": n,
            "points": sorted(points), "point_count": len(points),
            "minimum_rectangle_length_for_this_witness": 1 + max(x for x, _ in points)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    short_bounds = interval_bounds(441, 16)["bounds"]
    forced_product = prod(prime for prime, _ in DENOMINATOR_MODULI)
    assert forced_product == 134562351
    rows = []
    for width, count in LOWER.items():
        certificate = center_certificate(width, count)
        half_length = (width + 1) // 2
        denominator2_bound = 2 * short_bounds[half_length - 1]["maximum_allowed_rows"]
        denominator3plus_bound = 2 * ((width + 2) // 3)
        assert denominator2_bound <= count
        assert denominator3plus_bound <= count
        forcing = []
        for prime, modulus in DENOMINATOR_MODULI:
            h = max(mask.bit_count() for mask in masks(modulus, width))
            assert h <= count
            forcing.append({"prime_dividing_A_in_any_counterexample": prime,
                            "modulus": modulus, "maximum_permitted_rows": h})
        numerator, denominator = (count - 1) * forced_product, 2 * (width - 1)
        limit = (numerator + denominator - 1) // denominator
        assert denominator * (limit - 1) < numerator
        assert denominator * limit >= numerator
        lower_witness = witness(width, count)
        rows.append({"width": width,
                     "exact_maximum_if_2center_x_is_integer": count,
                     "integer_C_certificate": certificate,
                     "C_denominator2_upper_bound": denominator2_bound,
                     "C_denominator_at_least3_upper_bound": denominator3plus_bound,
                     "attaining_circle": lower_witness,
                     "denominator_forcing": forcing,
                     "forced_primitive_A_divisor": forced_product,
                     "all_center_rectangle_maximum": count,
                     "all_center_rectangle_attained_from_length": lower_witness["minimum_rectangle_length_for_this_witness"],
                     "all_center_rectangle_proved_through_length": limit,
                     "polygon_area_bound_numerator": numerator,
                     "polygon_area_bound_denominator": denominator,
                     "unrestricted_infinite_strip_lower_bound": count,
                     "unrestricted_infinite_strip_upper_bound": width,
                     "unrestricted_value_exact": width == 16})
    common_limit = min(row["all_center_rectangle_proved_through_length"] for row in rows)
    assert common_limit == 50460882
    result = {
        "status": "complete",
        "conditional_center_scope": "2*center_x integer, with arbitrary center_y and radius",
        "conditional_exact_extrema": {str(w): n for w, n in LOWER.items()},
        "unrestricted_infinite_strip_exact_new_value": {"P(16)": 16},
        "unrestricted_infinite_strip_unresolved_widths": list(range(17, 32)),
        "forced_primitive_coefficient_product": forced_product,
        "uniform_all_center_rectangle_range": {"width_min": 16, "width_max": 31,
                                                "length_min": 26, "length_max": common_limit},
        "rows": rows,
        "scope_warning": "The finite rectangle transfer is a congruence/determinant proof; no all-center infinite-strip equality for w>=17 is claimed.",
    }
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded)
        print(f"Verified extended strip certificates; saved {args.output}")
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
