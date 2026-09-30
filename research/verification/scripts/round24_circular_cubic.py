"""Exact supplemental checks for the B356/B357 infinite construction.

All coordinates are Fractions or integers; no shared geometry/search module
is imported. General validity follows from the circle polynomial identity.
"""
from fractions import Fraction
from itertools import combinations
from math import prod
from pathlib import Path
import hashlib
import json
import time


def point(exponent):
    u = Fraction(2)**exponent
    t = (u-1)/(u+1)
    x = (1-t*t)/(1+t*t)
    return x, t*x


def determinant(points):
    x0, y0 = points[0]
    a, b, c = [(x-x0, y-y0, (x-x0)**2+(y-y0)**2) for x, y in points[1:]]
    return (a[0]*(b[1]*c[2]-b[2]*c[1])
            - a[1]*(b[0]*c[2]-b[2]*c[0])
            + a[2]*(b[0]*c[1]-b[1]*c[0]))


def invert(points, center):
    cx, cy = center
    result = []
    for x, y in points:
        x, y = x-cx, y-cy
        norm = x*x+y*y
        assert norm
        result.append((x/norm, y/norm))
    return result


def main():
    started = time.perf_counter()
    source = Path(__file__).resolve()
    records = []
    for m in range(1, 4):
        k = 12*m
        rational_stones = [point(i) for i in range(1, k+1)]
        scale = prod((2**i+1)*(2**(2*i)+1) for i in range(1, k+1))
        n = 2*scale+1

        def integer_point(p):
            x, y = p
            x, y = scale*x, scale*(y+1)
            assert x.denominator == y.denominator == 1
            return int(x), int(y)

        stones = [integer_point(p) for p in rational_stones]
        assert len(set(stones)) == k
        assert all(0 <= x < n and 0 <= y < n for x, y in stones)
        safety_checks = 0
        for ids in combinations(range(k), 4):
            assert determinant([stones[i] for i in ids]) != 0
            safety_checks += 1
        counts = []
        inverse_checks = 0
        targets = []
        for c in range(11*m+1, 12*m+1):
            rational_target = point(-c)
            target = integer_point(rational_target)
            targets.append(target)
            assert target not in stones and 0 <= target[0] < n and 0 <= target[1] < n
            b = 0
            for ids in combinations(range(k), 3):
                predicted = sum(i+1 for i in ids) == c
                actual = determinant([stones[i] for i in ids]+[target]) == 0
                assert actual == predicted
                b += actual
            assert b >= m*m
            # Explicit m^2 different triples in three disjoint index intervals.
            lower_bound_triples = {(i, j, c-i-j) for i in range(1, m+1) for j in range(3*m+1, 4*m+1)}
            assert len(lower_bound_triples) == m*m
            assert all(1 <= i < j < ell <= k and i+j+ell == c for i,j,ell in lower_bound_triples)
            counts.append({'c': c, 'b': b, 'certified_lower_bound': m*m})
            if m <= 2:
                transformed = invert(rational_stones, rational_target)
                for ids in combinations(range(k), 4):
                    assert determinant([transformed[i] for i in ids]) != 0
                    inverse_checks += 1
        assert len(set(targets)) == m
        records.append({'m': m, 'k': k, 'n': n, 'scale': scale,
                        'stone_coordinates': stones, 'target_coordinates': targets,
                        'coverage_counts': counts, 'safe_four_sets_checked': safety_checks,
                        'inverted_safe_four_sets_checked': inverse_checks})
        print('m', m, 'k', k, 'b counts', [r['b'] for r in counts],
              'integer safety and coverage PASS', flush=True)
    # Check the four-point sum rule for mixed positive/negative exponents directly.
    exponents = list(range(1, 9))+[-9, -10, -11, -12]
    mixed_points = [point(e) for e in exponents]
    identity_checks = 0
    for ids in combinations(range(len(exponents)), 4):
        assert (determinant([mixed_points[i] for i in ids]) == 0) == (sum(exponents[i] for i in ids) == 0)
        identity_checks += 1
    output = {'records': records, 'uniform_c': '1/144', 'target_count': 'k/12',
              'mixed_four_point_identity_checks': identity_checks,
              'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'seconds': time.perf_counter()-started}
    (source.parents[1] / 'round24_circular_cubic_verified.json').write_text(json.dumps(output, indent=2)+'\n', encoding='utf-8')
    print('PASS exact integer construction and inverted safety; c=1/144, k/12 high-coverage points', flush=True)


if __name__ == '__main__':
    main()
