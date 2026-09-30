"""Audit n=6 geometry, full D4 coverage, and two independent single-removal solvers."""
from itertools import combinations
from pathlib import Path
import hashlib
import json


def det3(rows):
    a, b, c = rows
    return (a[0]*(b[1]*c[2]-b[2]*c[1])
            - a[1]*(b[0]*c[2]-b[2]*c[0])
            + a[2]*(b[0]*c[1]-b[1]*c[0]))


def det4(rows):
    return sum((-1)**j * rows[0][j]
               * det3([[row[k] for k in range(4) if k != j] for row in rows[1:]])
               for j in range(4))


def main():
    source = Path(__file__).resolve()
    root = source.parents[1]
    files = [root / f'round23_b251_n6_{suffix}'
             for suffix in ('geometry.json', 'scan.json', 'incremental.json', 'input.txt')]
    contents = [file.read_bytes() for file in files]
    geometry, scan, incremental = map(json.loads, contents[:3])
    n = geometry['n']
    assert n == 6
    points = [(x, y) for y in range(n) for x in range(n)]
    rows = [(x*x+y*y, x, y, 1) for x, y in points]
    quads = [sum(1 << p for p in ids) for ids in combinations(range(n*n), 4)
             if det4([rows[p] for p in ids]) == 0]
    assert quads == geometry['quad_masks'] and len(quads) == 2491
    quad_id = {q: qi for qi, q in enumerate(quads)}
    actual_orbits = {}
    for qi, q in enumerate(quads):
        ids = [p for p in range(n*n) if q & (1 << p)]
        images = set()
        for reflect in (False, True):
            for rotations in range(4):
                image = 0
                for p in ids:
                    x, y = points[p]
                    if reflect:
                        x = n-1-x
                    for _ in range(rotations):
                        x, y = n-1-y, x
                    image |= 1 << (x+n*y)
                images.add(quad_id[image])
        actual_orbits.setdefault(min(images), set()).add(qi)
    assert actual_orbits == {record['representative']: set(record['members']) for record in geometry['orbits']}
    assert len(actual_orbits) == 389
    assert sorted(qi for orbit in actual_orbits.values() for qi in orbit) == list(range(2491))
    assert scan['standard_outcome'] == incremental['standard_outcome'] == 1
    assert len(scan['cases']) == len(incremental['cases']) == 389
    for (rep, members), a, b in zip(sorted(actual_orbits.items()), scan['cases'], incremental['cases'], strict=True):
        assert rep == a['removed_index'] == b['removed_index']
        assert a['outcome'] == b['outcome'] == 1
        assert a['states'] <= scan['node_budget'] and b['states'] <= incremental['node_budget']
    cpp = [source.with_name(name) for name in ('round23_b251_single_scan.cpp', 'round23_b251_incremental.cpp')]
    output = {'n': n, 'all_quad_count': 2491, 'orbit_count': 389, 'winner_flips': 0,
              'unknown_orbits': 0, 'independent_outcomes_agree': True,
              'scan_state_sum': sum(case['states'] for case in scan['cases']),
              'incremental_state_sum': sum(case['states'] for case in incremental['cases']),
              'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'solver_sha256': {file.name: hashlib.sha256(file.read_bytes()).hexdigest() for file in cpp},
              'input_sha256': {file.name: hashlib.sha256(data).hexdigest() for file, data in zip(files, contents)}}
    (root / 'round23_b251_n6_audited.json').write_text(json.dumps(output, indent=2)+'\n', encoding='utf-8')
    print('PASS: all 2491 removals covered by 389 D4 orbits; both solvers complete and agree')


if __name__ == '__main__':
    main()
