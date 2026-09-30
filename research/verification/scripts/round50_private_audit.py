"""Independent census of the translated eight-board catalogue plus one point.

Completeness is only for this specified extension family, not all n9
nine-stone maximal sets. Check every member and the deletion intersection.
"""
from collections import Counter, defaultdict
from functools import reduce
from itertools import combinations, product
from operator import and_
from pathlib import Path
import hashlib
import json
import struct
from round25_forced_verify import bits, det4, geometry
from round46_audit import cover

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = (ROOT/'round4_b371.bin').read_bytes()
    words = struct.unpack('<'+'Q'*(len(source)//8), source)
    assert words[0] == len(words)-1 == 408
    result = json.loads((ROOT/'round50_n9_private_family.json').read_text())
    assert result['restricted_family_complete'] and result['embeddings'] == 1632
    points, quads, _ = geometry(9)
    completion = defaultdict(int)
    for q in quads:
        for p in bits(q):
            completion[q ^ (1 << p)] |= 1 << p
    full = (1 << 81)-1
    found = set()
    extensions = 0
    for s in words[1:]:
        old = list(bits(s))
        for dx, dy in product(range(2), repeat=2):
            ids = [9*(p//8+dy)+p % 8+dx for p in old]
            occupied = sum(1 << p for p in ids)
            blocked = 0
            for t in combinations(ids, 3):
                blocked |= completion[sum(1 << p for p in t)]
            assert not occupied&blocked
            for p in bits(full & ~(occupied | blocked)):
                extensions += 1
                next_blocked = blocked
                for a, b in combinations(ids, 2):
                    next_blocked |= completion[(1 << a) | (1 << b) | (1 << p)]
                next_occupied = occupied | (1 << p)
                if next_blocked | next_occupied == full:
                    found.add(next_occupied)
    assert extensions == result['extensions_checked'] == 12320
    assert len(found) == result['distinct_maximal_nine_stone_sets'] == 16
    reported = {sum(1 << p for p in ids) for ids in result['maximal_sets_ids']}
    assert reported == found
    private_hist = Counter()
    release_hist = Counter()
    records = []
    for s in sorted(found):
        ids = list(bits(s))
        stones = [points[p] for p in ids]
        c = cover(9, stones)
        triples = list(combinations(ids, 3))
        release_points = []
        for row in c:
            p = tuple(row['p'])
            direct = [i for i, t in enumerate(triples) if det4([*(points[q] for q in t), p]) == 0]
            assert direct == row['blocking_triple_indices'] and direct
            common = reduce(and_, (sum(1 << q for q in triples[i]) for i in direct))
            if common:
                release_points.append({'p': row['p'], 'deletable_stone_ids': list(bits(common))})
        minimum = min(row['b'] for row in c)
        assert minimum == 1 and release_points
        private_hist[minimum] += 1
        release_hist[len(release_points)] += 1
        records.append({'S_ids': ids, 'min_b': minimum, 'rho': 1,
                        'private_point_certificates': [row for row in c if row['b'] == 1],
                        'one_deletion_releasable_points': release_points})
    assert {str(k): v for k, v in private_hist.items()} == result['min_b_histogram']
    assert {str(k): v for k, v in release_hist.items()} == result['one_deletion_releasable_point_histogram']
    s9 = json.loads((ROOT/'round46_saturation_verified.json').read_text())
    assert s9['s9_bounds'] == [9, 9]
    files = ['scripts/round50_private_audit.py', 'scripts/round50_n9_private.cpp',
             'scripts/round46_kmin_tight.cpp', 'scripts/round25_forced_verify.py', 'scripts/round46_audit.py',
             'round4_b371.bin', 'round50_n9_private_family.json', 'round46_saturation_verified.json']
    out = {'family': 'all translated n8 maximal-eight catalogue members, dx/dy 0..1, plus one legal point on n9',
           'family_complete': True, 'n': 9, 's9': 9, 'embeddings': 1632, 'extensions': extensions,
           'distinct_minimum_size_maximal_sets': 16, 'all_min_b': 1, 'all_rho': 1,
           'not_a_complete_n9_minimum_maximal_catalogue': True,
           'B078_B361_general_n9_verdict': 'not decided by this restricted family',
           'records': records, 'sha256': {f: hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}}
    (ROOT/'round50_private_verified.json').write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('PASS all1632 embeddings /12320 extensions; exact family16; all minb1 rho1; no universal n9 claim')


if __name__ == '__main__':
    main()
