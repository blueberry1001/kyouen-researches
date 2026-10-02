#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Independent checker for the s4 edge classes of a two-stone reply.

The C++ rule for an illegal four is NOT collinearity. build_forbidden_
quadruples() tests a 4x4 determinant built from the rows

    [ x*x + y*y,  x,  y,  1 ]

which is the concyclic determinant: it vanishes exactly when the four
points lie on one circle (a line counts as a circle of infinite
radius, so collinear quadruples are included). An earlier version of
this checker only tested collinearity, which is strictly weaker: it
reported 6985 edges where the solver reports 6894. {0,5,55,60} is not
collinear but is concyclic, and the solver correctly rejects it.

This module reimplements that determinant from scratch rather than
reusing the solver, so the counts below are an independent check.
"""
import collections

N = 11
V = N * N


def pt(v):
    return (v % N, v // N)


def det3(m):
    return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))


def forbidden(a, b, c, d):
    """Same 4x4 determinant as the solver: four concyclic points."""
    ids = [a, b, c, d]
    rows = []
    for r in ids:
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


def has_forbidden_quad(pts):
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
    """Legal moves after occ under the game's concyclic rule."""
    out = []
    for v in range(V):
        if v in occ:
            continue
        if has_forbidden_quad(sorted(occ | {v})):
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


FIRST, R2 = 60, 0
base = {FIRST, R2}
verts = legal_after(base)
all_pairs = len(verts) * (len(verts) - 1) // 2

edge_set = set()
for a in verts:
    for b in legal_after(base | {a}):
        if b == a:
            continue
        edge_set.add((min(a, b), max(a, b)))

classes = collections.defaultdict(set)
raw_edges = collections.defaultdict(list)
for (a, b) in sorted(edge_set):
    key = d4_canonical([FIRST, R2, a, b])
    classes[key].update((a, b))
    raw_edges[key].append((a, b))

print('vertices                     : %d' % len(verts))
print('all pairs                    : %d' % all_pairs)
print('safe edges                   : %d' % len(edge_set))
print('unsafe pairs rejected        : %d' % (all_pairs - len(edge_set)))
print('canonical s4 classes         : %d' % len(classes))
hist = collections.Counter(len(v) for v in classes.values())
print('coverage histogram           : %s'
      % ' '.join('cov%d=%d' % (k, hist[k]) for k in sorted(hist)))
mx = max(len(v) for v in classes.values())
print('max coverage                 : %d' % mx)
print('lower bound ceil(119/%d)      : %d' % (mx, -(-len(verts) // mx)))

# The class that the proved cache covers, for cross-checking the solver.
print()
for key in sorted(classes, key=lambda k: -len(classes[k]))[:3]:
    print('class %s covers %d: %s'
          % (str(key), len(classes[key]), sorted(classes[key])))
    print('  raw edges: %s' % sorted(raw_edges[key]))