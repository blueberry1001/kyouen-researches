"""Independent certificate checker: standard library, no search-code imports.

Geometry uses the Leibniz determinant formula, unlike the producer's
cofactor implementation. Non-reachability is checked by closure, not BFS.
Run with ordinary Python (not -O, since the checks use assertions).
"""
from collections import Counter
from itertools import combinations, permutations
from pathlib import Path
import hashlib
import json
import struct

ROOT = Path(__file__).resolve().parents[1]
PERMS = [(p, (-1) ** sum(p[i] > p[j] for i in range(4) for j in range(i+1,4)))
         for p in permutations(range(4))]


def forbidden(points):
    rows = [[p % 7, p // 7, (p % 7)**2 + (p // 7)**2, 1] for p in points]
    total = 0
    for perm, sign in PERMS:
        product = sign
        for i in range(4):
            product *= rows[i][perm[i]]
        total += product
    return total == 0


def geometry(cells):
    return [sum(1 << i for i in inds) for inds in combinations(range(len(cells)), 4)
            if forbidden([cells[i] for i in inds])]


def safe(mask, quads):
    return all(mask & q != q for q in quads)


def check_path(path, a, b, quads, floor, count):
    assert path and path[0] == a and path[-1] == b
    assert all(isinstance(m,int) and 0 <= m < 1 << count for m in path)
    assert all(m.bit_count() >= floor and safe(m,quads) for m in path)
    assert all((x ^ y).bit_count() == 1 for x,y in zip(path,path[1:]))


def transform(mask, symmetry):
    result = 0
    for p in range(49):
        if mask >> p & 1:
            x,y = p%7,p//7
            if symmetry & 1: x = 6-x
            if symmetry & 2: y = 6-y
            if symmetry & 4: x,y = y,x
            result |= 1 << (y*7+x)
    return result


def main():
    assert __debug__, 'Run without -O'
    static_path = ROOT/'results/discovery_corridor_static_certificate.json'
    auxiliary_path = ROOT/'results/discovery_corridor_auxiliary.json'
    s = json.loads(static_path.read_text())
    d = json.loads(auxiliary_path.read_text())
    cells, a, b = s['cells'], s['a'], s['b']
    assert (cells,a,b) == (d['cells'],d['a'],d['b'])
    assert len(cells) == len(set(cells)) == 19 and all(0 <= p < 49 for p in cells)
    assert a.bit_count() == b.bit_count() == 14
    assert a|b == (1 << 19)-1 and (a&b).bit_count() == 9
    quads = geometry(cells)
    assert len(quads) == 59 and safe(a,quads) and safe(b,quads)
    pa,pb = a&~b,b&~a
    assert (a & pb).bit_count() - (a & pa).bit_count() == -5
    assert (b & pb).bit_count() - (b & pa).bit_count() == 5
    assert s['barrier_differences'] == [2,3] and s['capacity_bound'] == 12
    assert len(s['covering_quads']) == 21 and set(s['covering_quads']) <= set(quads)
    checked = 0
    sizes = Counter()
    for mask in range(1 << 19):
        if mask.bit_count() >= 13 and (mask & pb).bit_count() - (mask & pa).bit_count() in (2,3):
            assert not safe(mask,s['covering_quads'])
            checked += 1
            sizes[mask.bit_count()] += 1
    assert checked == s['candidate_count'] == 6460
    assert {str(k):v for k,v in sizes.items()} == s['candidate_sizes']
    check_path(s['path_floor_11'],a,b,quads,11,19)
    assert min(m.bit_count() for m in s['path_floor_11']) == 11

    # Positive path or a closed safe subset proves each of the 30 cases.
    assert d['floor'] == 12
    assert sorted(r['extra_cell'] for r in d['rows']) == sorted(set(range(49))-set(cells))
    successes = []
    closure_checks = 0
    for row in d['rows']:
        p = row['extra_cell']
        assert row['xy'] == [p%7,p//7]
        qs = geometry(cells+[p])
        assert len(qs)-len(quads) == row['added_quads']
        if row['connected']:
            check_path(row['path'],a,b,qs,12,20)
            assert any(m >> 19 & 1 for m in row['path'])
            successes.append(p)
        else:
            assert row['path'] is None
            states_list = d['closed_sets'][row['closed_set_id']]
            states = set(states_list)
            assert len(states) == len(states_list) == row['visited']
            assert a in states and b not in states
            for m in states:
                assert 0 <= m < 1 << 20 and m.bit_count() >= 12 and safe(m,qs)
                for i in range(20):
                    other = m ^ (1 << i)
                    if other.bit_count() >= 12 and safe(other,qs):
                        assert other in states
                    closure_checks += 1
    assert successes == [48]
    assert set([0,6,42,48])-set(cells) == {48}

    # Full-board width cannot be 13: every one-stone swap out of A is unsafe.
    aa = sum(1 << p for i,p in enumerate(cells) if a >> i & 1)
    bb = sum(1 << p for i,p in enumerate(cells) if b >> i & 1)
    swaps = 0
    for removed in range(49):
        if not aa >> removed & 1: continue
        rest = [p for p in range(49) if p != removed and aa >> p & 1]
        for added in range(49):
            if aa >> added & 1: continue
            assert any(forbidden(list(triple)+[added]) for triple in combinations(rest,3))
            swaps += 1
    assert swaps == 490
    # No direct fifteenth stone is possible either: for each added point,
    # the previous swap checks already exhibit a forbidden quad in A+point.

    # Generalize the representative to all eight nearest cross-phase pairs.
    raw = (ROOT/'night-research/maxsafe_n7_K14.bin').read_bytes()
    census = [x[0] for x in struct.iter_unpack('<Q',raw)]
    assert len(census) == len(set(census)) == 16
    nearest = {(x,y) for x in census if x >> 24 & 1 for y in census
               if not y >> 24 & 1 and (x^y).bit_count() == 10}
    orbit = {(transform(aa,i),transform(bb,i)) for i in range(8)}
    assert nearest == orbit and len(orbit) == 8
    assert min((x^y).bit_count() for x in census if x >> 24 & 1
               for y in census if not y >> 24 & 1) == 10

    # Full-board reachability certificates: spanning tree + closure.
    full_quads = geometry(list(range(49)))
    assert len(full_quads) == 6364
    by_point = [[q for q in full_quads if q >> p & 1] for p in range(49)]
    full_cert_paths = []
    full_components = {}
    for forbidden_point, expected_count in [(48,250),(-1,903)]:
        full_path = ROOT/f'results/discovery_full_board_forbid_{forbidden_point}.json'
        full_cert_paths.append(full_path)
        cert = json.loads(full_path.read_text())
        assert cert['forbidden_cell'] == forbidden_point and cert['floor'] == 12
        assert cert['complete'] and cert['processed'] == cert['reached'] == expected_count
        component = set(cert['closed_set'])
        assert len(component) == len(cert['closed_set']) == expected_count
        tree_seen = set()
        for m,parent in cert['spanning_tree']:
            assert m not in tree_seen and m in component
            if parent is None:
                assert m == aa and not tree_seen
            else:
                assert parent in tree_seen and (m^parent).bit_count() == 1
            tree_seen.add(m)
        assert tree_seen == component
        for m in component:
            assert 0 <= m < 1 << 49 and m.bit_count() >= 12 and safe(m,full_quads)
            assert forbidden_point < 0 or not m >> forbidden_point & 1
            for p in range(49):
                if p == forbidden_point: continue
                other = m ^ (1 << p)
                if other.bit_count() >= 12 and (m >> p & 1 or safe(other,by_point[p])):
                    assert other in component
        assert (bb in component) == cert['found'] == (forbidden_point < 0)
        if forbidden_point < 0:
            check_path(cert['path'],aa,bb,full_quads,12,49)
        assert sorted(m for m in component if m.bit_count()==14) == cert['reachable_14_sets']
        full_components[forbidden_point] = component
    assert set(census) & full_components[-1] == {aa,bb}
    symmetric_components = [{transform(m,i) for m in full_components[-1]} for i in range(8)]
    assert all(not (x & y) for x,y in combinations(symmetric_components,2))
    assert set().union(*(comp & set(census) for comp in symmetric_components)) == set(census)
    report = dict(status='PASS', static_candidates=checked, static_quads=21,
                  negative_auxiliary_cases=29, positive_auxiliary_cells=successes,
                  closure_neighbor_checks=closure_checks, forbidden_full_board_swaps=swaps,
                  symmetry_related_pairs=8, restricted_width=11, full_board_width=12,
                  forbidden_corner_component_size=250, full_board_component_size=903,
                  full_board_component_layers=dict(sorted(Counter(m.bit_count() for m in full_components[-1]).items())),
                  maximum_bearing_components=8, maxima_per_component=2,
                  certificate_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                      for p in (static_path,auxiliary_path,*full_cert_paths)})
    (ROOT/'results/discovery_corridor_verification.json').write_text(json.dumps(report,indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
