#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exact minimum set cover over the canonical s4 classes of a reply.

The counting bound ceil(119/6)=20 is weak because coverage sets
overlap heavily. A plain branch-and-bound stalls because it has no
useful lower bound beyond "uncovered / max coverage".

This uses iterative deepening with a GREEDY-ADAPTIVE bound: at each
node, take the vertex with the fewest remaining options and lower-bound
by summing per-vertex 1/(max coverage over classes covering that
vertex). That bound is valid (a class of size k covers at most k
vertices, so it contributes at most k vertex-slots) and is far stronger
than dividing by the global max.

To keep it fast the candidate classes are pre-filtered: only classes
that cover some vertex are considered, and identical coverage sets are
merged (keeping one representative, which is all an optimal cover
needs).
"""
import collections
import sys

N = 11
V = N * N
FIRST, R2 = 60, 0


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
verts = legal_after(base)
edge_set = set()
for a in verts:
    for b in legal_after(base | {a}):
        if a != b:
            edge_set.add((min(a, b), max(a, b)))

classes = collections.defaultdict(set)
for (a, b) in sorted(edge_set):
    classes[d4_canonical([FIRST, R2, a, b])].update((a, b))

# Merge identical coverage sets: an optimal cover needs only one member.
by_cov = {}
for key, cov in classes.items():
    by_cov.setdefault(frozenset(cov), []).append(key)
covs = list(by_cov)
print('vertices          : %d' % len(verts))
print('classes           : %d' % len(classes))
print('distinct covers   : %d' % len(covs))
mx = max(len(c) for c in covs)
print('max coverage      : %d' % mx)
print('counting bound    : %d' % (-(-len(verts) // mx)))
sys.stdout.flush()

allv = frozenset(verts)
idx_of = collections.defaultdict(list)
for i, c in enumerate(covs):
    for v in c:
        idx_of[v].append(i)
maxcov_of_v = {v: max(len(covs[i]) for i in idx_of[v]) for v in allv}

# greedy upper bound
unc = set(allv)
greedy = []
while unc:
    c = max(covs, key=lambda c: len(c & unc))
    if not (c & unc):
        break
    greedy.append(c)
    unc -= c
print('greedy upper bound: %d' % len(greedy))
sys.stdout.flush()


def lower_bound(uncovered):
    """Valid bound, two independent charges added together.

    Charge A (fractional): a class of size k covers at most k
    uncovered vertices, so vertex v costs at least 1/maxcov(v).

    Charge B (disjointness): vertices whose covering class SETS are
    pairwise disjoint can never be covered by one class. Greedily pick
    such vertices and charge 1 each; this is what actually bites, since
    a few high-coverage vertices are covered by only a handful of
    classes while the bulk is heavily constrained.

    The two charges are combined with max(), NOT by addition. Adding
    two valid lower bounds is not valid: they can charge the same chosen
    class twice. Minimal counterexample -- one vertex, one class
    covering it: OPT = 1, fractional charge = 1, disjoint charge = 1,
    sum = 2, which exceeds the optimum. Since each charge on its own is
    a lower bound, their max is also a lower bound; the sum is not.
    """
    frac = 0.0
    for v in uncovered:
        frac += 1.0 / maxcov_of_v[v]

    # Charge B: greedy independent set over the "who can cover me"
    # sets, restricted to uncovered vertices.
    sets = []
    for v in uncovered:
        s = frozenset(i for i in idx_of.get(v, ())
                      if set(covs[i]) & uncovered)
        if s:
            sets.append(s)
    sets.sort(key=len)
    used = set()
    extra = 0
    for s in sets:
        if not (s & used):
            used |= s
            extra += 1
    return max(frac, float(extra))


nodes = [0]


def solve(uncovered, limit, chosen, best):
    nodes[0] += 1
    if not uncovered:
        best[0] = list(chosen)
        return True
    if len(chosen) >= limit:
        return False
    if lower_bound(uncovered) > limit - len(chosen) + 1e-9:
        return False
    v = min(uncovered, key=lambda u: len(idx_of.get(u, ())))
    for i in sorted(idx_of.get(v, ()),
                    key=lambda i: -len(covs[i] & uncovered)):
        c = covs[i]
        newu = uncovered - c
        if not (newu & c):
            chosen.append(i)
            if solve(newu, limit, chosen, best):
                return True
            chosen.pop()
    return False


best = [None, len(greedy)]
for limit in range(-(-len(verts) // mx), len(greedy)):
    print('  trying limit=%d (nodes so far %d)' % (limit, nodes[0]))
    sys.stdout.flush()
    nodes[0] = 0
    if solve(allv, limit, [], best):
        print('EXACT minimum = %d classes (search nodes %d)'
              % (len(best[0]), nodes[0]))
        break
else:
    print('no solution below greedy bound')
sys.stdout.flush()

if best[0]:
    sizes = collections.Counter(len(covs[i]) for i in best[0])
    print('coverage sizes: %s'
          % ' '.join('%dx%d' % (k, sizes[k]) for k in sorted(sizes)))
    seen = set()
    disjoint = True
    for i in best[0]:
        c = covs[i]
        if c & seen:
            disjoint = False
        seen |= c
    print('pairwise disjoint : %s' % disjoint)
    print('union size        : %d' % len(seen))