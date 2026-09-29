#!/usr/bin/env python3
"""Round5 B551-B600 follow-up: weakened-form evidence.

Focus:
  B587/B589 xor-breaking amplification inventory
  B572 jump vs max nimber
  B581/B582 longer path/cycle on n=5
  B578 shared-winning-move symmetric difference
  B563 one-stone log-concavity (n=5 confirm)
  B591-B593 d_max ratio compression from existing table
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kyouen_core import Board, board_square
from residual_core import residual_R, residual_candidates


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


def graph_components(nverts: int, edges: list[tuple[int, int]]) -> list[list[int]]:
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


def abstract_type(comp_verts: list[int], edges: list[tuple[int, int]]):
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
    out = {}
    single_g = {}
    for m in range(1, 8):
        single_g[('path', m)] = path_cycle_g(m, False)
        if m >= 3:
            single_g[('cycle', m)] = path_cycle_g(m, True)
    out['single_g'] = {str(k): v for k, v in single_g.items()}

    # --- B587/B589: xor-breaking amplification inventory ---
    print('=== B587/B589 xor amplification ===')
    amp = {
        'by_type': defaultdict(list),
        'g_values_from_links': Counter(),
        'amplitude_hist': Counter(),  # g_total - g_xor
        'g4_found': [],
        'g5_found': [],
        'max_g_link': 0,
        'max_g_link_rec': None,
        'n_checked': {},
        'distinct_g_from_2comp': set(),
        'p3p3': [],
        'p3p3_cross': [],
    }

    for n in (4, 5):
        board = board_square(n)
        grundy = board.solve_grundy()
        max_sz = 5 if n == 5 else 8
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
                'n': n,
                'g_total': g_total,
                'g_xor': g_xor,
                'cross': len(cross),
                'S_size': occ.bit_count(),
            })
            if g_total >= 4:
                rec = {
                    'n': n, 'g_total': g_total, 'g_xor': g_xor, 'types': [t0, t1],
                    'cross': len(cross),
                    'S_pts': [board.points[i] for i in range(board.V) if (occ >> i) & 1],
                }
                if g_total == 4:
                    amp['g4_found'].append(rec)
                if g_total >= 5:
                    amp['g5_found'].append(rec)
            if g_total > amp['max_g_link']:
                amp['max_g_link'] = g_total
                amp['max_g_link_rec'] = {
                    'n': n, 'g_total': g_total, 'g_xor': g_xor, 'types': [t0, t1],
                    'cross': len(cross),
                    'S_pts': [board.points[i] for i in range(board.V) if (occ >> i) & 1],
                }
            if t0 == ('path', 3) and t1 == ('path', 3):
                rec = {
                    'n': n, 'g_total': g_total, 'g_xor': g_xor, 'cross': len(cross),
                    'S_pts': [board.points[i] for i in range(board.V) if (occ >> i) & 1],
                }
                amp['p3p3'].append(rec)
                if cross:
                    amp['p3p3_cross'].append(rec)
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
    amp['p3p3_cross_count'] = len(amp['p3p3_cross'])
    amp['p3p3_g_values'] = sorted(set(x['g_total'] for x in amp['p3p3']))
    out['b587_b589_amp'] = amp
    print('distinct g from 2comp links:', amp['distinct_g_from_2comp'])
    print('max g link:', amp['max_g_link'])
    print('g4 found:', len(amp['g4_found']), 'g5+:', len(amp['g5_found']))
    print('P3xP3:', amp['p3p3_count'], 'cross:', amp['p3p3_cross_count'], 'g:', amp['p3p3_g_values'])

    # --- B572: jump magnitude vs max nimber ---
    print()
    print('=== B572 one-stone swap jump ===')
    b572 = {'n4': {}, 'n5_sample': {}}
    for n, max_sz in ((4, 6), (5, 5)):
        board = board_square(n)
        grundy = board.solve_grundy()
        max_nimber = max(grundy.values()) if grundy else 0
        max_jump = 0
        jump_rec = None
        n_pairs = 0
        for occ in grundy:
            if occ == 0 or occ.bit_count() > max_sz:
                continue
            # one-stone exchange: remove one, add one
            bits = [i for i in range(board.V) if (occ >> i) & 1]
            g0 = grundy[occ]
            for i in bits:
                base = occ ^ (1 << i)
                # legal additions
                for j in range(board.V):
                    if (base >> j) & 1:
                        continue
                    nxt = base | (1 << j)
                    if nxt not in grundy:
                        continue
                    if not board.is_safe(nxt):
                        continue
                    n_pairs += 1
                    jump = abs(grundy[nxt] - g0)
                    if jump > max_jump:
                        max_jump = jump
                        jump_rec = {
                            'n': n,
                            'from': [board.points[k] for k in bits],
                            'remove': board.points[i],
                            'add': board.points[j],
                            'g_from': g0,
                            'g_to': grundy[nxt],
                            'jump': jump,
                        }
        key = 'n4' if n == 4 else 'n5_sample'
        b572[key] = {
            'max_nimber': max_nimber,
            'max_jump': max_jump,
            'n_exchange_pairs': n_pairs,
            'witness': jump_rec,
        }
        print(f'n={n}: max_nimber={max_nimber}, max_jump={max_jump}, pairs={n_pairs}')
    out['b572'] = b572

    # --- B581/B582: longer path/cycle on n=5 |S|<=6 ---
    print()
    print('=== B581/B582 longer path/cycle ===')
    b581 = {'m_found': set(), 'min_S_by_m': {}, 'examples': [], 'n_scanned': 0}
    b582 = {'m_found': set(), 'min_S_by_m': {}, 'examples': [], 'n_scanned': 0}
    for n in (5,):
        board = board_square(n)
        grundy = board.solve_grundy()
        max_sz = 6
        for occ in grundy:
            if occ == 0 or occ.bit_count() > max_sz:
                continue
            b581['n_scanned'] += 1
            R = residual_R(board, occ)
            edges = []
            higher = []
            for r in R:
                bits = [i for i in range(board.V) if (r >> i) & 1]
                if len(bits) == 2:
                    edges.append((bits[0], bits[1]))
                else:
                    higher.append(r)
            if not edges or higher:
                continue  # pure 2-point residual required
            comps = graph_components(board.V, edges)
            comps = [c for c in comps if any(v in {x for e in edges for x in e} for v in c)]
            if len(comps) != 1:
                continue
            t = abstract_type(comps[0], edges)
            if t[0] == 'path':
                m = t[1]
                b581['m_found'].add(m)
                if m not in b581['min_S_by_m'] or occ.bit_count() < b581['min_S_by_m'][m]:
                    b581['min_S_by_m'][m] = occ.bit_count()
                    if m >= 7:
                        b581['examples'].append({
                            'm': m,
                            'S_pts': [board.points[i] for i in range(board.V) if (occ >> i) & 1],
                            'path_pts': [board.points[v] for v in comps[0]],
                        })
            elif t[0] == 'cycle':
                m = t[1]
                if m % 2 == 1:
                    b582['m_found'].add(m)
                    if m not in b582['min_S_by_m'] or occ.bit_count() < b582['min_S_by_m'][m]:
                        b582['min_S_by_m'][m] = occ.bit_count()
                        if m >= 7:
                            b582['examples'].append({
                                'm': m,
                                'S_pts': [board.points[i] for i in range(board.V) if (occ >> i) & 1],
                                'cycle_pts': [board.points[v] for v in comps[0]],
                            })
    b581['m_found'] = sorted(b581['m_found'])
    b581['min_S_by_m'] = {str(k): v for k, v in sorted(b581['min_S_by_m'].items())}
    b582['m_found'] = sorted(b582['m_found'])
    b582['min_S_by_m'] = {str(k): v for k, v in sorted(b582['min_S_by_m'].items())}
    out['b581_n5'] = b581
    out['b582_n5'] = b582
    print('B581 m found:', b581['m_found'], 'minS:', b581['min_S_by_m'])
    print('B582 m found:', b582['m_found'], 'minS:', b582['min_S_by_m'])

    # --- B578: shared winning-move symmetric difference ---
    print()
    print('=== B578 shared winning move symdiff ===')
    b578 = {}
    for n, max_sz in ((4, 6), (5, 5)):
        board = board_square(n)
        outcomes = board.solve_outcomes()
        # group N-positions by a common winning move
        # winning move = move to P-position
        by_win_move = defaultdict(list)
        for occ, val in outcomes.items():
            if val != 1:  # not N (1 = next player win)
                continue
            if occ == 0 or occ.bit_count() > max_sz:
                continue
            for v in board.legal_moves(occ):
                nxt = occ | (1 << v)
                if outcomes.get(nxt) == 0:
                    by_win_move[v].append(occ)
        max_sd = 0
        sd_rec = None
        n_groups = 0
        for v, positions in by_win_move.items():
            if len(positions) < 2:
                continue
            n_groups += 1
            # find max pairwise symmetric difference
            for i in range(len(positions)):
                for j in range(i + 1, len(positions)):
                    sd = (positions[i] ^ positions[j]).bit_count()
                    if sd > max_sd:
                        max_sd = sd
                        sd_rec = {
                            'n': n,
                            'win_move': board.points[v],
                            'A': [board.points[k] for k in range(board.V) if (positions[i] >> k) & 1],
                            'B': [board.points[k] for k in range(board.V) if (positions[j] >> k) & 1],
                            'symdiff': sd,
                        }
        b578[f'n{n}'] = {
            'max_symdiff': max_sd,
            'ratio': max_sd / (n * n),
            'n_groups': n_groups,
            'witness': sd_rec,
        }
        print(f'n={n}: max_symdiff={max_sd} ({max_sd}/{n*n}={max_sd/(n*n):.2f}), groups={n_groups}')
    out['b578'] = b578

    # --- B563: one-stone log-concavity on n=5 (reconfirm with f_p arrays) ---
    print()
    print('=== B563 one-stone log-concavity ===')
    b563 = {'n': 5, 'n_points': 0, 'n_break': 0, 'by_type': Counter(), 'examples': []}
    n = 5
    board = board_square(n)
    # f_S(k) = number of safe supersets of S of size k
    # For one fixed stone p: f_p(k) for k=1..K
    # Compute all safe sets by size, then for each point count supersets
    K = board.max_safe_size()
    # enumerate safe sets up to K
    safe_by_size = defaultdict(list)
    # DFS enumeration
    def dfs(occ, start):
        sz = occ.bit_count()
        safe_by_size[sz].append(occ)
        if sz >= K:
            return
        for v in range(start, board.V):
            if (occ >> v) & 1:
                continue
            nxt = occ | (1 << v)
            if board.is_safe(nxt):
                dfs(nxt, v + 1)
    dfs(0, 0)
    # for each point p, f_p(k) = #{safe T : p in T, |T|=k}
    for p in range(board.V):
        x, y = board.points[p]
        if (x, y) == (0, 0):
            ptype = 'corner'
        elif x == 0 or y == 0 or x == n - 1 or y == n - 1:
            ptype = 'edge'
        else:
            ptype = 'interior'
        fp = []
        for k in range(1, K + 1):
            cnt = sum(1 for occ in safe_by_size[k] if (occ >> p) & 1)
            fp.append(cnt)
        # log-concavity: fp[i-1]*fp[i+1] <= fp[i]^2 for interior i
        breaks = []
        for i in range(1, len(fp) - 1):
            if fp[i] <= 0:
                continue
            if fp[i - 1] * fp[i + 1] > fp[i] * fp[i]:
                breaks.append((i, fp[i - 1], fp[i], fp[i + 1]))
        b563['n_points'] += 1
        b563['by_type'][ptype] += 1
        if breaks:
            b563['n_break'] += 1
            b563['examples'].append({'p': board.points[p], 'type': ptype, 'fp': fp, 'breaks': breaks})
    b563['by_type'] = dict(b563['by_type'])
    out['b563'] = b563
    print(f"one-stone: {b563['n_break']}/{b563['n_points']} break log-concavity")

    # --- B591/B593 compression from known d_max ---
    print()
    print('=== B591/B593 d_max ratio ===')
    # Known: n=4 K=8 d_max=2? Wait, from prior: n=4..8 d_max = 2,3,4,8,6
    # K_n: n=4:8, n=5:10, n=6:11, n=7:14, n=8:15
    known = [
        (4, 8, 2),
        (5, 10, 3),
        (6, 11, 4),
        (7, 14, 8),
        (8, 15, 6),
    ]
    b591 = []
    for n, K, dmax in known:
        b591.append({
            'n': n, 'K': K, 'd_max': dmax,
            'd_over_n': dmax / n,
            'C_needed': dmax,  # for c=1
        })
    out['b591_b593'] = b591
    for r in b591:
        print(r)

    out['note'] = ('followup computations for B551-B600; '
                   'n<=5 only; no n>=7 enumeration; no p_rand')

    path = Path(__file__).resolve().parent.parent / 'round5_b551_b600_followup.json'
    with open(path, 'w') as f:
        json.dump(out, f, indent=2, default=str)
    print()
    print('wrote', path)


if __name__ == '__main__':
    main()
