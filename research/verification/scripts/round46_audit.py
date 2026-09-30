"""Certificates for s8, the s9 bracket, and the exhaustive window reduction.

The 408-set catalogue's completeness comes from round4_b371.cpp / round10.
This audit independently checks every set and every translated embedding.
Timed-out searches and SAT UNKNOWN results are never absence certificates.
"""
from collections import Counter, defaultdict
from itertools import combinations, product
from pathlib import Path
import hashlib
import json
import struct
from round25_forced_verify import bits, curve, det4, geometry

ROOT = Path(__file__).resolve().parents[1]


def cover(n, stones):
    assert all(det4(q) != 0 for q in combinations(stones, 4))
    curves = [curve(t) for t in combinations(stones, 3)]
    assert len(set(curves)) == len(curves)
    occupied = set(stones)
    records = []
    for y in range(n):
        for x in range(n):
            if (x, y) in occupied:
                continue
            indices = [i for i, (a, b, c, d) in enumerate(curves)
                       if a*(x*x+y*y)+b*x+c*y+d == 0]
            records.append({'p': [x, y], 'b': len(indices), 'blocking_triple_indices': indices})
    return records


def main():
    dependencies = ['scripts/round46_audit.py', 'scripts/round25_forced_verify.py',
                    'scripts/round46_kmin_tight.cpp', 'scripts/round46_kmin_symmetry.cpp',
                    '../../scripts/analysis/fact_kmin_cover_bound.cpp', 'scripts/round4_b371.cpp',
                    'round4_b371.bin', 'round4_b371.json', 'round10-small-saturation.md',
                    'round10_small_saturation.json', 'round46_n8_to_n9_embeddings_probe.json']
    lower = {}
    for n in [8, 9]:
        points, quads, _ = geometry(n)
        completion = defaultdict(int)
        for q in quads:
            for p in bits(q):
                completion[q ^ (1 << p)] |= 1 << p
        maximum = max(v.bit_count() for v in completion.values())
        assert maximum == 9
        assert all((k*(k-1)*(k-2)//6 if k >= 3 else 0)*maximum < n*n-k for k in range(5))
        runs = []
        for k in [5, 6, 7]:
            name = f'round46_n{n}_k{k}' + ('_tight_check' if n == 8 and k == 7 else '') + '.json'
            d = json.loads((ROOT/name).read_text())
            assert d['n'] == n and d['k'] == k and d['complete'] and not d['found']
            assert d['forbidden_quads'] == len(quads)
            assert d['max_completion'] == maximum
            assert d['triple_completion_incidence'] == 4*len(quads)
            dependencies.append(name)
            runs.append({'k': k, 'file': name, 'nodes': d['nodes'], 'seconds': d['seconds']})
        lower[str(n)] = {'quad_count': len(quads), 'maximum_triple_completion': maximum,
                         'k_0_to_4_excluded_by_incidence_bound': True, 'complete_searches': runs}
    raw = (ROOT/'round4_b371.bin').read_bytes()
    words = struct.unpack('<'+'Q'*(len(raw)//8), raw)
    assert words[0] == len(words)-1 == len(set(words[1:])) == 408
    probe = json.loads((ROOT/'round46_n8_to_n9_embeddings_probe.json').read_text())['all_1632_embeddings']
    assert len(probe) == 1632
    probe_by_key = {(d['source_S_mask'], tuple(d['embedding'])): d for d in probe}
    assert len(probe_by_key) == 1632
    records = []
    histogram = Counter()
    min_b8 = Counter()
    for mask in words[1:]:
        stones = [(p % 8, p // 8) for p in bits(mask)]
        assert len(stones) == 8
        covered = cover(8, stones)
        assert len(covered) == 56 and all(d['b'] for d in covered)
        min_b8[min(d['b'] for d in covered)] += 1
        for dx, dy in product(range(2), repeat=2):
            translated = [(x+dx, y+dy) for x, y in stones]
            outside = [d['p'] for d in cover(9, translated) if d['b'] == 0]
            assert outside == probe_by_key[(mask, (dx, dy))]['outside_legal_points']
            assert len(outside) >= 2
            assert all(not (dx <= x < dx+8 and dy <= y < dy+8) for x, y in outside)
            # Independent integer determinant for one saved legal point per embedding.
            p = tuple(outside[0])
            assert all(det4([*t, p]) != 0 for t in combinations(translated, 3))
            histogram[len(outside)] += 1
            records.append({'source_mask': mask, 'translation': [dx, dy],
                            'legal_outside_point': list(p), 'outside_legal_count': len(outside)})
    assert min_b8 == {1: 408}
    witness8 = [(p % 8, p // 8) for p in [0, 1, 6, 20, 24, 32, 34, 60]]
    witness9 = [tuple(p) for p in json.loads((ROOT/'round10_small_saturation.json').read_text())['B379_witness']['target']]
    upper = {}
    for n, stones in [(8, witness8), (9, witness9)]:
        coverage = cover(n, stones)
        assert all(d['b'] for d in coverage)
        for d in coverage:
            p = tuple(d['p'])
            direct = [i for i, t in enumerate(combinations(stones, 3)) if det4([*t, p]) == 0]
            assert direct == d['blocking_triple_indices']
        upper[str(n)] = {'S_coordinates': stones, 'empty_point_certificates': coverage}
    unknown = []
    for name in ['round46_n9_k8.json', 'round46_n9_k8_tight.json',
                 'round46_sat_atmost8.json', 'round46_cadical_atmost8.json']:
        d = json.loads((ROOT/name).read_text())
        assert d.get('status', 'UNKNOWN') == 'UNKNOWN' and not d.get('complete', False)
        unknown.append(name)
        dependencies.append(name)
    reduced_file = ROOT/'round46_n9_k8_symmetry.json'
    reduced = None
    if reduced_file.exists() and reduced_file.stat().st_size:
        reduced = json.loads(reduced_file.read_text())
        assert reduced['n'] == 9 and reduced['k'] == 8
        assert reduced['forbidden_quads'] == lower['9']['quad_count']
        dependencies.append(reduced_file.name)
    verdict = 'SUPPORTED' if reduced and reduced['complete'] and not reduced['found'] else 'PARTIAL'
    if reduced and reduced['found']:
        candidate = [(p % 9, p // 9) for p in reduced['witness']]
        c = cover(9, candidate)
        assert len(candidate) == 8 and all(d['b'] for d in c)
        upper['9_eight_stone'] = {'S_coordinates': candidate, 'empty_point_certificates': c}
        verdict = 'REFUTED'
    output = {'B091_original_verdict': 'SUPPORTED', 's8': 8,
              'B092_original_verdict': verdict, 's9_bounds': [9, 9] if verdict == 'SUPPORTED' else [8, 8] if verdict == 'REFUTED' else [8, 9],
              'lower_bounds': lower, 'upper_bound_witnesses': upper,
              'catalogue_completeness_dependency': 'round4_b371.cpp full all-pair seeded enumeration, round10 audit',
              'catalogue_408_min_b_histogram': dict(sorted(min_b8.items())),
              'embedding_1632_legal_count_histogram': dict(sorted(histogram.items())),
              'embedding_certificates': records,
              'orbit_reduction': 'No maximal eight-stone set fits an 8x8 window; some axis spans 0..8. Rotate that axis vertically, reflect horizontally so minimum occupied row-0 x<=4. Some D4 representative has first sorted ID<=4.',
              'bounded_unknown_results_not_used_as_absence': unknown,
              'reduced_search': reduced,
              'sha256': {f: hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in dependencies}}
    (ROOT/'round46_saturation_verified.json').write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('PASS s8=8; s9', output['s9_bounds'], '; all 1632 embeddings checked; B092', verdict)


if __name__ == '__main__':
    main()
