"""Independent complete-curve verifier for the B224 witnesses.

Regenerates geometry with integer determinants, then enumerates every safe
state using counts on entire curves. No search solver or completion table is
imported. A curve forbids four or more occupied points on that curve.
"""
from collections import Counter
from itertools import combinations
from math import gcd
from pathlib import Path
import argparse
import hashlib
import json
import time


def determinant(rows):
    a, b, c = rows
    return (a[0]*(b[1]*c[2]-b[2]*c[1])
            - a[1]*(b[0]*c[2]-b[2]*c[0])
            + a[2]*(b[0]*c[1]-b[1]*c[0]))


def curve(points):
    (x, y), (u, v), (r, t) = points
    cross = (u-x)*(t-y)-(v-y)*(r-x)
    if not cross:
        key = [0, y-v, u-x, x*v-u*y]
    else:
        rows = [(a*a+b*b, a, b, 1) for a, b in points]
        key = [(-1)**j * determinant([tuple(row[k] for k in range(4) if k != j)
                                      for row in rows]) for j in range(4)]
    common = gcd(*key)
    key = [z//common for z in key]
    if next(z for z in key if z) < 0:
        key = [-z for z in key]
    return tuple(key)


def members(mask):
    while mask:
        bit = mask & -mask
        yield bit.bit_length()-1
        mask ^= bit


def regenerate(n):
    points = [(x, y) for y in range(n) for x in range(n)]
    keys = {curve([points[p] for p in ids]) for ids in combinations(range(n*n), 3)}
    groups = []
    for key in sorted(keys):
        a, b, c, d = key
        ids = [p for p, (x, y) in enumerate(points) if a*(x*x+y*y)+b*x+c*y+d == 0]
        if len(ids) >= 4:
            groups.append({'coefficients': list(key), 'point_indices': ids,
                           'kind': 'line' if a == 0 else 'circle'})
    # Independent determinant test for each four-set, including collinear sets.
    quads = []
    for ids in combinations(range(n*n), 4):
        x, y = points[ids[0]]
        rows = [(points[p][0]-x, points[p][1]-y,
                 (points[p][0]-x)**2+(points[p][1]-y)**2) for p in ids[1:]]
        if determinant(rows) == 0:
            quads.append(sum(1 << p for p in ids))
    grouped = [sum(1 << p for p in ids) for g in groups
               for ids in combinations(g['point_indices'], 4)]
    assert len(grouped) == len(set(grouped)) and sorted(grouped) == sorted(quads)
    return points, groups, quads


def solve(v, groups):
    full = (1 << v)-1
    masks = [sum(1 << p for p in g['point_indices']) for g in groups]
    legal_masks = {}

    def visit(s, tail):
        legal = full ^ s
        for mask in masks:
            count = (s & mask).bit_count()
            assert count <= 3
            if count == 3:
                legal &= ~mask
        legal_masks[s] = legal
        candidates = legal & tail
        while candidates:
            bit = candidates & -candidates
            candidates ^= bit
            visit(s | bit, candidates)

    visit(0, full)
    grundy = {}
    for s in sorted(legal_masks, reverse=True):
        options = {grundy[s | (1 << p)] for p in members(legal_masks[s])}
        value = 0
        while value in options:
            value += 1
        grundy[s] = value
    layers = Counter(s.bit_count() for s in legal_masks)
    # Store full Grundy table as a reproducible digest, not a giant JSON object.
    digest = hashlib.sha256()
    for s in sorted(grundy):
        digest.update(s.to_bytes(4, 'little'))
        digest.update(grundy[s].to_bytes(1, 'little'))
    return {'g0': grundy[0], 'first_move_grundy': [grundy[1 << p] for p in range(v)],
            'winning_first_moves': [p for p in range(v) if grundy[1 << p] == 0],
            'safe_states': len(legal_masks), 'layer_counts': dict(sorted(layers.items())),
            'maximum_size': max(layers), 'grundy_table_sha256': digest.hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--witness', default='round20_b224_orbit_search.json')
    parser.add_argument('--output', default='round21_b224_verified.json')
    args = parser.parse_args()
    start = time.perf_counter()
    source = Path(__file__).resolve()
    root = source.parents[1]
    geometry_file = root / 'round20_b224_geometry.json'
    witness_file = root / args.witness
    geometry_bytes = geometry_file.read_bytes()
    witness_bytes = witness_file.read_bytes()
    geometry = json.loads(geometry_bytes)
    witness = json.loads(witness_bytes)
    points, groups, quads = regenerate(5)
    assert len(groups) == 233 and len(quads) == 826
    assert points == [tuple(p) for p in geometry['point_order']]
    assert quads == geometry['quad_masks']
    for gi, (group, old) in enumerate(zip(groups, geometry['groups'], strict=True)):
        assert old['group_id'] == gi
        for key, value in group.items():
            assert old[key] == value, (gi, key)
        expected = [i for i, q in enumerate(quads)
                    if q & sum(1 << p for p in group['point_indices']) == q]
        assert expected == old['quad_indices']
    kept = witness['kept_group_ids']
    assert kept == sorted(set(kept)) and all(0 <= gi < 233 for gi in kept)
    selected = [groups[gi] for gi in kept]
    kept_quads = sum(len(list(combinations(g['point_indices'], 4))) for g in selected)
    assert kept_quads == witness['kept_quads']
    standard = solve(25, groups)
    print('standard:', standard, flush=True)
    changed = solve(25, selected)
    print('changed:', changed, flush=True)
    assert standard['winning_first_moves'] == changed['winning_first_moves']
    assert standard['winning_first_moves'] == [2, 6, 8, 10, 12, 14, 16, 18, 22]
    assert sum(1 << p for p in changed['winning_first_moves']) == witness['winning_first_move_mask']
    # Check that the whole family (not only its first-move labels) is D4 invariant.
    masks = {sum(1 << p for p in g['point_indices']) for g in selected}
    symmetric = True
    for mask in masks:
        for reflect in (False, True):
            for rotations in range(4):
                transformed = 0
                for p in members(mask):
                    x, y = points[p]
                    if reflect:
                        x = 4-x
                    for _ in range(rotations):
                        x, y = 4-y, x
                    transformed |= 1 << (x+5*y)
                symmetric &= transformed in masks
    out = {'n': 5, 'kept_groups': len(kept), 'removed_groups': 233-len(kept),
           'kept_group_ids': kept, 'kept_kind_counts': dict(Counter(g['kind'] for g in selected)),
           'kept_quads': kept_quads, 'd4_invariant': symmetric,
           'standard': standard, 'modified': changed,
           'selected_curves': [dict(group_id=gi, **groups[gi]) for gi in kept],
           'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
           'input_sha256': {geometry_file.name: hashlib.sha256(geometry_bytes).hexdigest(),
                            witness_file.name: hashlib.sha256(witness_bytes).hexdigest()},
           'seconds': time.perf_counter()-start}
    (root / args.output).write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('verified:', len(kept), 'whole curves, D4 invariant:', symmetric, flush=True)


if __name__ == '__main__':
    main()
