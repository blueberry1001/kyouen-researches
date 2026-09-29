#!/usr/bin/env python3
"""Round5 B551-B600: B585 cost comparison + B588 same-parts xor test.

Also: B581/B582 longer path/cycle search on n=6 samples.

Data out: research/verification/round5_b551_b600.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kyouen_core import Board, board_square
from residual_core import residual_R, residual_candidates

# Independent-set game on a graph (2-point residuals only): g via subsets.
def path_cycle_g(m: int, is_cycle: bool) -> int:
    """g of independent-set game on P_m or C_m (no-adjacent-pair placement)."""
    # states: subsets of {0..m-1} with no two adjacent (mod m if cycle)
    def ok(mask):
        for i in range(m):
            if (mask >> i) & 1:
                j = (i + 1) % m
                if is_cycle and (mask >> j) & 1:
                    return False
                if not is_cycle and i + 1 < m and (mask >> (i + 1)) & 1:
                    return False
        return True

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
    """Classify a connected 2-point residual component as path or cycle."""
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
    # fallback
    degrees = tuple(sorted(deg.values()))
    return ('other', m, ecount, degrees)


def solve_grundy_small(board: Board) -> dict[int, int]:
    return board.solve_grundy()


def main():
    out = {}
    print('=== B588: same-parts two-component xor test ===')
    b588 = {
        'same_type_pairs': [],
        'xor_violations': [],
        'n_checked': {},
        'type_pair_counts': Counter(),
        'with_cross_higher': [],
        'without_cross_higher_xor_ok': 0,
        'without_cross_higher_xor_bad': 0,
    }

    # known single-piece g
    single_g = {}
    for m in range(1, 7):
        single_g[('path', m)] = path_cycle_g(m, False)
        if m >= 3:
            single_g[('cycle', m)] = path_cycle_g(m, True)
    print('single-piece g:', single_g)

    for n in (4,):
        board = board_square(n)
        grundy = solve_grundy_small(board)
        count_pairs = 0
        count_safe = 0
        max_sz = 8
        for occ in grundy:
            if occ == 0 or occ.bit_count() > max_sz:
                continue
            R = residual_R(board, occ)
            # build 2-point edges from R
            edges = []
            higher = []
            L = 0
            for v in board.legal_moves(occ):
                L |= 1 << v
            for r in R:
                bits = [i for i in range(board.V) if (r >> i) & 1]
                if len(bits) == 2:
                    edges.append((bits[0], bits[1]))
                else:
                    higher.append(r)
            if not edges:
                continue
            verts = sorted({v for e in edges for v in e})
            # only consider if all legal points appear as edge endpoints or we restrict
            comps = graph_components(board.V, edges)
            # keep only comps that have edges
            comps = [c for c in comps if any(v in {x for e in edges for x in e} for v in c)]
            if len(comps) != 2:
                continue
            t0 = abstract_type(comps[0], edges)
            t1 = abstract_type(comps[1], edges)
            count_pairs += 1
            b588['type_pair_counts'][f'{t0}|{t1}'] += 1
            if t0 != t1:
                continue
            # same type
            count_safe += 1
            # check higher-order residuals that span components
            s0, s1 = set(comps[0]), set(comps[1])
            cross = []
            for r in higher:
                bits = set(i for i in range(board.V) if (r >> i) & 1)
                if bits & s0 and bits & s1:
                    cross.append(r)
            g_total = grundy[occ]
            g_xor = None
            if t0[0] == 'path' and t1[0] == 'path':
                if t0 in single_g and t1 in single_g:
                    g_xor = single_g[t0] ^ single_g[t1]
            elif t0[0] == 'cycle' and t1[0] == 'cycle':
                if t0 in single_g and t1 in single_g:
                    g_xor = single_g[t0] ^ single_g[t1]
            rec = {
                'n': n,
                'S_size': occ.bit_count(),
                'types': [t0, t1],
                'comps': [[board.points[v] for v in c] for c in comps],
                'g_total': g_total,
                'g_xor': g_xor,
                'cross_higher_count': len(cross),
                'xor_match': (g_total == g_xor) if g_xor is not None else None,
            }
            b588['same_type_pairs'].append(rec)
            if cross:
                b588['with_cross_higher'].append(rec)
            else:
                if g_xor is not None:
                    if g_total == g_xor:
                        b588['without_cross_higher_xor_ok'] += 1
                    else:
                        b588['without_cross_higher_xor_bad'] += 1
                        b588['xor_violations'].append(rec)
        b588['n_checked'][n] = {
            'two_comp_pairs': count_pairs,
            'same_type': count_safe,
        }
        print(f'n={n}: two-comp={count_pairs}, same-type={count_safe}')

    # convert Counter
    b588['type_pair_counts'] = dict(b588['type_pair_counts'])
    out['b588'] = b588
    print('same-type pairs found:', len(b588['same_type_pairs']))
    print('xor violations (no cross higher):', len(b588['xor_violations']))
    print('xor ok (no cross higher):', b588['without_cross_higher_xor_ok'])

    print()
    print('=== B585: shared shielding cost comparison ===')
    b585 = {
        'two_comp_costs': [],
        'single_comp_min_cost': {},
        'savings': [],
        'note': None,
    }
    # For each abstract type (path/cycle m), find min |S| realizing it as a single component residual
    # and min |S| realizing two copies as 2-component residual.
    # Scan n=4,5 all safe, n=6 sample.
    min_single = {}  # type -> min |S|
    min_double = {}  # (type,type) -> min |S|  (same type two comps)
    min_double_mixed = {}  # (t0,t1) -> min |S|

    for n in (4,):
        board = board_square(n)
        grundy = solve_grundy_small(board)
        max_sz = 8
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
            sz = occ.bit_count()
            types = [abstract_type(c, edges) for c in comps]
            # single-component residuals
            if len(comps) == 1:
                t = types[0]
                if t[0] in ('path', 'cycle'):
                    if t not in min_single or sz < min_single[t]:
                        min_single[t] = sz
            elif len(comps) == 2:
                key = tuple(sorted([types[0], types[1]], key=str))
                # only if both are path/cycle
                if types[0][0] in ('path', 'cycle') and types[1][0] in ('path', 'cycle'):
                    if key not in min_double_mixed or sz < min_double_mixed[key]:
                        min_double_mixed[key] = sz
                        b585['two_comp_costs'].append({
                            'n': n, 'S_size': sz, 'types': list(key),
                            'S_pts': [board.points[i] for i in range(board.V) if (occ >> i) & 1],
                        })
                    if types[0] == types[1]:
                        t = types[0]
                        if t not in min_double or sz < min_double[t]:
                            min_double[t] = sz

    b585['single_comp_min_cost'] = {str(k): v for k, v in sorted(min_single.items(), key=str)}
    b585['double_comp_min_cost'] = {str(k): v for k, v in sorted(min_double.items(), key=str)}
    b585['double_mixed_min_cost'] = {str(k): v for k, v in sorted(min_double_mixed.items(), key=str)}

    # savings: min_double[t] vs 2*min_single[t]
    for t, dbl in min_double.items():
        sgl = min_single.get(t)
        if sgl is not None:
            savings = 2 * sgl - dbl
            b585['savings'].append({
                'type': str(t), 'single_min': sgl, 'double_min': dbl,
                'sum_singles': 2 * sgl, 'saving': savings,
            })

    print('single min costs:', b585['single_comp_min_cost'])
    print('double (same type) min costs:', b585['double_comp_min_cost'])
    print('savings:', b585['savings'])
    out['b585'] = b585

    # save
    outpath = Path('research/verification/round5_b551_b600.json')
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2, default=str, ensure_ascii=False)
    print()
    print('saved to', outpath)


if __name__ == '__main__':
    main()
