#!/usr/bin/env python3
"""Exact g=2 witnesses immediately before all three four-row thresholds.

This verifier does not use chord profiles or the deficient-row search.
It builds circle/line equations from all board triples by cofactor expansion,
then computes the entire (depth at most two) game above each explicit position.
Python standard library only. Output is deterministic JSON on stdout.
"""
from functools import cache
from itertools import combinations
import json
from math import gcd


def det3(a, b, c):
    return (a[0] * (b[1] * c[2] - b[2] * c[1])
            - a[1] * (b[0] * c[2] - b[2] * c[0])
            + a[2] * (b[0] * c[1] - b[1] * c[0]))


def constraints(m, q):
    points = [(x, y) for y in range(4) for x in range(m)]
    lifted = [(x * x + y * y, x, y, 1) for x, y in points]
    equations = set()
    triples = 0
    for triple in combinations(lifted, 3):
        triples += 1
        coeff = tuple((-1) ** j * det3(*[p[:j] + p[j + 1:] for p in triple])
                      for j in range(4))
        divisor = 0
        for value in coeff:
            divisor = gcd(divisor, value)
        assert divisor
        if next(value for value in coeff if value) < 0:
            divisor = -divisor
        equations.add(tuple(value // divisor for value in coeff))
    masks = []
    lines = circles = 0
    for coeff in sorted(equations):
        mask = sum(1 << k for k, p in enumerate(lifted)
                   if sum(a * b for a, b in zip(coeff, p)) == 0)
        if mask.bit_count() >= q:
            masks.append(mask)
            if coeff[0]:
                circles += 1
            else:
                lines += 1
    return masks, dict(board_points=len(points), board_triples=triples,
                       distinct_equations=len(equations), lines=lines, circles=circles)


def verify(q, m, maximal_rows, removed):
    masks, geometry = constraints(m, q)
    capacity = 4 * (q - 1)
    maximal = sum(1 << (y * m + x) for y, row in enumerate(maximal_rows) for x in row)
    removed_index = removed[1] * m + removed[0]
    assert maximal >> removed_index & 1
    initial = maximal ^ (1 << removed_index)

    def safe(s):
        return all((s & curve).bit_count() < q for curve in masks)

    def moves(s):
        return [k for k in range(4 * m) if not s >> k & 1 and safe(s | (1 << k))]

    assert maximal.bit_count() == capacity - 1
    assert initial.bit_count() == capacity - 2
    assert safe(maximal) and not moves(maximal)
    assert safe(initial)
    visited = set()

    @cache
    def grundy(s):
        visited.add(s)
        assert s.bit_count() <= capacity
        values = {grundy(s | (1 << k)) for k in moves(s)}
        mex = 0
        while mex in values:
            mex += 1
        return mex

    value = grundy(initial)
    assert value == 2
    tree = []
    for s in sorted(visited, key=lambda x: (x.bit_count(), x)):
        extra = [[k % m, k // m] for k in range(4 * m) if (s ^ initial) >> k & 1]
        legal = [{'point': [k % m, k // m], 'child_grundy': grundy(s | (1 << k))}
                 for k in moves(s)]
        tree.append({'added_points': extra, 'stones': s.bit_count(),
                     'grundy': grundy(s), 'legal_moves': legal})
    assert all(len(node['added_points']) <= 2 for node in tree)
    return {'q': q, 'm': m, 'stabilization_length': m + 1,
            'maximal_witness_rows': maximal_rows, 'removed_point': list(removed),
            'initial_rows': [[x for x in row if (x, y) != removed]
                             for y, row in enumerate(maximal_rows)],
            'initial_stones': initial.bit_count(), 'grundy': value,
            'legal_first_moves': tree[0]['legal_moves'],
            'reachable_positions': len(visited),
            'all_reachable_positions': tree, 'independent_geometry': geometry}


def main():
    data = [
        (8, 10, [[0, 1, 2, 4, 7, 9], [1, 3, 4, 5, 6, 8, 9],
                 [1, 3, 4, 5, 6, 8, 9], [2, 3, 4, 5, 6, 7, 8]], (7, 0)),
        (7, 12, [[5, 6, 7, 8, 9, 10], [0, 1, 2, 3, 7],
                 [5, 6, 7, 8, 9, 11], [5, 6, 7, 8, 9, 10]], (7, 1)),
        (6, 15, [[8, 10, 13, 14], [3, 5, 6, 9, 10],
                 [2, 3, 8, 11, 12], [4, 5, 9, 10, 11]], (8, 0)),
    ]
    result = {
        'statement': 'For q=6,7,8 on four-row boards, the last nonstable length '
                     'has an explicit safe position of Grundy value 2.',
        'proof_scope': 'Three explicit positions; complete descendant games, '
                       'not a census or an upper bound for other positions.',
        'cases': [verify(*args) for args in data],
    }
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
