"""Independent cover census, nonvacuous global minimum witnesses, small-board scope.

Fresh four-point geometry enumerates all five-stone subsets on n=4..7.
The larger k=6,7 layers use the saved complete layer census with explicit
dependencies. Each reported maximal configuration is checked directly.
"""
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
import hashlib
import json
from round25_forced_verify import bits, det4, geometry
from round46_audit import cover

ROOT = Path(__file__).resolve().parents[1]


def main():
    dependencies = ['scripts/round47_cover_audit.py', 'scripts/round47_minimal_cover_census.cpp',
                    'scripts/round25_forced_verify.py', 'scripts/round46_audit.py',
                    'round46_saturation_verified.json', 'round45-cover-gap-and-sharp-overlap.md',
                    'round28_n4_layers.json', 'round39_n5_enum.json', 'round39_n6_enum.json',
                    'round28_n7_enum.json', 'round28_n7_layers.json', 'round47_layer_hashes.json']
    small = []
    n4_maximals = []
    for n in range(1, 5):
        points, quads, _ = geometry(n)
        full = (1 << (n*n))-1
        safe_count = 0
        maximal_records = []
        for s in range(1 << (n*n)):
            if any(s&q == q for q in quads):
                continue
            safe_count += 1
            if any(all((s | (1 << p))&q != q for q in quads) for p in bits(full ^ s)):
                continue
            c = cover(n, [points[p] for p in bits(s)])
            assert all(d['b'] for d in c)
            maximal_records.append({'S_mask': s, 'k': s.bit_count(),
                                    'min_b': min((d['b'] for d in c), default=None),
                                    'max_b': max((d['b'] for d in c), default=None)})
        sk = min(d['k'] for d in maximal_records)
        minsets = [d for d in maximal_records if d['k'] == sk]
        all_double = [d for d in maximal_records if d['min_b'] is not None and d['min_b'] >= 2]
        all_single = [d for d in maximal_records if d['max_b'] == 1]
        small.append({'n': n, 'safe_subsets': safe_count, 'maximal_count': len(maximal_records),
                      's_n': sk, 'minimum_size_maximal_count': len(minsets),
                      'minimum_size_min_b_histogram': dict(Counter(d['min_b'] for d in minsets)),
                      'all_double_count_nonempty_complement': len(all_double),
                      'all_single_count_nonempty_complement': len(all_single)})
        assert n == 4 or not all_double
        if n == 4:
            assert safe_count == 5811 and len(maximal_records) == 928
            assert len(all_double) == 104 and len(all_single) == 8 and sk == 5
            n4_maximals = maximal_records
    census = []
    layer_hashes = json.loads((ROOT/'round47_layer_hashes.json').read_text())['layers']
    for n, k in [(4, 5), (5, 5), (6, 6), (7, 7)]:
        name = f'round47_n{n}_min_cover.json'
        dependencies.append(name)
        d = json.loads((ROOT/name).read_text())
        assert d['input_processed_completely'] and d['layer_k'] == k
        assert d['terminal_count'] == len(d['maximal_sets'])
        h = next(h for h in layer_hashes if h['n'] == n and h['k'] == k)
        assert h['count'] == d['safe_layer_states_checked']
        fullname = {4: 'round28_n4_layers.json', 5: 'round39_n5_enum.json',
                    6: 'round39_n6_enum.json', 7: 'round28_n7_enum.json'}[n]
        full = json.loads((ROOT/fullname).read_text())
        expected = next(t['states'] for t in full['levels'] if t['k'] == k) if n == 4 else full['level_sizes'][k]
        assert expected == h['count']
        for row in d['maximal_sets']:
            ids = list(bits(row['S_mask']))
            assert len(ids) == k
            c = cover(n, [(p % n, p // n) for p in ids])
            assert row['min_b'] == min(t['b'] for t in c) == 1
            assert row['max_b'] == max(t['b'] for t in c)
        census.append({'n': n, 's_n': k, 'safe_layer_count': d['safe_layer_states_checked'],
                       'minimum_size_maximal_count': d['terminal_count'], 'all_min_b_equal_one': True})
    five_checks = []
    maximum_completion = {}
    for n in range(4, 8):
        points, quads, _ = geometry(n)
        qset = set(quads)
        completion = defaultdict(int)
        for q in quads:
            for p in bits(q):
                completion[q ^ (1 << p)] |= 1 << p
        maximum_completion[str(n)] = max(t.bit_count() for t in completion.values())
        full = (1 << (n*n))-1
        safe_count = 0
        terminals = []
        for ids in combinations(range(n*n), 5):
            s = sum(1 << p for p in ids)
            if any(s ^ (1 << p) in qset for p in ids):
                continue
            safe_count += 1
            blocked = 0
            for triple in combinations(ids, 3):
                blocked |= completion.get(sum(1 << p for p in triple), 0)
            assert not blocked&s
            if (s | blocked) == full:
                terminals.append(s)
        name = f'round47_n{n}_' + ('min_cover.json' if n <= 5 else 'k5_exclusion.json')
        dependencies.append(name)
        d = json.loads((ROOT/name).read_text())
        assert safe_count == d['safe_layer_states_checked']
        assert sorted(terminals) == sorted(t['S_mask'] for t in d['maximal_sets'])
        five_checks.append({'n': n, 'all_labeled_five_subsets_enumerated': True,
                            'safe_count': safe_count, 'maximal_count': len(terminals)})
    # Uniform incidence inequalities used in the proof, not extrapolated fits.
    assert maximum_completion['5'] == maximum_completion['6'] == 5
    assert all(2*(n*n-5) > 10*(2*n-3) for n in range(9, 1000))
    assert all(n*n-4 > 4*(2*n-3) for n in range(7, 1000))
    witnesses = {}
    for bid, ids, expected in [('B077', [0, 1, 2, 4, 10, 15], 2), ('B080', [0, 2, 7, 10, 12], 1)]:
        stones = [(p % 4, p // 4) for p in ids]
        c = cover(4, stones)
        assert min(d['b'] for d in c) == expected
        assert bid != 'B080' or max(d['b'] for d in c) == 1
        for row in c:
            p = tuple(row['p'])
            direct = [i for i, t in enumerate(combinations(stones, 3)) if det4([*t, p]) == 0]
            assert direct == row['blocking_triple_indices']
        witnesses[bid] = {'n': 4, 'S_ids': ids, 'S_coordinates': stones, 'all_empty_point_certificates': c}
    output = {'B077_original_verdict': 'SUPPORTED', 'B080_original_verdict': 'SUPPORTED',
              'B077_minimum_stone_count_nonempty_complement': 6, 'B077_minimum_board_nonempty_complement': 4,
              'B080_minimum_stone_count_for_original_n_at_least_4': 5, 'B080_minimum_board': 4,
              'B078_original_verdict': 'SCOPE_UNCLEAR', 'B361_original_verdict': 'SCOPE_UNCLEAR',
              'scope_reason': 'No original n>=2 restriction. For n=1, the unique minimal maximal set is the whole board, there is no empty point, and rho is undefined (or infinite). The nonempty-complement readings are verified for n=2..8 only and remain open for larger n.',
              'finite_nonempty_complement_support_range': [2, 8],
              'full_small_board_census': small, 'minimum_size_census_n4_to_n7': census,
              'independent_five_stone_exhaustions': five_checks,
              'triple_completion_maxima': maximum_completion, 'witnesses': witnesses,
              'n4_all_maximal_records': n4_maximals,
              'sha256': {f: hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in dict.fromkeys(dependencies)}}
    (ROOT/'round47_cover_verified.json').write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('PASS B077 minimum 6 stones; B080 minimum 5; all n2..8 minimal maximal sets have private points')


if __name__ == '__main__':
    main()
