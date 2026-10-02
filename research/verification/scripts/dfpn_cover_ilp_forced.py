#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Optimal cover WITH the already-proved {60,0,1,2} class forced in.

The plain ILP found an optimum of 31 that does NOT contain the class we
already proved. That is allowed -- it is a different 31-class solution --
but for a refutation certificate we want the proved class reused, so
that work already spent counts. This fixes x_K = 1 and re-optimises, to
check whether the optimum is still 31 when the known class is
mandatory, as claimed.
"""
import collections
import json
import os
import sys
import time

import numpy as np
from scipy.optimize import LinearConstraint, milp, Bounds
from scipy.sparse import csc_matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    'dfpn_cover_ilp.py'), encoding='utf-8').read()
head = src.split("keys = sorted(classes)")[0]
ns = {}
exec(compile(head, 'ilp', 'exec'), ns)

legal_after = ns['legal_after']
d4_canonical = ns['d4_canonical']
N, V, FIRST, R2 = ns['N'], ns['V'], ns['FIRST'], ns['R2']

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

# The proved class, identified by COVERAGE (implementation independent).
KNOWN_COV = frozenset((1, 2, 11, 22))
known_keys = [k for k, c in classes.items() if frozenset(c) == KNOWN_COV]
print('classes matching the proved coverage: %d' % len(known_keys))
known = sorted(known_keys)[0]

keys = sorted(classes)
M = len(keys)
ki = keys.index(known)
vidx = {v: i for i, v in enumerate(verts)}

rows, cols = [], []
for j, k in enumerate(keys):
    for v in classes[k]:
        rows.append(vidx[v])
        cols.append(j)
A = csc_matrix((np.ones(len(rows)), (rows, cols)),
               shape=(len(verts), M))
# Cover constraints, and x_known = 1.
cons = [
    LinearConstraint(A, lb=np.ones(len(verts)), ub=np.full(len(verts), np.inf)),
    LinearConstraint(csc_matrix(([1.0], ([ki], [0])), shape=(1, M)),
                     lb=np.array([1.0]), ub=np.array([1.0])),
]

t0 = time.time()
res = milp(c=np.ones(M), constraints=cons, integrality=np.ones(M),
           bounds=Bounds(0, 1),
           options={'time_limit': float(os.environ.get('ILP_TIME', '900')),
                    'presolve': True, 'mip_rel_gap': 0.0})
dt = time.time() - t0
print('status=%s wall=%.2fs objective=%s gap=%s'
      % (res.status, dt, res.fun,
         getattr(res, 'mip_gap', 'n/a')))

if res.x is None:
    print('NO SOLUTION')
    sys.exit(1)

sel = [i for i in range(M) if res.x[i] > 0.5]
union = set()
for i in sel:
    union |= set(classes[keys[i]])
print('selected=%d union=%d/%d  known present=%s'
      % (len(sel), len(union), len(verts), ki in sel))
sizes = collections.Counter(len(classes[keys[i]]) for i in sel)
print('coverage sizes: %s'
      % ' '.join('%dx%d' % (s, sizes[s]) for s in sorted(sizes)))

out = {
    'note': 'ILP optimum with the proved class forced in',
    'solver_status': str(res.status),
    'objective': float(res.fun) if res.fun is not None else None,
    'wall_s': round(dt, 2),
    'first_move': FIRST, 'r2': R2,
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
path = '/mnt/d/ghq/build11/logs/coveropt/cert_cover_ilp_forced.json'
with open(path, 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=1)
print('wrote', path)
print('OPTIMUM_WITH_KNOWN = %d (status %s)' % (len(sel), res.status))