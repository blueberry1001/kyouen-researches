#!/usr/bin/env python3
"""Computer-assisted proof that M_{4,8}=11 (Python standard library only).

The general counting argument proves stability for m>=70.  Integer recurrence
checks classify every eight-point circle for m<=69.  Only the translated
(1,3,3,1) chord pattern remains, yielding stability already for m>=13.
An exhaustive necessary-condition search excludes deficient maximal positions
at m=11,12.  A separate triple-defined, exact-integer curve generator verifies
a deficient maximal witness on 4x10 without relying on the chord classification.
"""
from __future__ import annotations

import itertools
import json
from math import gcd, isqrt
from pathlib import Path


def chord_patterns(max_span: int) -> list[tuple[int, int, int, int]]:
    """All positive same-parity chord differences bounded by max_span."""
    out = []
    for a in range(1, max_span + 1):
        for b in range(1, max_span + 1):
            if (a - b) % 2:
                continue
            c2, d2 = 2 * b * b - a * a - 8, 3 * b * b - 2 * a * a - 24
            if min(c2, d2) <= 0:
                continue
            c, d = isqrt(c2), isqrt(d2)
            if c * c == c2 and d * d == d2 and max(c, d) <= max_span:
                assert len({x % 2 for x in (a, b, c, d)}) == 1
                out.append((a, b, c, d))
    return out


def local_circles(m: int) -> list[tuple[int, int, int, int]]:
    return [((1 << (t + 1)) | (1 << (t + 2)),
             (1 << t) | (1 << (t + 3)),
             (1 << t) | (1 << (t + 3)),
             (1 << (t + 1)) | (1 << (t + 2))) for t in range(m - 3)]


def exclude_deficient_row(m: int, target: int) -> dict:
    """Enumerate ALL target subsets of size 0..6 and all blocker choices.

    For each blank target point choose a local circle containing it and one
    occupied target point.  All six exterior points of that circle are forced.
    Reject whenever one exterior row exceeds seven points, or a complete
    forbidden circle is forced.  Every deficient maximal safe position induces
    a surviving branch, so zero leaves is an exhaustive impossibility proof.
    The search need not enumerate optional exterior stones.
    """
    cs = local_circles(m)
    counts = {'target_subsets': 0, 'subsets_with_blocker_options': 0,
              'search_nodes': 0, 'row_capacity_rejections': 0,
              'unsafe_rejections': 0, 'surviving_leaves': 0}
    for size in range(7):
        for subset in itertools.combinations(range(m), size):
            counts['target_subsets'] += 1
            occupied = sum(1 << x for x in subset)
            options = []
            for x in range(m):
                if occupied >> x & 1:
                    continue
                choices = [c for c in cs if c[target] >> x & 1
                           and (c[target] & occupied).bit_count() == 1]
                if not choices:
                    break
                options.append(choices)
            else:
                counts['subsets_with_blocker_options'] += 1
                options.sort(key=len)

                def visit(i: int, rows: tuple[int, ...]) -> None:
                    counts['search_nodes'] += 1
                    if any(row.bit_count() > 7 for row in rows):
                        counts['row_capacity_rejections'] += 1
                        return
                    if any(all(c[y] & rows[y] == c[y] for y in range(4)) for c in cs):
                        counts['unsafe_rejections'] += 1
                        return
                    if i == len(options):
                        counts['surviving_leaves'] += 1
                        return
                    for c in options[i]:
                        new_rows = tuple(occupied if y == target else rows[y] | c[y]
                                         for y in range(4))
                        visit(i + 1, new_rows)

                visit(0, tuple(occupied if y == target else 0 for y in range(4)))
    assert counts['surviving_leaves'] == 0, (m, target, counts)
    return {'m': m, 'target_row': target, **counts}


def normalize(values: tuple[int, ...]) -> tuple[int, ...]:
    divisor = 0
    for value in values:
        divisor = gcd(divisor, value)
    assert divisor
    sign = next(value for value in values if value) > 0
    return tuple(value // divisor * (1 if sign else -1) for value in values)


def through_three(p: tuple[int, int], q: tuple[int, int], r: tuple[int, int]) -> tuple[int, ...]:
    """Integer coefficients A(x*x+y*y)+B*x+C*y+D=0, also for lines."""
    x0, y0 = p
    u, v = q[0] - x0, q[1] - y0
    s, t = r[0] - x0, r[1] - y0
    rq, rr = u * u + v * v, s * s + t * t
    a = u * t - v * s
    bp, cp = v * rr - rq * t, rq * s - u * rr
    return normalize((a, bp - 2 * a * x0, cp - 2 * a * y0,
                      a * (x0 * x0 + y0 * y0) - bp * x0 - cp * y0))


def curve_masks(m: int, q: int = 8) -> tuple[list[int], dict]:
    """Independent exhaustive curve generator: all triples on the board."""
    points = [(x, y) for y in range(4) for x in range(m)]
    coefficients = {through_three(*triple) for triple in itertools.combinations(points, 3)}
    masks = []
    line_count = circle_count = 0
    for a, b, c, d in coefficients:
        mask = sum(1 << k for k, (x, y) in enumerate(points)
                   if a * (x * x + y * y) + b * x + c * y + d == 0)
        if mask.bit_count() >= q:
            masks.append(mask)
            if a:
                circle_count += 1
            else:
                line_count += 1
    return masks, {'board_points': len(points), 'triples': len(points) * (len(points) - 1) *
                  (len(points) - 2) // 6, 'distinct_curves': len(coefficients),
                  'curves_with_at_least_q_points': len(masks),
                  'lines': line_count, 'circles': circle_count}


def witness_check() -> dict:
    m = 10
    rows = [[0, 1, 2, 4, 7, 9], [1, 3, 4, 5, 6, 8, 9],
            [1, 3, 4, 5, 6, 8, 9], [2, 3, 4, 5, 6, 7, 8]]
    occupied = sum(1 << (m * y + x) for y, row in enumerate(rows) for x in row)
    masks, details = curve_masks(m)
    assert all((mask & occupied).bit_count() < 8 for mask in masks)
    blocked = []
    for k in range(4 * m):
        if occupied >> k & 1:
            continue
        containing = [mask for mask in masks if ((occupied | (1 << k)) & mask).bit_count() >= 8]
        assert containing, k
        blocked.append([k % m, k // m])
    # Independent geometry must recover exactly m-3 local 8-point circles.
    assert details['lines'] == 4 and details['circles'] == m - 3
    return {'m': m, 'rows': rows, 'stones': occupied.bit_count(),
            'row_counts': list(map(len, rows)), 'safe': True,
            'maximal': True, 'blocked_blank_points': blocked,
            'independent_geometry': details}


def main() -> None:
    patterns68 = chord_patterns(68)
    assert patterns68 == [(1, 3, 3, 1)]
    patterns72 = chord_patterns(72)
    patterns73 = chord_patterns(73)
    assert patterns72 == [(1, 3, 3, 1)]
    assert patterns73 == [(1, 3, 3, 1), (35, 51, 63, 73), (73, 63, 51, 35)]
    result = {
        'statement': 'M_{4,8}=11; every safe S on 4xm with m>=11 has g(S)=(28-|S|) mod 2',
        'universal_counting_stability_from': 70,
        'local_circle_classification': {'maximum_span_for_proof': 68,
                                       'patterns': patterns68,
                                       'first_nonlocal_board_length': 74,
                                       'patterns_at_span_73': patterns73},
        'local_counting_stability_from': 13,
        'finite_exclusions': [exclude_deficient_row(m, r) for m in (11, 12) for r in (0, 1)],
        'lower_bound_witness': witness_check(),
        'proof_scope': {'finite_search': 'm=11,12; all subsets of target row of sizes 0..6',
                        'local_geometry_and_counting': 'm=13..69',
                        'universal_geometry_and_counting': 'all m>=70'},
    }
    destination = Path(__file__).resolve().parents[1] / 'q48_exact_threshold.json'
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
