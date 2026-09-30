"""Audit all n7 single removals and the complete baseline P/N proof table."""
from itertools import combinations
from pathlib import Path
import argparse
import hashlib
import json
from round23_b251_audit import det4

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('baseline_directory', type=Path)
    args = parser.parse_args()
    geo, first, second, proof, old = [json.loads((ROOT / name).read_bytes()) for name in (
        'round32_b251_n7_geometry.json', 'round32_b251_n7_scan.json',
        'round32_b251_n7_curves.json', 'round32_standard_pn_verified.json',
        'round28_n7_layers.json')]
    n = 7
    rows = [(x*x+y*y, x, y, 1) for y in range(n) for x in range(n)]
    quads = [sum(1 << p for p in ids) for ids in combinations(range(n*n), 4)
             if det4([rows[p] for p in ids]) == 0]
    assert quads == geo['quad_masks'] and len(quads) == 6364
    curves = geo['curve_masks']
    assert len(curves) == len(set(curves)) == 1625
    covered = {}
    for c in curves:
        ids = [i for i in range(49) if c >> i & 1]
        assert len(ids) >= 4
        for points in combinations(ids, 4):
            q = sum(1 << i for i in points)
            assert det4([rows[i] for i in points]) == 0
            assert q not in covered
            covered[q] = c
    assert set(covered) == set(quads)
    index = {q: i for i, q in enumerate(quads)}
    orbits = {}
    for qi, q in enumerate(quads):
        images = set()
        for reflect in (False, True):
            for rotations in range(4):
                image = 0
                for p in range(49):
                    if not q >> p & 1:
                        continue
                    x, y = p % n, p // n
                    if reflect:
                        x = n-1-x
                    for _ in range(rotations):
                        x, y = n-1-y, x
                    image |= 1 << (x+n*y)
                images.add(index[image])
        orbits.setdefault(min(images), set()).add(qi)
    assert orbits == {r['rep']: set(r['members']) for r in geo['orbits']}
    assert len(orbits) == 935
    assert sorted(i for members in orbits.values() for i in members) == list(range(6364))
    reps = [r['rep'] for r in geo['orbits']]
    for result in (first, second):
        assert result['checked'] == result['representatives_total'] == 935
        assert result['all_representatives_processed']
        assert result['standard_outcome'] == result['unknown'] == result['flips'] == 0
        assert [r['removed_index'] for r in result['cases']] == reps
        for r in result['cases']:
            assert r['removed_mask'] == quads[r['removed_index']]
            assert r['outcome'] == 0 and r['states'] <= result['node_budget']
    assert proof['all_local_proof_obligations_pass']
    assert proof['checked_states'] == old['total_states'] == 179810350
    assert proof['vertices'] == 49 and proof['curves'] == 1625
    baseline = []
    for a, b in zip(proof['levels'], old['levels'], strict=True):
        assert a['k'] == b['k'] and a['checked'] == b['states']
        assert a['P'] == b['histogram'].get('0', 0)
        occ = args.baseline_directory / f"level_{a['k']}.occ"
        pn = args.baseline_directory / f"standard_{a['k']}.pn"
        data = pn.read_bytes()
        assert len(data) == a['checked'] and len(data)*8 == occ.stat().st_size
        assert set(data) <= {0, 1} and data.count(0) == a['P']
        baseline.append({'k': a['k'], 'states': a['checked'], 'P': a['P'],
                         'occ_sha256': digest(occ), 'pn_sha256': digest(pn)})
    sources = ['round32_b251_audit.py', 'round32_b251_input.py',
               'round32_b251_accelerated.cpp', 'round32_b251_curves.cpp',
               'round32_standard_table.h', 'round32_standard_pn.cpp',
               'round32_standard_pn_verify.cpp', 'round25_forced_verify.py',
               'round23_b251_audit.py', 'kc_core.h', 'round5_prand_stream.cpp']
    evidence = ['round32_b251_n7_geometry.json', 'round32_b251_n7_input.txt',
                'round32_b251_n7_scan.json', 'round32_b251_n7_curves.json',
                'round32_standard_pn_verified.json', 'round28_n7_layers.json']
    out = {'n': 7, 'all_quad_count': 6364, 'orbit_count': 935,
           'unknown_orbits': 0, 'winner_flips': 0, 'outcomes_agree': True,
           'completion_solver_state_sum': sum(r['states'] for r in first['cases']),
           'curve_solver_state_sum': sum(r['states'] for r in second['cases']),
           'baseline_local_proof_checked_states': 179810350,
           'baseline_layers': baseline,
           'source_sha256': {name: digest(Path(__file__).with_name(name)) for name in sources},
           'evidence_sha256': {name: digest(ROOT/name) for name in evidence}}
    (ROOT/'round32_b251_n7_audited.json').write_text(json.dumps(out, indent=2)+'\n', encoding='utf-8')
    print('PASS: all 6364 removals covered; both 935-orbit sweeps exact; baseline proof complete')


if __name__ == '__main__':
    main()
