"""Exact finite checks for B455/B456; general results are proved in the reports.

Enumerates all norms <= 50000 for the listed exact center denominators.
Also checks Gaussian product constructions without floating-point arithmetic.
"""
from collections import defaultdict
from fractions import Fraction
from math import gcd, isqrt
from pathlib import Path
import json


def factor(n):
    result = {}
    p = 2
    while p * p <= n:
        while n % p == 0:
            result[p] = result.get(p, 0) + 1
            n //= p
        p += 1
    if n > 1:
        result[n] = result.get(n, 0) + 1
    return result


def squarefree_part(ff):
    value = 1
    for p, e in ff.items():
        if e % 2:
            value *= p
    return value


def representation_count(ff):
    total = 4
    for p, e in ff.items():
        if p % 4 == 3 and e % 2:
            return 0
        if p % 4 == 1:
            total *= e + 1
    return total


def multiply(z, w):
    a, b = z
    c, d = w
    return a * c - b * d, a * d + b * c


def gaussian_prime(p):
    for a in range(1, isqrt(p) + 1):
        b = isqrt(p - a * a)
        if b * b + a * a == p:
            return a, b
    raise AssertionError(p)


def primitive_classes(points, q):
    classes = defaultdict(list)
    for u, v in points:
        a, b = (-u) % q, (-v) % q
        if gcd(gcd(a, b), q) == 1:
            classes[(a, b)].append((u, v))
    return classes


def main():
    limit = 50000
    qs = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 16)
    reps = [[] for _ in range(limit + 1)]
    for u in range(-isqrt(limit), isqrt(limit) + 1):
        bound = isqrt(limit - u * u)
        for v in range(-bound, bound + 1):
            n = u * u + v * v
            if n:
                reps[n].append((u, v))
    records = {q: [] for q in qs}
    best = {q: 0 for q in qs}
    seen = {q: set() for q in qs}
    seed_classes = {q: set() for q in qs}
    restricted_best = {q: 0 for q in qs}
    occupied_checks = 0
    rotation_checks = 0
    rotation_orbits = 0
    nonuniform_example = None
    for n in range(1, limit + 1):
        ff = factor(n)
        assert len(reps[n]) == representation_count(ff)
        sf = squarefree_part(ff)
        for q in qs:
            classes = primitive_classes(reps[n], q)
            occupied_checks += len(classes)
            if not classes:
                continue
            if q >= 3:
                orbits = set()
                histogram = defaultdict(int)
                for (a, b), zs in classes.items():
                    orbit = {(a, b), ((-b) % q, a),
                             ((-a) % q, (-b) % q), (b, (-a) % q)}
                    assert len(orbit) == 4
                    assert all(len(classes[ab]) == len(zs) for ab in orbit)
                    histogram[len(zs)] += 1
                    orbits.add(min(orbit))
                    rotation_checks += 1
                assert all(multiplicity % 4 == 0 for multiplicity in histogram.values())
                rotation_orbits += len(orbits)
                if n == 25 and q == 6:
                    assert set(histogram) == {1, 2}
                    nonuniform_example = {
                        'norm': n, 'q': q,
                        'primitive_center_residue_counts': [
                            {'a': a, 'b': b, 'count': len(zs)}
                            for (a, b), zs in sorted(classes.items())],
                        'count_histogram': dict(histogram),
                    }
            (a, b), points = max(classes.items(), key=lambda item: len(item[1]))
            count = len(points)
            if sf in seed_classes[q]:
                restricted_best[q] = max(restricted_best[q], count)
            if count <= best[q]:
                continue
            best[q] = count
            new_type = sf not in seen[q]
            if new_type and len(seed_classes[q]) < 3:
                seed_classes[q].add(sf)
                restricted_best[q] = max(restricted_best[q], count)
            rational_parents = [r['norm'] for r in records[q]
                                if r['squarefree_part'] == sf]
            integer_parents = [r['norm'] for r in records[q]
                               if n % r['norm'] == 0
                               and isqrt(n // r['norm']) ** 2 == n // r['norm']]
            assert not new_type or not rational_parents
            assert set(integer_parents) <= set(rational_parents)
            lattice = sorted(((u + a) // q, (v + b) // q) for u, v in points)
            assert all((q*x-a)**2 + (q*y-b)**2 == n for x, y in lattice)
            records[q].append({
                'norm': n, 'radius_squared': str(Fraction(n, q*q)),
                'point_count': count, 'factors': ff, 'squarefree_part': sf,
                'new_square_class_among_earlier_records': new_type,
                'earlier_record_norms_with_rational_radius_ratio': rational_parents,
                'earlier_record_norms_with_integer_radius_ratio': integer_parents,
                'center_numerator': [a, b], 'center_denominator': q,
                'all_lattice_points': lattice,
            })
            seen[q].add(sf)
    assert [(r['norm'], r['point_count']) for r in records[3]] == [
        (r['norm'], r['point_count']) for r in records[4]]

    # Independent finite check of the two elementary exponent inequalities.
    for e in range(129):
        assert e + 1 <= 2 ** e
        if e % 2 == 0:
            assert e + 1 <= 3 ** (e // 2)

    construction = []
    for q in qs:
        primes = []
        p = 5
        while len(primes) < 6:
            if p % 4 == 1 and q % p and factor(p) == {p: 1}:
                primes.append(p)
            p += 1
        for exponent in (1, 2):
            points = {(1, 0), (0, 1), (-1, 0), (0, -1)}
            norm = 1
            for t, p in enumerate(primes, 1):
                pi = gaussian_prime(p)
                conjugate = (pi[0], -pi[1])
                options = (pi, conjugate) if exponent == 1 else (
                    multiply(pi, pi), (p, 0), multiply(conjugate, conjugate))
                points = {multiply(z, w) for z in points for w in options}
                norm *= p ** exponent
                expected = 4 * (exponent + 1) ** t
                assert len(points) == expected
                assert all(u*u + v*v == norm for u, v in points)
                classes = primitive_classes(points, q)
                assert sum(map(len, classes.values())) == expected
                largest = max(map(len, classes.values()))
                assert largest * q*q >= expected
                construction.append({
                    'q': q, 'prime_count': t, 'primes': primes[:t],
                    'exponent': exponent, 'norm': norm,
                    'representation_count': expected,
                    'occupied_primitive_residue_classes': len(classes),
                    'largest_class': largest,
                    'pigeonhole_guarantee': (expected + q*q - 1) // (q*q),
                })
        # The fixed-square-class lower bound also permits d sharing primes with q.
        for d in (2, 5, 10, 13, 65):
            primes = []
            p = 5
            while len(primes) < 4:
                if p % 4 == 1 and (q*d) % p and factor(p) == {p: 1}:
                    primes.append(p)
                p += 1
            points = set(reps[d])
            norm = d
            for t, p in enumerate(primes, 1):
                pi = gaussian_prime(p)
                conjugate = (pi[0], -pi[1])
                options = (multiply(pi, pi), (p, 0), multiply(conjugate, conjugate))
                points = {multiply(z, w) for z in points for w in options}
                norm *= p*p
                expected = len(reps[d]) * 3**t
                assert len(points) == expected
                assert all(u*u + v*v == norm for u, v in points)
                classes = primitive_classes(points, q)
                assert sum(map(len, classes.values())) == expected
                largest = max(map(len, classes.values()))
                assert largest*q*q >= expected
                construction.append({
                    'q': q, 'fixed_squarefree_part': d, 'prime_count': t,
                    'primes': primes[:t], 'exponent': 2, 'norm': norm,
                    'representation_count': expected,
                    'occupied_primitive_residue_classes': len(classes),
                    'largest_class': largest,
                    'pigeonhole_guarantee': (expected+q*q-1)//(q*q),
                })
    data = {
        'B455': 'REFUTED by the free order-four rotation action on primitive residue classes',
        'B456': 'SUPPORTED by the general proof, not by this finite enumeration',
        'record_definition': 'strict increase of the maximum complete-circle point count over exact-denominator centers, at a new radius threshold',
        'norm_limit': limit, 'denominators': qs,
        'all_norm_representation_formula_checks': limit,
        'occupied_primitive_classes': occupied_checks,
        'q_ge_3_rotation_class_checks': rotation_checks,
        'q_ge_3_free_rotation_orbits': rotation_orbits,
        'nonuniform_residue_example': nonuniform_example,
        'records': records,
        'finite_seed_comparison_not_an_asymptotic_proof': {
            q: {'first_three_record_square_classes': sorted(seed_classes[q]),
                'restricted_max_at_limit': restricted_best[q],
                'unrestricted_max_at_limit': best[q]} for q in qs},
        'gaussian_product_checks': construction,
    }
    path = Path(__file__).resolve().parents[1] / 'round11_circle_records.json'
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('norms', limit, 'occupied classes', occupied_checks,
          'product checks', len(construction))
    for q in qs:
        print('q', q, 'records', len(records[q]), 'types', len(seen[q]),
              'maximum', best[q], 'seed maximum', restricted_best[q])
    print(path)


if __name__ == '__main__':
    main()
