"""Exact checks for the all-n B256 minimum-family theorem.

A family of r disjoint forbidden four-sets has no constraints between its
components. Quotient states record free remaining points and remaining slots
on each four-set, so every legal move reduces total remaining capacity by one.
The general proof is in the companion markdown; finite checks are supplemental.
"""
from itertools import product
from pathlib import Path
import hashlib
import json


def determinant(points):
    x, y = points[0]
    a, b, c = [(u-x, v-y, (u-x)**2+(v-y)**2) for u, v in points[1:]]
    return (a[0]*(b[1]*c[2]-b[2]*c[1])
            - a[1]*(b[0]*c[2]-b[2]*c[0])
            + a[2]*(b[0]*c[1]-b[1]*c[0]))


def images(points, n):
    results = []
    for reflect in (False, True):
        for rotations in range(4):
            result = set()
            for x, y in points:
                if reflect:
                    x = n-1-x
                for _ in range(rotations):
                    x, y = n-1-y, x
                result.add((x, y))
            results.append(result)
    return results


def invariant(quad, n):
    return all(image == set(quad) for image in images(quad, n))


def quotient(v, r):
    assert v >= 4*r
    grundy = {}
    for free in range(v-4*r+1):
        for slots in product(range(4), repeat=r):
            options = set()
            if free:
                options.add(grundy[free-1, slots])
            for i, remaining in enumerate(slots):
                if remaining:
                    child = list(slots)
                    child[i] -= 1
                    options.add(grundy[free, tuple(child)])
            value = 0
            while value in options:
                value += 1
            grundy[free, slots] = value
            assert value == (free+sum(slots)) % 2
    return grundy[v-4*r, (3,)*r], len(grundy)


def main():
    source = Path(__file__).resolve()
    records = []
    quotient_states = 0
    for n in range(2, 21):
        outer = {(0, 0), (n-1, 0), (0, n-1), (n-1, n-1)}
        assert len(outer) == 4 and determinant(sorted(outer)) == 0 and invariant(outer, n)
        g_free, states = quotient(n*n, 0)
        quotient_states += states
        g_one, states = quotient(n*n, 1)
        quotient_states += states
        assert g_one != g_free
        record = {'n': n, 'outer_quad': sorted(outer), 'g_free': g_free, 'g_one': g_one}
        if n >= 3:
            c = n//2
            if n % 2:
                inner = {(c-1, c), (c+1, c), (c, c-1), (c, c+1)}
            else:
                inner = {(c-1, c-1), (c, c-1), (c-1, c), (c, c)}
            assert len(inner) == 4 and not outer & inner
            assert determinant(sorted(inner)) == 0 and invariant(inner, n)
            g_two, states = quotient(n*n, 2)
            quotient_states += states
            assert g_two == g_free
            record.update(inner_quad=sorted(inner), g_two=g_two)
        if n >= 4:
            # Two preserving families have disjoint D4 types: squares vs 2x1 rectangles.
            squares = [{(0, y), (1, y), (0, y+1), (1, y+1)} for y in (0, 2)]
            rectangles = [{(0, y), (2, y), (0, y+1), (2, y+1)} for y in (0, 2)]
            assert not squares[0] & squares[1] and not rectangles[0] & rectangles[1]
            assert all(determinant(sorted(q)) == 0 for q in squares+rectangles)
            assert all(image != other for q in squares for image in images(q, n) for other in rectangles)
            record.update(square_pair=[sorted(q) for q in squares],
                          rectangle_pair=[sorted(q) for q in rectangles])
        records.append(record)
    out = {'verified_n': [2, 20], 'quotient_states_checked': quotient_states,
           'records': records, 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
           'scope': 'Supplemental finite checks of explicit all-n constructions; proof is symbolic'}
    (source.parents[1] / 'round23_minimum_family_verified.json').write_text(json.dumps(out, indent=2)+'\n', encoding='utf-8')
    print('PASS: all n=2..20 constructions, D4 invariance, exact quotient mex;', quotient_states, 'quotient states')


if __name__ == '__main__':
    main()
