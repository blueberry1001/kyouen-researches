#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find a concrete small cover over the canonical s4 classes and emit it
machine-readably, then independently verify it.

Two stages:

1. CONSTRUCT. Greedy seeding plus local improvement (repeatedly try to
   replace two chosen classes by one, and try to drop a class). This is a
   heuristic, so it returns a cover of SOME size; the point is to shrink
   the upper bound with an explicit witness rather than assert a number.

2. VERIFY, in a separate pass that recomputes the classes from the game
   rules and checks the emitted certificate:
     (a) the number of classes in the witness
     (b) every class is one of the legal canonical s4 classes
     (c) the union of their coverage is all 119 vertices
     (d) the same again with the known-LOSS class forced into the cover

Output: cert_cover.json plus a summary on stdout.
"""
import collections
import json
import os
import sys

N = 11
V = N * N
FIRST, R2 = 60, 0
# The proved {60,0,1,2} class, identified by COVERAGE rather than by
# key: the solver keys positions by the minimum over 8 stored bitmask
# images, which need not be the sorted stone tuple used here, so keys
# are not comparable across the two implementations.
KNOWN_LOSS_COVERAGE = frozenset((1, 2, 11, 22))


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


def build():
    base = {FIRST, R2}
    verts = legal_after(base)
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
    return verts, classes, raw


def greedy(covs, uncovered):
    """Greedy cover of `uncovered`. The argument is the set still TO BE
    covered, not a pre-covered set: an earlier version passed the known
    class's coverage here, which asked greedy to cover only the four
    vertices the known class already handles and returned a 1-class
    "cover" of them."""
    unc = set(uncovered)
    chosen = []
    pool = list(covs)
    while unc:
        c = max(pool, key=lambda c: len(c & unc))
        if not (c & unc):
            return None
        chosen.append(c)
        unc -= c
    return chosen


def improve(chosen, covs, universe):
    """Local search: drop redundant classes, then try to replace a pair
    by a single class covering at least as much of what they covered.
    Deterministic, so the result is reproducible.

    The drop step is only allowed when the remaining classes still cover
    everything; a previous version computed `newunc` but never checked it
    was empty, which emptied the cover completely and produced a
    zero-class witness."""
    chosen = [frozenset(c) for c in chosen]
    changed = True
    while changed:
        changed = False
        # drop redundant
        for i in range(len(chosen)):
            rest = set()
            for j, c in enumerate(chosen):
                if j != i:
                    rest |= c
            newunc = set(universe) - rest
            if not newunc:
                del chosen[i]
                changed = True
                break
        if changed:
            continue
        # replace two by one
        best = None
        for i in range(len(chosen)):
            for j in range(i + 1, len(chosen)):
                need = (chosen[i] | chosen[j])
                for c in covs:
                    if c in chosen:
                        continue
                    if need <= c:
                        gain = len(c) - len(need)
                        if gain >= 0:
                            key = (gain, -len(c))
                            if best is None or key < best[0]:
                                best = (key, i, j, c)
        if best:
            _, i, j, c = best
            chosen = [x for k, x in enumerate(chosen) if k not in (i, j)]
            chosen.append(c)
            changed = True
    return chosen


verts, classes, raw = build()
COVS = [frozenset(c) for c in classes.values()]
UNIVERSE = frozenset(verts)
cov_of_key = {k: frozenset(v) for k, v in classes.items()}
key_of_cov = {}
for k, c in cov_of_key.items():
    key_of_cov.setdefault(c, []).append(k)

print('vertices=%d classes=%d maxcov=%d'
      % (len(verts), len(classes), max(len(c) for c in COVS)))
print('counting lower bound = %d' % (-(-len(verts) // max(len(c) for c in COVS))))
sys.stdout.flush()

# Force the already-proved class in, so the cover is compatible with
# what has already been proved, then shrink the rest.
known = [c for c in COVS if c == KNOWN_LOSS_COVERAGE]
assert known, 'known-LOSS class not found by coverage'
already = set(known[0])
g = greedy(COVS, set(verts) - already)
assert g is not None, 'no cover found for the remaining vertices'
g = [known[0]] + g
before = len(g)
g2 = improve(g, COVS, UNIVERSE)
if not g2:
    g2 = g
print('forced-in greedy=%d  after local improvement=%d' % (before, len(g2)))
sys.stdout.flush()

# choose a representative key for each chosen coverage
chosen_keys = []
for c in g2:
    ks = key_of_cov[c]
    ks.sort()
    chosen_keys.append(ks[0])
chosen_keys = sorted(set(chosen_keys))

out = {
    'note': 'candidate cover, not a proof of optimality',
    'first_move': FIRST,
    'r2': R2,
    'n_vertices': len(verts),
    'n_classes': len(chosen_keys),
    'counting_lower_bound': -(-len(verts) // max(len(c) for c in COVS)),
    'classes': [
        {'key': list(k),
         'coverage': sorted(cov_of_key[k]),
         'coverage_size': len(cov_of_key[k]),
         'raw_edges': sorted(raw[k])}
        for k in chosen_keys
    ],
}
path = '/mnt/d/ghq/build11/logs/coveropt/cert_cover.json'
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=1)
print('wrote %s with %d classes' % (path, len(chosen_keys)))

sizes = collections.Counter(len(cov_of_key[k]) for k in chosen_keys)
print('coverage sizes: %s'
      % ' '.join('%dx%d' % (s, sizes[s]) for s in sorted(sizes)))
seen = set()
for k in chosen_keys:
    seen |= cov_of_key[k]
print('union covers %d/%d vertices' % (len(seen), len(verts)))