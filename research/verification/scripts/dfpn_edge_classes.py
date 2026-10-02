#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check the unsafe-edge count and the canonical-s4-class breakdown.

An edge {a,b} for the reply {first,r2} is only meaningful if the
four-stone set {first,r2,a,b} is itself legal, i.e. contains no
collinear quadruple. The C++ classify_edge() only rejects repeated
stones, so it currently accepts illegal edges.

v = y*11 + x, and a quadruple is collinear iff the cross products of
two direction vectors against the first point vanish.
"""
import collections

N = 11
V = N * N


def pt(v):
    return (v % N, v // N)


def is_collinear(q):
    (ax, ay), (bx, by), (cx, cy), (dx, dy) = [pt(p) for p in q]
    return ((bx - ax) * (cy - ay) - (by - ay) * (cx - ax) == 0 and
            (bx - ax) * (dy - ay) - (by - ay) * (dx - ax) == 0)


def has_quad(pts):
    s = sorted(pts)
    n = len(s)
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                for l in range(k + 1, n):
                    if is_collinear((s[i], s[j], s[k], s[l])):
                        return True
    return False


def legal_after(occ):
    """Legal moves after occ, matching the game's rule."""
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


FIRST, R2 = 60, 0
base = {FIRST, R2}
verts = legal_after(base)
print('vertices (legal third moves): %d' % len(verts))
print('all pairs                  : %d' % (len(verts) * (len(verts) - 1) // 2))

# Build SAFE edges the way the fix will: for each m3=a, take the actual
# legal fourth replies, and register {min(a,b), max(a,b)}.
edge_set = set()
unsafe = 0
for a in verts:
    occ = base | {a}
    for b in legal_after(occ):
        if b == a:
            continue
        key = (min(a, b), max(a, b))
        if key in edge_set:
            continue
        s4 = [FIRST, R2, key[0], key[1]]
        if has_quad(sorted(s4)):
            unsafe += 1
            continue
        edge_set.add(key)

print('unsafe pairs rejected      : %d' % unsafe)
print('safe edges                 : %d' % len(edge_set))

# Canonical s4 classes over the safe edges, and how many third-move
# vertices each class covers.
classes = collections.defaultdict(set)
members = collections.defaultdict(list)
for (a, b) in sorted(edge_set):
    key = d4_canonical([FIRST, R2, a, b])
    classes[key].update((a, b))
    members[key].append((a, b))

print('canonical s4 classes       : %d' % len(classes))
hist = collections.Counter(len(v) for v in classes.values())
print('coverage histogram         : %s'
      % ' '.join('cov%d=%d' % (k, hist[k]) for k in sorted(hist)))
print('max coverage               : %d' % max(len(v) for v in classes.values()))
print('theoretical lower bound    : ceil(119/%d) = %d'
      % (max(len(v) for v in classes.values()),
         -(-119 // max(len(v) for v in classes.values()))))

for key in sorted(classes, key=lambda k: -len(classes[k]))[:3]:
    print()
    print('class %s covers %d: %s'
          % (str(key), len(classes[key]), sorted(classes[key])))
    print('  representative edges: %s' % sorted(members[key])[:6])