"""Audit maximum six-stone cover incidence and a genuine ten-stone maximal set.

The universal 85 upper bound is a completed branch-and-bound computation,
not an enumeration-free analytic proof of B079. One extremal witness and
the ten-stone witness are independently checked on every empty point.
"""
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
import hashlib
import json
from round25_forced_verify import bits, det4, geometry
from round46_audit import cover

ROOT = Path(__file__).resolve().parents[1]


def hashes(files):
    return {f: hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}


def checked_cover(n, ids):
    stones = [(p % n, p // n) for p in ids]
    c = cover(n, stones)
    for row in c:
        p = tuple(row['p'])
        direct = [i for i, t in enumerate(combinations(stones, 3)) if det4([*t, p]) == 0]
        assert direct == row['blocking_triple_indices']
    return {'S_ids': ids, 'S_coordinates': stones, 'empty_point_certificates': c,
            'sum_b': sum(d['b'] for d in c), 'min_b': min(d['b'] for d in c),
            'legal_empty_points': [d['p'] for d in c if d['b'] == 0]}


def main():
    points, quads, _ = geometry(10)
    assert len(quads) == 54441
    completion = defaultdict(int)
    for q in quads:
        for p in bits(q):
            completion[q ^ (1 << p)] |= 1 << p
    assert sum(t.bit_count() for t in completion.values()) == 217764
    maximum = max(t.bit_count() for t in completion.values())
    assert maximum == 9
    assert all((k*(k-1)*(k-2)//6 if k >= 3 else 0)*maximum < 100-k for k in range(6))
    old = json.loads((ROOT/'round48_n10_k6.json').read_text())
    assert old['complete'] and not old['found'] and old['forbidden_quads'] == len(quads)
    optimized = json.loads((ROOT/'round48_n10_k6_max_incidence.json').read_text())
    assert optimized['complete'] and optimized['maximization'] and optimized['maximum_total_completion'] == 85
    assert not any(optimized['coverage_prunes'])
    extreme = checked_cover(10, optimized['witness'])
    assert len(extreme['S_ids']) == 6 and extreme['sum_b'] == 85
    # Each triple completion stays outside S by safety, so sum c(T)=sum_p b(p).
    score = sum(completion[sum(1 << p for p in t)].bit_count() for t in combinations(extreme['S_ids'], 3))
    assert score == 85
    pp, qq, _ = geometry(4)
    qset = set(qq)
    four_completion = defaultdict(int)
    for q in qq:
        for p in bits(q):
            four_completion[q ^ (1 << p)] |= 1 << p
    best = -1
    safe6 = 0
    for ids in combinations(range(16), 6):
        s = sum(1 << p for p in ids)
        if any(sum(1 << p for p in t) in qset for t in combinations(ids, 4)):
            continue
        safe6 += 1
        best = max(best, sum(four_completion[sum(1 << p for p in t)].bit_count() for t in combinations(ids, 3)))
    check = json.loads((ROOT/'round48_n4_k6_max_incidence_check.json').read_text())
    assert check['complete'] and check['maximum_total_completion'] == best == 22 and safe6 == 1064
    common = ['scripts/round48_49_audit.py', 'scripts/round25_forced_verify.py', 'scripts/round46_audit.py',
              'scripts/round46_kmin_tight.cpp']
    out48 = {'B079_original_verdict': 'PARTIAL', 'n': 10, 'k': 6,
             'exact_maximum_sum_b': 85, 'maximality_required_sum_b': 94,
             'extremal_witness': extreme, 'independent_n4_optimizer_check': {'safe_six_sets': safe6, 'maximum': best},
             'proof_limit': 'The 85 upper bound relies on a completed geometric branch-and-bound optimization. An enumeration-free short system of cooccurrence inequalities remains unproved.',
             'sha256': hashes(common + ['scripts/round48_max_incidence.cpp', 'round48_n10_k6.json',
                                       'round48_n10_k6_max_incidence.json', 'round48_n4_k6_max_incidence_check.json'])}
    (ROOT/'round48_incidence_verified.json').write_text(json.dumps(out48, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    embedded = json.loads((ROOT/'round48_n10_embedded_extensions.json').read_text())
    assert embedded['n'] == 10 and embedded['stone_count_limit'] == 10
    witness = checked_cover(10, embedded['witness_ids'])
    assert len(witness['S_ids']) == 10 and not witness['legal_empty_points']
    source_ids = embedded['source_ids']
    dx, dy = embedded['translation']
    translated = [10*(p//8+dy)+p % 8+dx for p in source_ids]
    assert embedded['source_mask'] == sum(1 << p for p in source_ids)
    assert len(source_ids) == 8 and set(translated) <= set(witness['S_ids'])
    remaining = sorted(set(witness['S_ids'])-set(translated))
    assert remaining == [29, 48]
    nine = json.loads((ROOT/'round49_n10_embedded_nine.json').read_text())
    assert nine['family_complete'] and not nine['witness_ids']
    assert nine['embeddings_checked'] == 408*9 and nine['one_extensions_checked'] == 63672
    lower = 7
    upper = 10
    b093 = 'PARTIAL'
    smaller_witness = None
    extra = []
    k7file = ROOT/'round49_n10_k7.json'
    k7 = None
    if k7file.exists() and k7file.stat().st_size:
        k7 = json.loads(k7file.read_text())
        assert k7['n'] == 10 and k7['k'] == 7 and k7['forbidden_quads'] == len(quads)
        extra.append(k7file.name)
        if k7['complete'] and not k7['found']:
            lower = 8
        if k7['found']:
            smaller_witness = checked_cover(10, k7['witness'])
            assert len(smaller_witness['S_ids']) == 7 and not smaller_witness['legal_empty_points']
            upper = 7
            b093 = 'REFUTED'
    window_file = ROOT/'round51_n10_k7_window.json'
    window = None
    if window_file.exists() and window_file.stat().st_size:
        window = json.loads(window_file.read_text())
        s9 = json.loads((ROOT/'round46_saturation_verified.json').read_text())
        assert s9['B092_original_verdict'] == 'SUPPORTED' and s9['s9_bounds'] == [9, 9]
        assert window['n'] == 10 and window['k'] == 7 and window['forbidden_quads'] == len(quads)
        assert window['complete'] and not window['found'] and window['nodes_by_depth'][1] == 5
        lower = 8
        extra.extend([window_file.name, 'scripts/round51_n10_window.cpp', 'round46_saturation_verified.json'])
    assert lower <= upper
    out49 = {'B094_original_verdict': 'REFUTED', 'B093_original_verdict': b093,
             's10_bounds': [lower, upper], 'minimum_stone_lower_sizes_closed': list(range(lower)),
             'six_stone_exclusion': 'completed maximum sum_b=85<94',
             'ten_stone_maximal_witness': witness, 'source_eight_stone_mask': embedded['source_mask'],
             'source_translation': embedded['translation'], 'added_point_ids': remaining,
             'nine_stone_search_limit': 'Only all 3672 translated n8 eight-stone catalogue sets plus one point. This is not a universal n10 nine-stone exclusion.',
             'seven_stone_search': k7,
             'seven_stone_complete_window_search': window, 'smaller_witness': smaller_witness,
             'sha256': hashes(common + ['scripts/round48_n10_embedded.cpp', 'round4_b371.bin',
                                       'round48_n10_embedded_extensions.json', 'round49_n10_embedded_nine.json',
                                       'round48_incidence_verified.json'] + extra)}
    (ROOT/'round49_s10_verified.json').write_text(json.dumps(out49, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('PASS exact max six-stone sum_b=85; genuine ten-stone maximal; B094 REFUTED; s10', out49['s10_bounds'])


if __name__ == '__main__':
    main()
