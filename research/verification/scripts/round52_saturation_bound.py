"""Finite checks for the general exponent >=2/3 saturation lower bound.

The infinite theorem is proved analytically in the report. These checks
validate the coefficient constants and direction-count charging, not a
finite extrapolation to an asymptotic claim.
"""
from collections import Counter
from fractions import Fraction
from itertools import combinations
from math import gcd, isqrt
from pathlib import Path
import hashlib
import json
from round25_forced_verify import bits, curve, geometry

ROOT = Path(__file__).resolve().parents[1]


def r2(number):
    remaining = number
    answer = 4
    p = 2
    while p*p <= remaining:
        exponent = 0
        while remaining % p == 0:
            remaining //= p
            exponent += 1
        if p % 4 == 3 and exponent % 2:
            return 0
        if p % 4 == 1:
            answer *= exponent+1
        p += 1
    if remaining % 4 == 3:
        return 0
    if remaining > 1 and remaining % 4 == 1:
        answer *= 2
    return answer


def main():
    coefficient_records = []
    total = 0
    for n in range(2, 11):
        points = [(x, y) for y in range(n) for x in range(n)]
        m = n-1
        checked = 0
        maximum_d = 0
        maximum_coeff = [0, 0, 0, 0]
        for triple in combinations(points, 3):
            a, b, c, d = curve(triple)
            if not a:
                continue
            checked += 1
            assert abs(a) <= 2*m*m and abs(b) <= 8*m**3 and abs(c) <= 8*m**3 and abs(d) <= 12*m**4
            disc = b*b+c*c-4*a*d
            assert 0 < disc <= 224*m**6
            maximum_d = max(maximum_d, disc)
            maximum_coeff = [max(old, abs(new)) for old, new in zip(maximum_coeff, [a, b, c, d])]
            # All three original grid points map to integer two-square representations.
            for x, y in triple:
                assert (2*a*x+b)**2+(2*a*y+c)**2 == disc
        coefficient_records.append({'n': n, 'proper_three_point_circles_checked': checked,
                                    'maximum_primitive_coefficient_magnitudes': maximum_coeff,
                                    'maximum_integer_norm_D': maximum_d, 'uniform_norm_bound': 224*m**6})
        total += checked
    directions = []
    for shell in range(1, 101):
        actual = set()
        for x in range(-shell, shell+1):
            for y in [-shell, shell]:
                if gcd(abs(x), abs(y)) == 1:
                    actual.add(min((x, y), (-x, -y)))
        for y in range(-shell+1, shell):
            for x in [-shell, shell]:
                if gcd(abs(x), abs(y)) == 1:
                    actual.add(min((x, y), (-x, -y)))
        assert len(actual) <= 4*shell
        directions.append({'shell': shell, 'unoriented_primitive_directions': len(actual), 'bound': 4*shell})
    records = json.loads((ROOT/'round47_cover_verified.json').read_text())['n4_all_maximal_records']
    line_checks = []
    for row in records:
        ids = list(bits(row['S_mask']))
        stones = [(p % 4, p // 4) for p in ids]
        k = len(stones)
        line_triples = []
        for t in combinations(stones, 3):
            a, b, c, d = curve(t)
            if a:
                continue
            ux, uy = t[1][0]-t[0][0], t[1][1]-t[0][1]
            g = gcd(abs(ux), abs(uy))
            direction = min((ux//g, uy//g), (-ux//g, -uy//g))
            shell = max(abs(z) for z in direction)
            completions = sum(b*x+c*y+d == 0 for y in range(4) for x in range(4))-3
            line_triples.append((direction, shell, completions))
        assert len(line_triples)*3 <= k*(k-1)//2
        assert all(number <= k//3 for number in Counter(t[0] for t in line_triples).values())
        line_sum = sum(t[2] for t in line_triples)
        for cutoff in range(1, 8):
            low = sum(t[2] for t in line_triples if t[1] <= cutoff)
            high = line_sum-low
            low_bound = Fraction(4*k*4*cutoff, 3)
            high_bound = Fraction(4*k*(k-1), 6*cutoff)
            assert low <= low_bound and high <= high_bound
        line_checks.append({'S_mask': row['S_mask'], 'k': k, 'three_stone_lines': len(line_triples), 'sum_line_completions': line_sum})
    circle_examples = []
    for n in [4, 8, 9, 10]:
        points, _, masks = geometry(n)
        proper = []
        for mask in masks:
            ids = list(bits(mask))
            coeff = curve([points[p] for p in ids[:3]])
            if coeff[0]:
                proper.append((len(ids), coeff, ids))
        size = max(t[0] for t in proper)
        _, (a, b, c, d), ids = next(t for t in proper if t[0] == size)
        norm = b*b+c*c-4*a*d
        full_representations = r2(norm)
        assert size <= full_representations
        circle_examples.append({'n': n, 'maximum_proper_circle_grid_points': size, 'coefficients': [a, b, c, d],
                                'point_ids': ids, 'integer_norm_D': norm, 'r2_D': full_representations})
    files = ['scripts/round52_saturation_bound.py', 'scripts/round25_forced_verify.py',
             'round47_cover_verified.json', 'round10-circle-denominator.md']
    out = {'B095_original_verdict': 'PARTIAL', 'B096_original_verdict': 'PARTIAL',
           'general_standard_square_theorem': 'For every epsilon>0, all sufficiently large n have s_n>n^(2/3-epsilon).',
           'equivalent_exponent_lower_bound': 'liminf(log(s_n)/log(n)) >= 2/3',
           'proper_circle_uniform_bound': 'R(n) <= 4 max_{1<=D<=224(n-1)^6} tau(D) = n^o(1)',
           'line_cover_bound_for_any_integer_cutoff_D_at_least_1': '(4/3)*n*k*D + n*k*(k-1)/(6*D)',
           'line_only_saturation_lower_bound': '(1-o(1))*(9/8)^(1/3)*n^(2/3)',
           'coefficient_checks': coefficient_records, 'total_proper_triples_checked': total,
           'primitive_direction_shell_checks': directions, 'n4_all_928_maximal_line_checks': line_checks,
           'maximum_circle_examples': circle_examples,
           'limits': 'No upper bound s_n<=n^(2/3+o(1)) or s_n=o(n) is proved.',
           'primary_source': 'https://kconrad.math.uconn.edu/blurbs/ugradnumthy/Zinotes.pdf',
           'sha256': {f: hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}}
    (ROOT/'round52_saturation_bound_verified.json').write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('PASS coefficient triples', total, '; direction shells 1..100; all928 n4 maximal line checks; exponent lower bound proved in report')


if __name__ == '__main__':
    main()
