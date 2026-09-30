"""Original B098 has no n>=4 restriction; exact n2->n3 is a witness.

The monotonicity check of B097 is finite through n9 only. Larger n remain
open, including whether s10 falls below the now proved s9=9.
"""
from collections import Counter
from pathlib import Path
import hashlib
import json
from round25_forced_verify import bits, geometry

ROOT = Path(__file__).resolve().parents[1]


def main():
    small = []
    for n in [1, 2, 3]:
        points, quads, _ = geometry(n)
        full = (1 << (n*n))-1
        layer = Counter()
        terminals = Counter()
        minimum_sets = []
        for s in range(1 << (n*n)):
            if any(s&q == q for q in quads):
                continue
            layer[s.bit_count()] += 1
            legal = [p for p in bits(full ^ s) if all((s | (1 << p))&q != q for q in quads)]
            if not legal:
                terminals[s.bit_count()] += 1
                minimum_sets.append(list(bits(s)))
        sn = min(terminals)
        assert sn == {1: 1, 2: 3, 3: 5}[n]
        small.append({'n': n, 'all_subsets_checked': 1 << (n*n), 'quad_count': len(quads),
                      'safe_layer_counts': dict(sorted(layer.items())), 'terminal_size_counts': dict(sorted(terminals.items())),
                      's_n': sn, 'minimum_maximal_ids': [ids for ids in minimum_sets if len(ids) == sn]})
    minimum = json.loads((ROOT/'round47_cover_verified.json').read_text())['minimum_size_census_n4_to_n7']
    previous = json.loads((ROOT/'round46_saturation_verified.json').read_text())
    assert previous['s8'] == 8 and previous['s9_bounds'] == [9, 9]
    sequence = [d['s_n'] for d in small]+[d['s_n'] for d in minimum]+[8, 9]
    assert sequence == [1, 3, 5, 5, 5, 6, 7, 8, 9]
    assert all(a <= b for a, b in zip(sequence, sequence[1:]))
    files = ['scripts/round54_saturation_jump.py', 'scripts/round25_forced_verify.py',
             'round47_cover_verified.json', 'round46_saturation_verified.json',
             'round47-private-cover-and-global-minima.md', 'round28_n7_layers.json']
    output = {'B098_original_verdict': 'SUPPORTED', 'B097_original_verdict': 'PARTIAL',
              'jump_witness': {'n': 2, 's_n': 3, 's_next': 5, 'difference': 2},
              'another_literal_jump': {'n': 1, 's_n': 1, 's_next': 3, 'difference': 2},
              'B098_n_at_least_4_additional_variant': 'not decided',
              'B097_finite_complete_range': [1, 9], 'minimum_maximal_sequence': sequence,
              'small_board_complete_censuses': small,
              'sha256': {f: hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}}
    (ROOT/'round54_saturation_jump_verified.json').write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('PASS exact jump s3-s2=2; B098 original satisfied; monotonicity verified only n1..9')


if __name__ == '__main__':
    main()
