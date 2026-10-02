#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Independently verify a cover witness produced by dfpn_cover_witness.py.

Recomputes the legal canonical s4 classes from the game rules and
checks the emitted certificate:
  (a) the witness uses the claimed number of classes
  (b) every class in it is one of the legal canonical s4 classes
  (c) the union of their coverage is all 119 third-move vertices
  (d) every listed coverage set equals the recomputed coverage for that
      class, so the certificate cannot overstate what a class covers
  (e) the known-proved LOSS class {1,2,11,22} is present

Deliberately does NOT reuse the witness script's own helpers beyond the
game rules, so a bug in the search does not propagate into the check.
"""
import collections
import io
import json
import sys

N = 11
V = N * N
FIRST, R2 = 60, 0
KNOWN_LOSS_COVERAGE = frozenset((1, 2, 11, 22))

CERT = sys.argv[1] if len(sys.argv) > 1 else \
    '/mnt/d/ghq/build11/logs/coveropt/cert_cover.json'


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
verts = set(legal_after(base))
edge_set = set()
for a in verts:
    for b in legal_after(base | {a}):
        if a != b:
            edge_set.add((min(a, b), max(a, b)))

classes = collections.defaultdict(set)
for (a, b) in sorted(edge_set):
    classes[d4_canonical([FIRST, R2, a, b])].update((a, b))
cov_of_key = {k: frozenset(v) for k, v in classes.items()}

cert = json.load(open(CERT, encoding='utf-8'))
witness = [tuple(sorted(c['key'])) for c in cert['classes']]
fail = 0

print('recomputed : %d vertices, %d classes' % (len(verts), len(classes)))
print('witness    : %d classes (claim %d)'
      % (len(witness), cert['n_classes']))

# (a) count
if len(witness) != cert['n_classes']:
    print('  FAIL (a) class count mismatch')
    fail = 1
else:
    print('  OK   (a) class count = %d' % len(witness))

# (b)+(d) each key legal and coverage exact
bad_key = bad_cov = 0
for k, c in zip(witness, cert['classes']):
    if k not in cov_of_key:
        bad_key += 1
        continue
    if sorted(cov_of_key[k]) != sorted(c['coverage']):
        bad_cov += 1
print('  %s (b) all keys are legal canonical s4 classes'
      % ('OK  ' if bad_key == 0 else 'FAIL'))
print('  %s (d) all coverage sets match the recomputation'
      % ('OK  ' if bad_cov == 0 else 'FAIL'))
if bad_key or bad_cov:
    fail = 1

# (c) union covers everything
union = set()
for c in cert['classes']:
    union |= set(c['coverage'])
missing = sorted(verts - union)
extra = sorted(union - verts)
print('  %s (c) union covers all %d vertices (missing %d, spurious %d)'
      % ('OK  ' if not missing and not extra else 'FAIL',
         len(verts), len(missing), len(extra)))
if missing or extra:
    fail = 1

# (e) known proved class present
has_known = any(frozenset(c['coverage']) == KNOWN_LOSS_COVERAGE
                for c in cert['classes'])
print('  %s (e) known-proved LOSS class present'
      % ('OK  ' if has_known else 'FAIL'))
if not has_known:
    fail = 1

lb = cert['counting_lower_bound']
print()
print('certified bounds : %d <= OPT <= %d' % (lb, len(witness)))
print('VERIFIED' if not fail else 'VERIFY_FAILED')
sys.exit(1 if fail else 0)