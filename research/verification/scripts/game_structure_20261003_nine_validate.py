#!/usr/bin/env python3
"""Independent checks of the 81-bit bounded-search primitives.

Reads --probe JSONL. Geometry uses the lifted 4x4 determinant expanded by
its squared-radius column, not the search's translated 3x3 formula. Legal
moves and residual games are obtained by scanning every forbidden quadruple.
This validates primitives, not an incomplete empty-board outcome.
"""
import argparse
from functools import lru_cache
from itertools import combinations
import json
from math import comb
from pathlib import Path


def validate(path):
    lines = [json.loads(line) for line in Path(path).read_text().splitlines()]
    header, records = lines[0], lines[1:]
    assert header['n'] == 9 and len(records) == header['samples']
    n, v = 9, 81
    all_points = (1 << v) - 1
    coordinates = [(p % n, p // n) for p in range(v)]
    radius = [x*x + y*y for x, y in coordinates]
    area = {}
    for a, b, c in combinations(range(v), 3):
        ax, ay = coordinates[a]
        bx, by = coordinates[b]
        cx, cy = coordinates[c]
        area[a, b, c] = ax*(by-cy) + bx*(cy-ay) + cx*(ay-by)
    forbidden = []
    for a, b, c, d in combinations(range(v), 4):
        determinant = (radius[a]*area[b, c, d]
                       - radius[b]*area[a, c, d]
                       + radius[c]*area[a, b, d]
                       - radius[d]*area[a, b, c])
        if determinant == 0:
            forbidden.append((1 << a) | (1 << b) | (1 << c) | (1 << d))
    assert len(forbidden) == header['forbidden'] == 29152

    transforms = []
    for reflect in range(2):
        for turns in range(4):
            mapping = []
            for x, y in coordinates:
                if reflect:
                    x = n - 1 - x
                for _ in range(turns):
                    x, y = n - 1 - y, x
                mapping.append(1 << (x + n*y))
            transforms.append(mapping)

    checked_endgames = 0
    checked_hi = 0
    max_stones = 0
    ranks = {}
    for record in records:
        s = record['occupied_lo'] | (record['occupied_hi'] << 64)
        legal = record['legal_lo'] | (record['legal_hi'] << 64)
        canonical = record['canonical_lo'] | (record['canonical_hi'] << 64)
        assert not (s | legal) & ~all_points
        assert not s & legal
        blocked = 0
        residuals = []
        for q in forbidden:
            occupied_count = (q & s).bit_count()
            assert occupied_count < 4
            if occupied_count == 3:
                blocked |= q & ~s
            if not q & ~(s | legal):
                residuals.append(q & ~s)
        assert legal == all_points & ~(s | blocked)
        points = [p for p in range(v) if s >> p & 1]
        expected = min(sum(mapping[p] for p in points) for mapping in transforms)
        assert canonical == expected
        canonical_points = [p for p in range(v) if canonical >> p & 1]
        rank = (sum(comb(v, k) for k in range(len(points)))
                + sum(comb(p, j) for j, p in enumerate(canonical_points, 1)))
        assert record['rank'] == rank
        assert ranks.setdefault(rank, canonical) == canonical
        if legal.bit_count() <= 6:
            @lru_cache(None)
            def outcome(added):
                moves = [1 << p for p in range(v) if legal >> p & 1
                         and not added >> p & 1
                         and not any((added | (1 << p)) & edge == edge
                                     for edge in residuals)]
                return not moves or any(not outcome(added | move) for move in moves)
            assert record['misere'] == int(outcome(0))
            checked_endgames += 1
        else:
            assert record['misere'] == -1
        checked_hi += bool(s >> 64)
        max_stones = max(max_stones, len(points))
    assert checked_endgames and checked_hi
    return {'n': n, 'forbidden_quadruples': len(forbidden),
            'states_checked': len(records), 'tiny_endgames_checked': checked_endgames,
            'states_with_occupied_high_bits': checked_hi,
            'max_occupied_points': max_stones, 'verified': True,
            'scope': 'geometry, legal sets, D4, exact ranks, tiny outcomes; not root outcome'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('probes', type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.probes), indent=2))
