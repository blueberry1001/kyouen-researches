#!/usr/bin/env python3
"""Independent exact geometry and occupied-target audit of all 14 heavy pairs.

The candidate list is produced by q46_pair_independent_star.cpp.  Its exhaustive
support scan is a separate part of the proof.  Here every listed target graph
is regenerated using rational root products; all four-point determinants are
checked; and all choices of up to four occupied target vertices are evaluated.
The star-forest criterion of the producer is not used for the blocker bound.
"""
from fractions import Fraction
from itertools import combinations
from math import isqrt
from pathlib import Path
import json


def determinant4(points):
    x, y = points[0]
    rows = [[u*u+v*v-x*x-y*y, u-x, v-y] for u, v in points[1:]]
    a, b, c = rows
    return (a[0]*(b[1]*c[2]-b[2]*c[1])
            - a[1]*(b[0]*c[2]-b[2]*c[0])
            + a[2]*(b[0]*c[1]-b[1]*c[0]))


def main():
    directory = Path(__file__).resolve().parents[1]
    data = json.loads((directory/'q46_pair_independent_star.json').read_text())
    results = []
    for candidate in data['all_seven_edge_candidates']:
        B, C = candidate['B'], candidate['C']
        t, v, w = {2: (0, 2, 3), 4: (1, 0, 3)}[candidate['shape']]
        circles = []
        for b in combinations(B, 2):
            s = sum(b)
            for c in combinations(C, 2):
                if sum(c) != s:
                    continue
                product = (Fraction((w-t)*b[0]*b[1]+(t-v)*c[0]*c[1], w-v)
                           + (t-v)*(t-w))
                disc = s*s - 4*product
                if disc.denominator != 1 or disc <= 0:
                    continue
                root = isqrt(disc.numerator)
                if root*root != disc or (s-root) % 2:
                    continue
                target = ((s-root)//2, (s+root)//2)
                coordinates = list(B) + list(c) + list(target)
                if max(coordinates)-min(coordinates) > 67:
                    continue
                points = [(x,t) for x in target] + [(x,v) for x in b] + [(x,w) for x in c]
                assert all(determinant4(p) == 0 for p in combinations(points,4))
                circles.append(target)
        assert len(circles) == 7
        edges = sorted(set(circles))
        assert edges == [tuple(e) for e in candidate['target_edges']]
        vertices = sorted({x for edge in edges for x in edge})
        best = 0
        choices = 0
        witness = []
        for k in range(5):
            for occupied in combinations(vertices, k):
                choices += 1
                occupied = set(occupied)
                # No safety condition is imposed: this is a relaxed upper bound.
                blocked = {x for edge in edges if occupied.intersection(edge)
                           for x in edge if x not in occupied}
                if len(blocked) > best:
                    best = len(blocked)
                    witness = sorted(occupied)
        assert best <= 6
        results.append({'shape': candidate['shape'], 'B': sorted(B), 'C': sorted(C),
                        'target_edges': edges, 'occupied_target_choices': choices,
                        'maximum_blocked_blanks_with_at_most_four_target_stones': best,
                        'maximizing_target_stones': witness})
    assert len(results) == 14
    print(json.dumps({'status': 'passed', 'candidate_count': len(results),
                      'four_point_determinants_checked': 14*7*15,
                      'total_occupied_target_choices': sum(r['occupied_target_choices'] for r in results),
                      'scope': 'Independent audit of every listed heavy candidate, not a second exhaustive support scan',
                      'candidates': results}, indent=2))


if __name__ == '__main__':
    main()
