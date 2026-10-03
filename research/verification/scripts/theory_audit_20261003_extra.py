#!/usr/bin/env python3
"""Exact independent census for denominator-5 and denominator-8 theorems."""
from __future__ import annotations

import argparse
from array import array
from fractions import Fraction
from itertools import combinations
import json
from math import gcd, isqrt
from pathlib import Path


def factors(n: int) -> list[tuple[int, int]]:
    out = []
    p = 2
    while p * p <= n:
        if n % p == 0:
            e = 0
            while n % p == 0:
                n //= p
                e += 1
            out.append((p, e))
        p += 1
    if n > 1:
        out.append((n, 1))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=200000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    limit = args.limit
    counts = {q: array("H", [0]) * ((limit + 1) * q * q) for q in [5, 8]}
    primitive = {q: [(a, b) for a in range(q) for b in range(q)
                     if gcd(gcd(a, b), q) == 1] for q in [5, 8]}
    assert len(primitive[5]) == 24 and len(primitive[8]) == 48
    bound = isqrt(limit)
    for x in range(-bound, bound + 1):
        for y in range(-bound, bound + 1):
            norm = x * x + y * y
            if 1 <= norm <= limit:
                for q in [5, 8]:
                    counts[q][q*q*norm + q*(x % q) + y % q] += 1
    observed = {5: {}, 8: {}}
    candidates = {5: {}, 8: {}}
    unrestricted = {}
    for norm in range(1, limit + 1):
        ff = factors(norm)
        possible = all(p % 4 != 3 or e % 2 == 0 for p, e in ff)
        split_only = all(p % 4 == 1 for p, e in ff)
        D = D5 = D0 = D1 = 1
        delta = 1
        e2 = 0
        for p, e in ff:
            if p == 2:
                e2 = e
            if p % 4 == 1:
                D *= e + 1
                if p != 5:
                    D5 *= e + 1
                if p % 8 == 1:
                    D0 *= e + 1
                else:
                    D1 *= e + 1
                    if e % 2:
                        delta = 0
        actual = {q: sorted(counts[q][q*q*norm + q*a + b] for a, b in primitive[q])
                  for q in [5, 8]}
        nonempty_q5 = 8 if norm % 5 == 0 else 4
        expected5 = ([0] * (24 - nonempty_q5) + [D5] * nonempty_q5
                     if possible else [0] * 24)
        if possible and e2 <= 1:
            lo, hi = D0 * (D1 - delta) // 2, D0 * (D1 + delta) // 2
            expected8 = sorted([0] * 40 + [lo] * 4 + [hi] * 4)
        else:
            expected8 = [0] * 48
        assert actual[5] == expected5, (norm, ff, actual[5], expected5)
        assert actual[8] == expected8, (norm, ff, actual[8], expected8)
        for q in [5, 8]:
            for m in range(1, max(actual[q]) + 1):
                observed[q].setdefault(m, norm)
        if split_only:
            for m in range(1, D + 1):
                unrestricted.setdefault(m, norm)
            if norm % 5:
                for m in range(1, D5 + 1):
                    candidates[5].setdefault(m, norm)
            for m in range(1, D0 * (D1 + delta) // 2 + 1):
                candidates[8].setdefault(m, norm)
    thresholds = {}
    for q in [5, 8]:
        rows = []
        for m, norm in sorted(observed[q].items()):
            assert norm == candidates[q][m]
            N = unrestricted[m]
            if q == 5 and m >= 2:
                assert 5 * norm >= 13 * N
            if q == 8 and m >= 3:
                assert norm >= 5 * N
            rows.append({"minimum_points": m, "N_m": N,
                         "least_q_norm": norm,
                         "least_radius_squared": str(Fraction(norm, q*q))})
        thresholds[str(q)] = rows
    # Explicit two-point witnesses for every exact denominator 1..100.
    two_point = []
    for q in range(1, 101):
        if q == 1:
            a, b, points, r2 = 0, 0, [(-1, 0), (1, 0)], Fraction(1)
        elif q == 2:
            a, b, points, r2 = 1, 0, [(0, 0), (1, 0)], Fraction(1, 4)
        elif q % 2 == 0:
            a, b, points, r2 = q // 2, 1, [(0, 0), (1, 0)], Fraction(1, 4) + Fraction(1, q*q)
        else:
            a, b, points, r2 = (q - 1) // 2, (q + 1) // 2, [(0, 0), (1, 1)], Fraction(1, 2) + Fraction(1, 2*q*q)
        assert gcd(gcd(a, b), q) == 1
        assert all((Fraction(x) - Fraction(a, q))**2 +
                   (Fraction(y) - Fraction(b, q))**2 == r2 for x, y in points)
        two_point.append({"q": q, "center_numerators": [a, b],
                          "radius_squared": str(r2), "points": points})
    determinant_checks = 0
    higher_point_witnesses = []
    for q in [5, 8]:
        for m, norm in sorted(observed[q].items()):
            if m < 3:
                continue
            rx, ry = max(primitive[q], key=lambda ab: counts[q][q*q*norm + q*ab[0] + ab[1]])
            a, b = (-rx) % q, (-ry) % q
            points = []
            for u in range(-isqrt(norm), isqrt(norm) + 1):
                v = isqrt(norm-u*u)
                if u*u+v*v == norm:
                    for vv in {v, -v}:
                        if u % q == rx and vv % q == ry:
                            points.append(((u+a)//q, (vv+b)//q))
            assert len(points) >= m
            raw = [q*q, -2*q*a, -2*q*b, a*a+b*b-norm]
            divisor = gcd(gcd(raw[0], raw[1]), gcd(raw[2], raw[3]))
            A = raw[0] // divisor
            assert A == q // gcd(q, 2)
            for (x0, y0), (x1, y1), (x2, y2) in combinations(points, 3):
                det = (x1-x0)*(y2-y0)-(x2-x0)*(y1-y0)
                assert det and det % A == 0
                determinant_checks += 1
            # Square the triangle-radius lower bound to stay in integers.
            assert 27*norm*norm >= 4*A*A*q**4
            higher_point_witnesses.append({"q": q, "minimum_points": m,
                                           "actual_points": len(points), "primitive_A": A})
    result = {"arithmetic": "exact integers; Gaussian lattice points enumerated directly",
              "limit": limit,
              "center_norm_conditions_checked": (24 + 48) * limit,
              "thresholds": thresholds,
              "two_point_witnesses": two_point,
              "primitive_denominator_checks": higher_point_witnesses,
              "triangle_determinants_checked": determinant_checks,
              "scope": "Finite check of formulas; general claims proved separately in the research note"}
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded)
        print(f"All denominator-5/8 checks passed: {args.output}")
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
