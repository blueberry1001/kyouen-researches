#!/usr/bin/env python3
"""Quick n=5 scan: same-type 2-component residuals, esp. P_3 x P_3 for B587."""
from __future__ import annotations
import json, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import board_square
from residual_core import residual_R

def graph_components(nverts, edges):
    adj = [[] for _ in range(nverts)]
    for a, b in edges:
        adj[a].append(b); adj[b].append(a)
    seen = [False]*nverts
    comps = []
    for s in range(nverts):
        if seen[s]: continue
        stack = [s]; seen[s] = True; cur = []
        while stack:
            u = stack.pop(); cur.append(u)
            for w in adj[u]:
                if not seen[w]:
                    seen[w] = True; stack.append(w)
        comps.append(sorted(cur))
    return comps

def abstract_type(comp_verts, edges):
    vs = set(comp_verts)
    deg = {v: 0 for v in comp_verts}
    ecount = 0
    for a, b in edges:
        if a in vs and b in vs:
            deg[a] += 1; deg[b] += 1; ecount += 1
    m = len(comp_verts)
    if ecount == m-1 and all(d <= 2 for d in deg.values()) and sum(1 for d in deg.values() if d==1)==2:
        return ('path', m)
    if ecount == m and all(d == 2 for d in deg.values()):
        return ('cycle', m)
    return ('other', m)

# single g
def path_g(m):
    # independent set game on P_m
    from functools import lru_cache
    @lru_cache(maxsize=None)
    def ev(mask):
        moves = []
        for v in range(m):
            if (mask >> v) & 1: continue
            if v > 0 and (mask >> (v-1)) & 1: continue
            if v+1 < m and (mask >> (v+1)) & 1: continue
            moves.append(v)
        if not moves: return 0
        seen = set()
        for v in moves:
            seen.add(ev(mask | (1 << v)))
        g = 0
        while g in seen: g += 1
        return g
    return ev(0)

single = {('path', m): path_g(m) for m in range(1, 7)}
print('single g:', single)

n = 5
board = board_square(n)
print('n=5 quads:', len(board.quads))
grundy = board.solve_grundy()
print('safe states:', len(grundy))

results = []
max_sz = 5
count = 0
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
    if t0 != t1:
        continue
    if t0[0] not in ('path', 'cycle'):
        continue
    # cross higher
    s0, s1 = set(comps[0]), set(comps[1])
    cross = 0
    for r in higher:
        bits = set(i for i in range(board.V) if (r >> i) & 1)
        if bits & s0 and bits & s1:
            cross += 1
    g_total = grundy[occ]
    g_xor = single.get(t0, 0) ^ single.get(t1, 0) if t0[0]=='path' else None
    rec = {
        'S_size': occ.bit_count(),
        'type': str(t0),
        'g_total': g_total,
        'g_xor': g_xor,
        'cross': cross,
        'S_pts': [board.points[i] for i in range(board.V) if (occ >> i) & 1],
        'comps': [[board.points[v] for v in c] for c in comps],
    }
    results.append(rec)
    count += 1
    if t0 == ('path', 3):
        print('P3xP3:', rec)

print('same-type 2-comp found:', count)
mismatch = [r for r in results if r['g_xor'] is not None and r['g_total'] != r['g_xor']]
print('xor mismatches:', len(mismatch))
ok = [r for r in results if r['g_xor'] is not None and r['g_total'] == r['g_xor']]
print('xor ok:', len(ok))

# save
out = {'n5_same_type': results, 'n5_mismatch_count': len(mismatch), 'n5_ok_count': len(ok)}
# append to existing json
jpath = Path('research/verification/round5_b551_b600.json')
data = json.loads(jpath.read_text(encoding='utf-8'))
data['b588_n5_sample'] = out
jpath.write_text(json.dumps(data, indent=2, default=str, ensure_ascii=False), encoding='utf-8')
print('saved')
