#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Solve the s4 edge-class set cover exactly as a 0-1 ILP.

    min  sum_C x_C
    s.t. for all v:  sum_{C containing v} x_C >= 1
         x_C in {0,1}

3396 binary variables, 119 covering constraints, solved with HiGHS via
scipy.optimize.milp. On success the selected classes are written to
cert_cover_ilp.json in the same schema dfpn_cover_verify.py checks, so
the optimum is verified by the same independent recomputation that
verified the greedy witness.

If the solver times out or returns no certificate, the incumbent and its
bound are reported so the interval can be narrowed honestly.
"""
import collections
import io
import json
import os
import sys
import time

import numpy as np
from scipy.optimize import LinearConstraint, milp, Bounds
from scipy.sparse import csc_matrix

N = 11
V = N * N
FIRST, R2 = 60, 0
OUT = '/mnt/d/ghq/build11/logs/coveropt'


def pt(v):
    return (v % N, v // N)


def det3(m):
    return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))


def forbidden(a, b, c, d):
    rows = []
    for r in (a, b, c, d):
        x, y = pt(r)
        rows.append([x * x + y * y, x, y, 1])
    det = 0
    for col in range(4):
        z = [[0] * 3 for _ in range(3)]
        rr = 0
        for r in range(1, 4):
            cc = 0
            for c2 in range(4):
                if c2 == col:
                    continue
                z[rr][cc] = rows[r][c2]
                cc += 1
            rr += 1
        det += (1 if col % 2 == 0 else -1) * rows[0][col] * det3(z)
    return det == 0


def has_quad(pts):
    s = sorted(pts)
    n = len(s)
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                for l in range(k + 1, n):
                    if forbidden(s[i], s[j], s[k], s[l]):
                        return True
    return False


def legal_after(occ):
    out = []
    for v in range(V):
        if v in occ:
            continue
        if has_quad(sorted(occ | {v})):
            continue
        out.append(v)
    return out


def d4_canonical(pts):
    imgs = set()
    for refl in (0, 1):
        for rot in range(4):
            got = []
            for v in pts:
                x, y = pt(v)
                if refl:
                    y = N - 1 - y
                for _ in range(rot):
                    x, y = y, N - 1 - x
                got.append(y * N + x)
            imgs.add(tuple(sorted(got)))
    return min(imgs)


base = {FIRST, R2}
verts = sorted(legal_after(base))
edge_set = set()
for a in verts:
    for b in legal_after(base | {a}):
        if a != b:
            edge_set.add((min(a, b), max(a, b)))

classes = collections.defaultdict(set)
raw = collections.defaultdict(list)
for (a, b) in sorted(edge_set):
    key = d4_canonical([FIRST, R2, a, b])
    classes[key].update((a, b))
    raw[key].append((a, b))

keys = sorted(classes)
M = len(keys)
vidx = {v: i for i, v in enumerate(verts)}
print('vertices=%d classes=%d maxcov=%d'
      % (len(verts), M, max(len(c) for c in classes.values())))
sys.stdout.flush()

rows, cols = [], []
for j, k in enumerate(keys):
    for v in classes[k]:
        rows.append(vidx[v])
        cols.append(j)
A = csc_matrix((np.ones(len(rows)), (rows, cols)),
               shape=(len(verts), M))
cons = LinearConstraint(A, lb=np.ones(len(verts)), ub=np.full(len(verts), np.inf))
c = np.ones(M)

TIME = float(os.environ.get('ILP_TIME', '900'))
t0 = time.time()
res = milp(c=c, constraints=cons, integrality=np.ones(M),
           bounds=Bounds(0, 1),
           options={'time_limit': TIME, 'presolve': True,
                    'mip_rel_gap': 0.0})
dt = time.time() - t0
print('status=%s  wall=%.1fs' % (res.status, dt))
print('objective =', res.fun)
print('mip gap    =', res.mip_gap if hasattr(res, 'mip_gap') else 'n/a')
sys.stdout.flush()

if res.x is None:
    print('NO SOLUTION RETURNED; nothing certified')
    sys.exit(1)

sel = [i for i in range(M) if res.x[i] > 0.5]
print('selected classes = %d' % len(sel))
union = set()
for i in sel:
    union |= set(classes[keys[i]])
print('union covers %d/%d vertices' % (len(union), len(verts)))
sizes = collections.Counter(len(classes[keys[i]]) for i in sel)
print('coverage sizes: %s'
      % ' '.join('%dx%d' % (s, sizes[s]) for s in sorted(sizes)))

out = {
    'note': 'ILP optimum via HiGHS; verify with dfpn_cover_verify.py',
    'solver_status': str(res.status),
    'solver_message': str(res.message),
    'objective': float(res.fun) if res.fun is not None else None,
    'mip_gap': float(res.mip_gap) if hasattr(res, 'mip_gap') else None,
    'wall_s': round(dt, 1),
    'first_move': FIRST,
    'r2': R2,
    'n_vertices': len(verts),
    'n_classes': len(sel),
    'counting_lower_bound': -(-len(verts) // max(len(c) for c in classes.values())),
    'classes': [
        {'key': list(keys[i]),
         'coverage': sorted(classes[keys[i]]),
         'coverage_size': len(classes[keys[i]]),
         'raw_edges': sorted(raw[keys[i]])}
        for i in sel
    ],
}
os.makedirs(OUT, exist_ok=True)
path = OUT + '/cert_cover_ilp.json'
with open(path, 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=1)
print('wrote', path)
if res.status == 0:
    print('OPTIMUM CERTIFIED = %d' % len(sel))
else:
    print('NOT proven optimal (status %s); incumbent %d' % (res.status, len(sel)))