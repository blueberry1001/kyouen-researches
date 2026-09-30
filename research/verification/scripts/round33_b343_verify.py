"""Independent original B343 certificate, including the stronger sole-triple premise."""
from collections import Counter
from functools import cache
from itertools import combinations
from pathlib import Path
import hashlib
import json
from round25_forced_verify import geometry, bits, det4

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = json.loads((ROOT/'round33_b343_n6_sole.json').read_bytes())
    n = source['n']
    points, quads, curves = geometry(n)
    s = source['S_mask']
    assert all(s&q != q for q in quads)
    assert all((s&c).bit_count() <= 3 for c in curves)
    full = (1 << (n*n))-1
    L = full ^ s
    for c in curves:
        if (s&c).bit_count() == 3:
            L &= ~c
    ids = list(bits(L))
    assert ids == source['L_ids'] and len(ids) == 8
    raw = {q&~s for q in quads if not (q&~s)&~L}
    edges = sorted(e for e in raw if not any(f != e and f&e == f for f in raw))
    compress = lambda mask: sum(1 << i for i, p in enumerate(ids) if mask >> p & 1)
    assert sorted(map(compress, edges)) == sorted(source['minimal_edges'])
    triples = [e for e in edges if e.bit_count() == 3]
    assert len(triples) == 1 and all(e.bit_count() in (2, 3) for e in edges)
    removed = triples[0]
    assert compress(removed) == source['removed_compressed_mask']
    kept = [e for e in edges if e != removed]
    reached = {ids[0]}
    while True:
        previous = set(reached)
        for e in kept:
            vertices = set(bits(e))
            if reached & vertices:
                reached |= vertices
        if reached == previous:
            break
    assert reached == set(ids)  # Every retained edge is a pair; graph connected.
    certificates = []
    for m in range(1 << len(ids)):
        extension = sum(1 << p for i, p in enumerate(ids) if m >> i & 1)
        original_safe = not any(extension&e == e for e in edges)
        assert original_safe == all((s|extension)&q != q for q in quads)
        assert original_safe == all(((s|extension)&c).bit_count() <= 3 for c in curves)
        direct = all(det4([points[p] for p in four]) != 0 for four in combinations(bits(s|extension), 4))
        assert direct == original_safe
        relaxed_safe = not any(extension&e == e for e in kept)
        certificates.append({'extension_mask': extension, 'original_safe': original_safe,
                             'one_triple_removed_safe': relaxed_safe})

    def solver(family):
        @cache
        def value(t):
            seen = set()
            for p in reversed(ids):
                if t >> p & 1:
                    continue
                c = t | (1 << p)
                if not any(c&e == e for e in family):
                    seen.add(value(c))
            g = 0
            while g in seen:
                g += 1
            return g
        value(0)
        return value, {p: value(1 << p) for p in ids}

    original, a = solver(edges)
    relaxed, b = solver(kept)
    wa = [p for p in ids if a[p] == 0]
    wb = [p for p in ids if b[p] == 0]
    assert original(0) == source['g_full'] == 1
    assert relaxed(0) == source['g_minus'] == 3
    assert wa and wb and set(wa).isdisjoint(wb)
    assert compress(sum(1 << p for p in wa)) == source['win_full_compressed']
    assert compress(sum(1 << p for p in wb)) == source['win_minus_compressed']
    # Store full DAG values and child lists, checked by local mex obligations.
    dags = []
    for family, value in ((edges, original), (kept, relaxed)):
        records = []
        for c in certificates:
            t = c['extension_mask']
            if any(t&e == e for e in family):
                continue
            children = [t|(1 << p) for p in ids if not t >> p & 1
                        and not any((t|(1 << p))&e == e for e in family)]
            seen = {value(u) for u in children}
            g = value(t)
            assert g not in seen and all(j in seen for j in range(g))
            records.append({'extension_mask': t, 'g': g, 'child_masks': children})
        dags.append(records)
    q_witnesses = {str(e): list(bits(next(q for q in quads if q&~s == e))) for e in edges}
    files = ['scripts/round33_b343_verify.py', 'scripts/round33_b343_search.cpp',
             'scripts/round25_forced_verify.py', 'scripts/kc_core.h', 'round33_b343_n6_sole.json']
    result = {'original_verdict': 'SUPPORTED', 'n': n, 'S_mask': s, 'S_ids': list(bits(s)),
              'S_coordinates': [points[p] for p in bits(s)], 'L_ids': ids,
              'L_coordinates': [points[p] for p in ids],
              'minimal_residual_edges': [list(bits(e)) for e in edges],
              'quad_witnesses': q_witnesses, 'residual_size_histogram': dict(Counter(e.bit_count() for e in edges)),
              'removed_triple_ids': list(bits(removed)),
              'g_full': 1, 'g_minus': 3, 'winning_full_ids': wa, 'winning_minus_ids': wb,
              'child_g_full': a, 'child_g_minus': b, 'all_256_extensions': certificates,
              'full_game_dag': dags[0], 'one_triple_removed_dag': dags[1],
              'sha256': {f: hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}}
    (ROOT/'round33_b343_verified.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('PASS B343: exactly one minimal triple; all 256 extensions; g 1->3; disjoint winning moves', wa, wb)


if __name__ == '__main__':
    main()
