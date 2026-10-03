#!/usr/bin/env python3
"""Independent integer check of exact denominator-6 circle count formulas."""
from __future__ import annotations

import argparse
from array import array
import json
from math import gcd, isqrt
from pathlib import Path


def factor(n: int) -> list[tuple[int, int]]:
    answer = []
    p = 2
    while p * p <= n:
        if n % p == 0:
            e = 0
            while n % p == 0:
                n //= p
                e += 1
            answer.append((p, e))
        p += 1
    if n > 1:
        answer.append((n, 1))
    return answer


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=100000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    limit = args.limit
    counts = array("H", [0]) * ((limit + 1) * 36)
    bound = isqrt(limit)
    for x in range(-bound, bound + 1):
        for y in range(-bound, bound + 1):
            norm = x * x + y * y
            if 1 <= norm <= limit:
                counts[36 * norm + 6 * (x % 6) + y % 6] += 1
    primitive = [(a, b) for a in range(6) for b in range(6)
                 if gcd(gcd(a, b), 6) == 1]
    assert len(primitive) == 24
    first_norm: dict[int, int] = {}
    first_N: dict[int, int] = {}
    checked = 0
    for norm in range(1, limit + 1):
        factors = factor(norm)
        D0 = D1 = 1
        delta = 1
        e2 = 0
        possible = True
        split_only = True
        for p, e in factors:
            if p == 2:
                e2 = e
            elif p % 4 == 3 and e % 2:
                possible = False
            if p % 12 == 1:
                D0 *= e + 1
            elif p % 12 == 5:
                D1 *= e + 1
                if e % 2:
                    delta = 0
            if p % 4 != 1:
                split_only = False
        D = D0 * D1
        actual = sorted(counts[36 * norm + 6 * a + b] for a, b in primitive)
        if not possible or norm % 3 == 0 or e2 >= 2:
            expected = [0] * 24
        elif e2 == 1:
            expected = sorted([D] * 4 + [0] * 20)
        else:
            lo = D0 * (D1 - delta) // 2
            hi = D0 * (D1 + delta) // 2
            expected = sorted([lo] * 4 + [hi] * 4 + [0] * 16)
        assert actual == expected, (norm, factors, actual, expected)
        checked += 24
        for threshold in range(1, max(actual) + 1):
            first_norm.setdefault(threshold, norm)
        if split_only:
            for threshold in range(1, D + 1):
                first_N.setdefault(threshold, norm)
    assert first_norm[1] == 1
    thresholds = []
    for m, norm in sorted(first_norm.items()):
        expected = 1 if m == 1 else 2 * first_N[m]
        assert norm == expected, (m, norm, expected)
        thresholds.append({"minimum_points": m, "N_m": first_N[m],
                           "least_q6_norm": norm, "least_radius_squared": f"{norm}/36"})
    output = {"arithmetic": "exact integers; direct enumeration of all Gaussian integers with norm <= limit",
              "limit": limit, "primitive_center_norm_conditions_checked": checked,
              "thresholds": thresholds,
              "scope": "finite verification supports the separate proof for all thresholds"}
    encoded = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded)
        print(f"All denominator-6 formulas passed: {args.output}")
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
