"""Independent full-state verifier for the B252 4x4 comparison witness.

No search/geometry modules are imported. Geometry uses translated integer
determinants; legality uses direct containment of four-point masks.
"""
from collections import Counter
from itertools import combinations
from pathlib import Path
import hashlib
import json


def forbidden(points):
    x0, y0 = points[0]
    a, b, c = [(x-x0, y-y0, (x-x0)**2+(y-y0)**2) for x, y in points[1:]]
    return (a[0]*(b[1]*c[2]-b[2]*c[1])
            - a[1]*(b[0]*c[2]-b[2]*c[0])
            + a[2]*(b[0]*c[1]-b[1]*c[0])) == 0


def members(mask):
    while mask:
        bit = mask & -mask
        yield bit.bit_length()-1
        mask ^= bit


def solve(quads):
    full = (1 << 16)-1
    legal_masks = {}

    def visit(s, tail):
        legal = full ^ s
        for q in quads:
            missing = q & ~s
            assert missing
            if missing & (missing-1) == 0:
                legal &= ~missing
        legal_masks[s] = legal
        candidates = legal & tail
        while candidates:
            bit = candidates & -candidates
            candidates ^= bit
            visit(s | bit, candidates)

    visit(0, full)
    grundy = {}
    for s in sorted(legal_masks, reverse=True):
        values = {grundy[s | (1 << p)] for p in members(legal_masks[s])}
        value = 0
        while value in values:
            value += 1
        grundy[s] = value
    layers = Counter(s.bit_count() for s in legal_masks)
    return {'g0': grundy[0], 'safe_states': len(legal_masks),
            'maximum_size': max(layers), 'layer_counts': dict(sorted(layers.items())),
            'winning_first_moves': [p for p in range(16) if grundy[1 << p] == 0]}


def main():
    source = Path(__file__).resolve()
    root = source.parents[1]
    files = [root / name for name in ('round22_b252_n4_all_geometry.json',
              'round22_b252_n4_all_scan.json', 'round22_b252_scattered_cases.json',
              'round22_b252_scattered_scan.json')]
    data = [p.read_bytes() for p in files]
    geometry, bundle_scan, scattered_cases, scattered_scan = map(json.loads, data)
    points = [(x, y) for y in range(4) for x in range(4)]
    quads = [sum(1 << p for p in ids) for ids in combinations(range(16), 4)
             if forbidden([points[p] for p in ids])]
    assert len(quads) == 194 and quads == geometry['quad_masks']
    grouped_indices = []
    quad_index = {q: qi for qi, q in enumerate(quads)}
    for gi, group in enumerate(geometry['groups']):
        assert group['group_id'] == gi
        a, b, c, d = group['coefficients']
        ids = [p for p, (x, y) in enumerate(points) if a*(x*x+y*y)+b*x+c*y+d == 0]
        assert ids == group['point_indices']
        indices = sorted(quad_index[sum(1 << p for p in subset)] for subset in combinations(ids, 4))
        assert indices == group['quad_indices']
        grouped_indices.extend(indices)
    assert sorted(grouped_indices) == list(range(194))
    central_points = [p for p, (x, y) in enumerate(points) if (2*x-3)**2+(2*y-3)**2 == 10]
    assert len(central_points) == 8
    circle_masks = {sum(1 << p for p in ids) for ids in combinations(central_points, 4)}
    circle_removed = [qi for qi, q in enumerate(quads) if q in circle_masks]
    assert len(circle_removed) == 70
    scatter_result = next(case for case in scattered_scan['cases'] if case['outcome'] == 0)
    scatter = next(case for case in scattered_cases if case['name'] == scatter_result['name'])
    scattered_removed = scatter['removed_indices']
    assert len(scattered_removed) == len(set(scattered_removed)) == 70
    assert not set(scattered_removed) & set(circle_removed)
    assert set(scattered_removed) <= set(range(194))
    assert scatter['kept_indices'] == scatter_result['kept_indices']
    group_of = {qi: g['group_id'] for g in geometry['groups'] for qi in g['quad_indices']}
    counts = Counter(group_of[qi] for qi in scattered_removed)
    assert len(counts) == scatter['removed_curve_count'] >= 20
    assert max(counts.values()) == scatter['maximum_quads_removed_on_one_curve'] < 15
    results = {}
    for label, removed in [('standard', []), ('one_circle', circle_removed), ('scattered', scattered_removed)]:
        results[label] = solve([q for qi, q in enumerate(quads) if qi not in set(removed)])
        print(label, results[label], flush=True)
    assert results['standard']['g0'] == results['scattered']['g0'] == 0
    assert results['one_circle']['g0'] > 0
    circle_result = next(case for case in bundle_scan['cases']
                         if case['name'] == 'B252_n4_circle_37')
    assert circle_result['kept_indices'] == [qi for qi in range(194) if qi not in set(circle_removed)]
    assert circle_result['outcome'] == bool(results['one_circle']['g0'])
    out = {'n': 4, 'central_circle_coefficients': [1, -3, -3, 2],
           'central_circle_point_indices': central_points,
           'circle_removed_indices': circle_removed,
           'scattered_case': scatter, 'scattered_removed_curve_counts': dict(sorted(counts.items())),
           'circle_removed_coordinates': [[points[p] for p in members(quads[qi])] for qi in circle_removed],
           'scattered_removed_coordinates': [[points[p] for p in members(quads[qi])] for qi in scattered_removed],
           'results': results, 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
           'input_sha256': {p.name: hashlib.sha256(b).hexdigest() for p, b in zip(files, data)}}
    (root / 'round22_b252_verified.json').write_text(json.dumps(out, indent=2)+'\n', encoding='utf-8')
    print('PASS: 70 removals on one circle reverse the winner; 70 scattered removals do not', flush=True)


if __name__ == '__main__':
    main()
