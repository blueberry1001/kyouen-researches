"""Independent exact verifier of the B255 5x5 witness.

Uses a translated 3x3 determinant and direct four-set containment. It does not
import the search code, its completion tables, or the shared geometry module.
"""
from collections import Counter
from itertools import combinations
from pathlib import Path
import hashlib
import json
import time


def forbidden(points):
    x0, y0 = points[0]
    rows = [(x-x0, y-y0, (x-x0)**2 + (y-y0)**2) for x, y in points[1:]]
    a, b, c = rows
    return (a[0]*(b[1]*c[2]-b[2]*c[1])
            - a[1]*(b[0]*c[2]-b[2]*c[0])
            + a[2]*(b[0]*c[1]-b[1]*c[0])) == 0


def members(mask):
    while mask:
        bit = mask & -mask
        yield bit.bit_length()-1
        mask ^= bit


def solve(v, quads):
    full = (1 << v)-1
    legal_masks = {}

    def visit(s, tail):
        legal = full ^ s
        for q in quads:
            missing = q & ~s
            assert missing, ('unsafe enumeration state', s, q)
            if not missing & (missing-1):
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
        g = 0
        while g in values:
            g += 1
        grundy[s] = g
    layers = Counter(s.bit_count() for s in legal_masks)
    k = max(layers)
    maxima = sorted(s for s in legal_masks if s.bit_count() == k)
    return {"g0": grundy[0], "winning_first_moves": [p for p in range(v) if grundy[1 << p] == 0],
            "safe_states": len(legal_masks), "layer_counts": dict(sorted(layers.items())),
            "maximum_size": k, "maximum_sets": maxima}


def main():
    started = time.perf_counter()
    source = Path(__file__).resolve()
    directory = source.parents[1]
    search_file = directory / 'round20_b255_n5.json'
    search = json.loads(search_file.read_text(encoding='utf-8'))
    n = search['n']
    assert n == 5
    points = [(x, y) for y in range(n) for x in range(n)]
    quads = [sum(1 << p for p in ids) for ids in combinations(range(n*n), 4)
             if forbidden([points[p] for p in ids])]
    assert quads == search['quad_masks'] and len(quads) == 826
    for qi, s in search['unique_quad_maximum_layer_witnesses'].items():
        assert s.bit_count() == 9
        assert [i for i, q in enumerate(quads) if s & q == q] == [int(qi)]
    removed = set(search['variant_search']['removed_indices'])
    assert removed <= set(search['no_unique_quad_extension'])
    removed_mask = sum(1 << i for i in removed)
    assert not any(int(sig) & removed_mask == int(sig)
                   for sig in search['minimal_maximum_preservation_conflicts'])
    standard = solve(n*n, quads)
    print('standard:', standard['g0'], standard['safe_states'], len(standard['maximum_sets']), flush=True)
    changed = solve(n*n, [q for i, q in enumerate(quads) if i not in removed])
    print('changed:', changed['g0'], changed['safe_states'], len(changed['maximum_sets']), flush=True)
    assert standard['maximum_size'] == changed['maximum_size'] == 9
    assert standard['maximum_sets'] == changed['maximum_sets']
    assert len(standard['maximum_sets']) == 100
    assert standard['g0'] == 1 and changed['g0'] == 0
    out = {
        "claim": "B255 SUPPORTED on the full 5x5 board: same K=9 and all 100 maxima; g0 1 to 0",
        "n": n, "point_order": points,
        "removed_quad_indices": sorted(removed),
        "removed_quad_masks": [quads[i] for i in sorted(removed)],
        "removed_quad_coordinates": [[points[p] for p in members(quads[i])] for i in sorted(removed)],
        "standard": standard, "changed": changed,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "search_data_sha256": hashlib.sha256(search_file.read_bytes()).hexdigest(),
        "seconds": time.perf_counter()-started,
    }
    target = directory / 'round20_b255_verified.json'
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('PASS: all maximum sets identical, exact Grundy winner reversed', flush=True)


if __name__ == '__main__':
    main()
