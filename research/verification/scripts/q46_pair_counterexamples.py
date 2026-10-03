#!/usr/bin/env python3
"""Verify why naive four/five-edge bounds for two five-point rows fail."""
from fractions import Fraction
from itertools import combinations
from math import isqrt
import json


def determinant4(points):
    x, y = points[0]
    rows = [[u*u + v*v - x*x - y*y, u-x, v-y] for u, v in points[1:]]
    a, b, c = rows
    return (a[0]*(b[1]*c[2]-b[2]*c[1])
            - a[1]*(b[0]*c[2]-b[2]*c[0])
            + a[2]*(b[0]*c[1]-b[1]*c[0]))


def circles(m, target, row_b, row_c, B, C):
    result = []
    for b in combinations(B, 2):
        s = sum(b)
        for c in combinations(C, 2):
            if sum(c) != s:
                continue
            product = (Fraction((row_c-target)*b[0]*b[1]
                                + (target-row_b)*c[0]*c[1], row_c-row_b)
                       + (target-row_b)*(target-row_c))
            disc = s*s - 4*product
            if disc.denominator != 1 or disc <= 0:
                continue
            d = isqrt(disc.numerator)
            if d*d != disc or (s-d) % 2:
                continue
            a = [(s-d)//2, (s+d)//2]
            if not (0 <= a[0] < a[1] < m):
                continue
            points = [(x, target) for x in a] + [(x, row_b) for x in b] + [(x, row_c) for x in c]
            assert all(determinant4(q) == 0 for q in combinations(points, 4))
            result.append({'target_pair': a, 'exterior_b_pair': list(b),
                           'exterior_c_pair': list(c), 'six_points': points})
    return result


def main():
    specs = [
        {'m': 23, 'target': 0, 'row_b': 1, 'row_c': 2,
         'B': [4, 8, 11, 15, 19], 'C': [3, 8, 11, 12, 15], 'expected': 5},
        {'m': 22, 'target': 0, 'row_b': 2, 'row_c': 3,
         'B': [5, 10, 12, 17, 19], 'C': [5, 10, 12, 17, 19], 'expected': 7,
         'target_occupied': [8, 11, 13, 14]},
    ]
    for example in specs:
        args = {k: example[k] for k in ('m', 'target', 'row_b', 'row_c', 'B', 'C')}
        found = circles(**args)
        assert len(found) == example.pop('expected')
        example['circles'] = found
        example['circle_count'] = len(found)
        example['distinct_target_edges'] = len({tuple(c['target_pair']) for c in found})
        if 'target_occupied' in example:
            occupied = set(example['target_occupied'])
            assert all(len(occupied.intersection(c['target_pair'])) <= 1 for c in found)
            blocked = {x for c in found if occupied.intersection(c['target_pair'])
                       for x in c['target_pair'] if x not in occupied}
            example['blocked_target_blanks'] = sorted(blocked)
            assert len(blocked) == 6
    print(json.dumps({'statement': 'Counterexamples to proposed four/five-edge bounds; not threshold witnesses',
                      'examples': specs}, indent=2))


if __name__ == '__main__':
    main()
