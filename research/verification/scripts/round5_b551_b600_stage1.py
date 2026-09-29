#!/usr/bin/env python3
"""Stage 1: B587/B589 xor amplification on n=4 full + n=5 |S|<=5."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kyouen_core import board_square
from residual_core import residual_R


def path_cycle_g(m: int, is_cycle: bool) -> int:
    from functools import lru_cache

    @lru_cache(maxsize=None)
    def ev(mask):
        moves = []
        for v in range(m):
            if (mask >> v) & 1:
                continue
            if is_cycle:
                left, right = (v - 1) % m, (v + 1) % m
                if (mask >> left) & 1 or (mask >> right) & 1:
                    continue
            else:
                if v > 0 and (mask >> (v - 1)) & 1:
                    continue
                if v + 1 < m and (mask >> (v + 1)) & 1:
                    continue
            moves.append(v)
        if not moves:
            return 0
        seen = set()
        for v in moves:
            seen.add(ev(mask | (1 << v)))
        g = 0
        while g in seen:
            g += 1
        return g

    return ev(0)


def graph_components(nverts: int, edges):
    adj = [[] for _ in range(nverts)]
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    seen = [False] * nverts
    comps = []
    for s in range(nverts):
        if seen[s]:
            continue
        stack = [s]
        seen[s] = True
        cur = []
        while stack:
            u = stack.pop()
            cur.append(u)
            for w in adj[u]:
                if not seen[w]:
                    seen[w] = True
                    stack.append(w)
        comps.append(sorted(cur))
    return comps


def abstract_type(comp_verts, edges):
    vs = set(comp_verts)
    deg = {v: 0 for v in comp_verts}
    ecount = 0
    for a, b in edges:
        if a in vs and b in vs:
            deg[a] += 1
            deg[b] += 1
            ecount += 1
    m = len(comp_verts)
    if ecount == m - 1 and all(d <= 2 for d in deg.values()) and sum(1 for d in deg.values() if d == 1) == 2:
        return ('path', m)
    if ecount == m and all(d == 2 for d in deg.values()):
        return ('cycle', m)
    degrees = tuple(sorted(deg.values()))
    return ('other', m, ecount, degrees)


def main():
    single_g = {}
    for m in range(1, 8):
        single_g[('path', m)] = path_cycle_g(m, False)
        if m >= 3:
            single_g[('cycle', m)] = path_cycle_g(m, True)
    print('single_g', single_g)

    amp = {
        'single_g': {str(k): v for k, v in single_g.items()},
        'by_type': defaultdict(list),
        'g_values_from_links': Counter(),
        'amplitude_hist': Counter(),
        'g4_found': [],
        'g5_found': [],
        'max_g_link': 0,
        'max_g_link_rec': None,
        'n_checked': {},
        'distinct_g_from_2comp': set(),
        'p3p3': [],
    }

    for n, max_sz in ((4, 8), (5, 5)):
        board = board_square(n)
        grundy = board.solve_grundy()
        n_two = 0
        for occ in grundy:
            if occ == 0 or occ.bit_count() > max_sz:
                continue
            R = residual_R(board, occ)
            edges = []
            higher = []
            for r in R:
                bits = [i for i in range(board.V) if (r >> i) & 1]
                if len(bits) == 2:
                    edges.append((bits[0], bits[1]))
                else:
                    higher.append(r)
            if not edges:
                continue
            comps = graph_components(board.V, edges)
            comps = [c for c in comps if any(v in {x for e in edges for x in e} for v in c)]
            if len(comps) != 2:
                continue
            t0 = abstract_type(comps[0], edges)
            t1 = abstract_type(comps[1], edges)
            if t0[0] not in ('path', 'cycle') or t1[0] not in ('path', 'cycle'):
                continue
            n_two += 1
            g_total = grundy[occ]
            g_xor = single_g.get(t0, 0) ^ single_g.get(t1, 0)
            s0, s1 = set(comps[0]), set(comps[1])
            cross = []
            for r in higher:
                bits = set(i for i in range(board.V) if (r >> i) & 1)
                if bits & s0 and bits & s1:
                    cross.append(r)
            amp['distinct_g_from_2comp'].add(g_total)
            amp['g_values_from_links'][g_total] += 1
            amp['amplitude_hist'][g_total - g_xor] += 1
            key = f'{t0}|{t1}'
            amp['by_type'][key].append({
                'n': n, 'g_total': g_total, 'g_xor': g_xor,
                'cross': len(cross), 'S_size': occ.bit_count(),
            })
            if g_total >= 4:
                rec = {
                    'n': n, 'g_total': g_total, 'g_xor': g_xor,
                    'types': [t0, t1], 'cross': len(cross),
                    'S_pts': [board.points[i] for i in range(board.V) if (occ >> i) & 1],
                }
                if g_total == 4:
                    amp['g4_found'].append(rec)
                if g_total >= 5:
                    amp['g5_found'].append(rec)
            if g_total > amp['max_g_link']:
                amp['max_g_link'] = g_total
                amp['max_g_link_rec'] = {
                    'n': n, 'g_total': g_total, 'g_xor': g_xor,
                    'types': [t0, t1], 'cross': len(cross),
                    'S_pts': [board.points[i] for i in range(board.V) if (occ >> i) & 1],
                }
            if t0 == ('path', 3) and t1 == ('path', 3):
                amp['p3p3'].append({
                    'n': n, 'g_total': g_total, 'g_xor': g_xor,
                    'cross': len(cross),
                    'S_pts': [board.points[i] for i in range(board.V) if (occ >> i) & 1],
                })
        amp['n_checked'][n] = {'two_comp_path_cycle': n_two}
        print(f'n={n}: two-comp path/cycle = {n_two}')

    amp['by_type'] = {k: {
        'count': len(v),
        'g_values': sorted(set(x['g_total'] for x in v)),
        'g_xor_values': sorted(set(x['g_xor'] for x in v)),
        'max_amp': max(x['g_total'] - x['g_xor'] for x in v),
        'with_cross': sum(1 for x in v if x['cross'] > 0),
        'without_cross': sum(1 for x in v if x['cross'] == 0),
    } for k, v in amp['by_type'].items()}
    amp['g_values_from_links'] = dict(amp['g_values_from_links'])
    amp['amplitude_hist'] = dict(amp['amplitude_hist'])
    amp['distinct_g_from_2comp'] = sorted(amp['distinct_g_from_2comp'])
    amp['p3p3_count'] = len(amp['p3p3'])
    amp['p3p3_g_values'] = sorted(set(x['g_total'] for x in amp['p3p3']))
    amp['p3p3_cross_count'] = sum(1 for x in amp['p3p3'] if x['cross'] > 0)

    print('distinct g:', amp['distinct_g_from_2comp'])
    print('max g link:', amp['max_g_link'])
    print('g4:', len(amp['g4_found']), 'g5+:', len(amp['g5_found']))
    print('P3xP3:', amp['p3p3_count'], 'g:', amp['p3p3_g_values'], 'cross:', amp['p3p3_cross_count'])

    path = Path(__file__).resolve().parent.parent / 'round5_b551_b600_followup.json'
    data = {}
    if path.exists():
        with open(path) as f:
            data = json.load(f)
    data['b587_b589_amp'] = amp
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    print('wrote', path)


if __name__ == '__main__':
    main()
