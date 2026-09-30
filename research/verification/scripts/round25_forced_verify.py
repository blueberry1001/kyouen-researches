"""Independent whole-curve and fixed-target AND/OR checks for B333/B334.

Fresh integer four-point determinants generate the forbidden family. No
existing geometry or solver module is imported. DP uses frozenset lengths;
fixed-target checks use actual player identities, with no Grundy filtering.
"""
from collections import Counter
from functools import cache
from itertools import combinations
from math import gcd
from pathlib import Path
import argparse
import hashlib
import json
import time


def bits(mask):
    while mask:
        bit = mask & -mask
        yield bit.bit_length()-1
        mask ^= bit


def det4(points):
    x, y = points[0]
    rows = [(a-x, b-y, (a-x)**2+(b-y)**2) for a, b in points[1:]]
    a, b, c = rows
    return (a[0]*(b[1]*c[2]-b[2]*c[1])
            - a[1]*(b[0]*c[2]-b[2]*c[0])
            + a[2]*(b[0]*c[1]-b[1]*c[0]))


def curve(points):
    (x, y), (xx, yy), (xxx, yyy) = points[:3]
    ux, uy, vx, vy = xx-x, yy-y, xxx-x, yyy-y
    cross = ux*vy-uy*vx
    if not cross:
        coefficients = [0, -uy, ux, uy*x-ux*y]
    else:
        a = cross
        fx = (ux*ux+uy*uy)*vy-(vx*vx+vy*vy)*uy
        fy = ux*(vx*vx+vy*vy)-vx*(ux*ux+uy*uy)
        coefficients = [a, -2*a*x-fx, -2*a*y-fy,
                        a*(x*x+y*y)+fx*x+fy*y]
    factor = gcd(*coefficients)
    coefficients = [z//factor for z in coefficients]
    if next(z for z in coefficients if z) < 0:
        coefficients = [-z for z in coefficients]
    return tuple(coefficients)


def geometry(n):
    points = [(x, y) for y in range(n) for x in range(n)]
    quads = []
    curves = set()
    for ids in combinations(range(n*n), 4):
        selected = [points[i] for i in ids]
        if det4(selected) == 0:
            quads.append(sum(1 << i for i in ids))
            curves.add(curve(selected))
    masks = []
    for a, b, c, d in sorted(curves):
        masks.append(sum(1 << i for i, (x, y) in enumerate(points)
                         if a*(x*x+y*y)+b*x+c*y+d == 0))
    reconstructed = [sum(1 << p for p in ids) for mask in masks
                     for ids in combinations(bits(mask), 4)]
    assert sorted(reconstructed) == sorted(quads) and len(set(reconstructed)) == len(quads)
    return points, quads, masks


def decode(mask):
    return frozenset(bits(mask))


def main():
    started = time.perf_counter()
    source = Path(__file__).resolve()
    root = source.parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs-only', action='store_true')
    args = parser.parse_args()
    if args.inputs_only:
        for n in range(2, 6):
            _, quads, _ = geometry(n)
            (root/f'round25_forced_n{n}_input.txt').write_text(
                f'{n*n} {len(quads)} 0\n'+' '.join(map(str, quads))+'\n', encoding='utf-8')
        print('all small-board inputs generated', flush=True)
        return
    result = json.loads((root/'round25_forced_n6.json').read_text())
    points, quads, masks = geometry(6)
    old = json.loads((root/'round23_b251_n6_geometry.json').read_text())
    assert quads == old['quad_masks']
    full = (1 << 36)-1

    @cache
    def children(s):
        legal = full ^ s
        for mask in masks:
            occupied = (mask & s).bit_count()
            assert occupied <= 3
            if occupied == 3:
                legal &= ~mask
        return tuple(s | (1 << p) for p in reversed(list(bits(legal))))

    @cache
    def solve(s):
        options = [solve(c) for c in children(s)]
        if not options:
            return 0, frozenset({s.bit_count()}), frozenset({s.bit_count()}), s.bit_count(), 0, 0
        nimbers = {c[0] for c in options}
        g = next(i for i in range(37) if i not in nimbers)
        allowed = [c for c in options if c[0] == 0] if g else options
        terminal = frozenset().union(*(c[1] for c in allowed))
        forced = (frozenset().union(*(c[2] for c in allowed)) if g
                  else allowed[0][2].intersection(*(c[2] for c in allowed[1:])))
        fast = (min if g else max)(c[3] for c in allowed)
        h = 1+max(c[4] for c in options)
        mu = 1+min(c[5] for c in options)
        return g, terminal, forced, fast, h, mu

    def verify_record(record):
        s = record['mask']
        actual = solve(s)
        expected = (record['g'], decode(record['Tstar_bits']), decode(record['WFT_bits']),
                    record['fast_terminal'], record['h'], record['mu'])
        assert actual == expected, (record, actual, expected)
        return {'mask': s, 'coordinates': [points[p] for p in bits(s)],
                'g': actual[0], 'Tstar': sorted(actual[1]), 'WFT': sorted(actual[2]),
                'fast_terminal': actual[3], 'h': actual[4], 'mu': actual[5]}

    targets = result['B333_gap_witnesses']+[result['B334_least_stone_witness'],result['B334_least_N_witness']]
    base_gap = result['B333_gap_witnesses'][0]['mask']
    images = set()
    for reflect in (False, True):
        for rotations in range(4):
            transformed = 0
            for p in bits(base_gap):
                x, y = points[p]
                if reflect:
                    x = 5-x
                for _ in range(rotations):
                    x, y = 5-y, x
                transformed |= 1 << (x+6*y)
            images.add(transformed)
    assert len(images) == 8 and images == {r['mask'] for r in result['B333_gap_witnesses']}
    records = []
    for record in targets:
        checked = verify_record(record)
        s = record['mask']
        winner = 0 if checked['g'] else 1
        start_k = s.bit_count()
        force_checks = {}
        for target in range(min(checked['Tstar']), max(checked['Tstar'])+1, 2):
            @cache
            def force(s_now):
                moves = children(s_now)
                player = (s_now.bit_count()-start_k) % 2
                if not moves:
                    return s_now.bit_count() == target and 1-player == winner
                possibilities = (force(c) for c in moves)
                return any(possibilities) if player == winner else all(possibilities)
            can_force = force(s)
            assert can_force == (target in checked['WFT'])
            force_checks[str(target)] = can_force
        checked['fixed_target_actual_player_checks'] = force_checks
        if checked['g'] and not checked['WFT']:
            winning_children = [c for c in children(s) if solve(c)[0] == 0]
            assert winning_children and all(not solve(c)[2] for c in winning_children)
            checked['winning_children'] = [{'mask': c, 'g': solve(c)[0],
                                            'Tstar': sorted(solve(c)[1]), 'WFT': sorted(solve(c)[2])}
                                           for c in winning_children]
        records.append(checked)
        print('independent', s, 'Tstar', checked['Tstar'], 'WFT', checked['WFT'], 'PASS', flush=True)
    checked_children = [verify_record(c) for c in result['B334_least_witness_children']]
    assert {c['mask'] for c in checked_children} == set(children(result['B334_least_stone_witness']['mask']))
    assert set.intersection(*(set(c['WFT']) for c in checked_children)) == set()
    assert set.union(*(set(c['Tstar']) for c in checked_children)) == {7,9,11}
    independent_states = solve.cache_info().currsize
    small_checks = []
    for n in range(2, 6):
        _, small_quads, small_masks = geometry(n)
        (root/f'round25_forced_n{n}_input.txt').write_text(
            f'{n*n} {len(small_quads)} 0\n'+ ' '.join(map(str, small_quads))+'\n', encoding='utf-8')
        small_full = (1 << (n*n))-1

        @cache
        def small_children(s):
            legal = small_full ^ s
            for mask in small_masks:
                if (mask & s).bit_count() == 3:
                    legal &= ~mask
            return tuple(s | (1 << p) for p in bits(legal))

        small_values = {}

        def small_solve(s):
            if s in small_values:
                return small_values[s]
            options = [small_solve(c) for c in small_children(s)]
            if not options:
                value = 0, frozenset({s.bit_count()}), frozenset({s.bit_count()})
            else:
                seen = {c[0] for c in options}
                g = next(i for i in range(n*n+1) if i not in seen)
                allowed = [c for c in options if not c[0]] if g else options
                terminal = frozenset().union(*(c[1] for c in allowed))
                forced = (frozenset().union(*(c[2] for c in allowed)) if g
                          else allowed[0][2].intersection(*(c[2] for c in allowed[1:])))
                value = g, terminal, forced
            small_values[s] = value
            return value

        small_solve(0)
        gap_count = sum(bool(w) and any(t not in w for t in range(min(w),max(w)+1,2))
                        for _, _, w in small_values.values())
        empty_count = sum(len(t) >= 3 and not w for _, t, w in small_values.values())
        assert gap_count == empty_count == 0
        small_result = json.loads((root/f'round25_forced_n{n}.json').read_text())
        assert small_result['safe_states'] == len(small_values)
        assert small_result['B333_gap_count'] == gap_count
        assert small_result['B334_count'] == empty_count
        small_checks.append({'n': n, 'safe_states': len(small_values),
                             'B333_gap_count': gap_count, 'B334_count': empty_count})
        print('small-board independent', n, 'states', len(small_values), 'PASS', flush=True)
    output = {'n': 6, 'forbidden_quads': len(quads), 'whole_curves': len(masks),
              'witnesses': records, 'B334_children': checked_children,
              'independent_subgame_states': independent_states, 'small_board_full_checks': small_checks,
              'sources_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in
                                  (source, source.with_name('round25_forced_lengths.cpp'),
                                   root/'round25_forced_n6.json', root/'round23_b251_n6_input.txt')},
              'seconds': time.perf_counter()-started}
    (root/'round25_forced_verified.json').write_text(json.dumps(output, indent=2)+'\n', encoding='utf-8')
    print('PASS independent states', output['independent_subgame_states'], flush=True)


if __name__ == '__main__':
    main()
