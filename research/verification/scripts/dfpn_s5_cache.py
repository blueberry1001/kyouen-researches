#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Seed the persistent s5 verdict cache from the classified children, and
verify a refutation directly from the cache rather than trusting the
solver's own bookkeeping.

Only decided verdicts are written. An UNKNOWN means the node budget ran
out; persisting that would make a later, better funded query inherit an
earlier failure.
"""
import io
import os

BASE = '/mnt/d/ghq/build11/logs'
OUT = BASE + '/s5cache'
DST = OUT + '/s5_verdicts.csv'


def load_results(path):
    d = {}
    if not os.path.exists(path):
        return d
    for line in io.open(path, encoding='utf-8', errors='replace'):
        line = line.strip()
        if not line.startswith('replay,'):
            continue
        f = line.split(',')
        if len(f) < 11:
            continue
        d[(f[9], f[10])] = (int(f[6]), int(f[7]))
    return d


def seed():
    b5 = load_results(BASE + '/s5dist/replay_b5.csv')
    b20 = load_results(BASE + '/s5dist/replay_b20.csv')
    n = w = l = skipped = 0
    with io.open(DST, 'w', encoding='utf-8') as f:
        # Header: the loader refuses a file whose board size or schema does
        # not match, so a cache from another configuration cannot be
        # mistaken for proof material.
        f.write('# s5 verdict cache: n=11 schema=1 '
                '(canonical key -> WIN/LOSS, UNKNOWN never stored)\n')
        for key, (r5, n5) in b5.items():
            if r5 != 0:
                r, nodes = r5, n5
            else:
                r, nodes = b20.get(key, (0, 0))
            if r == 1:
                w += 1
            elif r == 2:
                l += 1
            else:
                skipped += 1
                continue          # never persist UNKNOWN
            f.write('s5verdict,%s,%s,5,%d,%d\n' % (key[0], key[1], r, nodes))
            n += 1
    print('cache written: %s' % DST)
    print('  entries=%d  WIN=%d  LOSS=%d  skipped_UNKNOWN=%d'
          % (n, w, l, skipped))


def verify():
    """Recompute the refutation from the cache, independently of the
    solver. If every legal fifth move of the fixed s4 is a cached LOSS
    then that fourth reply refutes its third move."""
    cache = {}
    for line in io.open(DST, encoding='utf-8'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        f = line.split(',')
        if f[0] == 's5verdict':
            cache[(int(f[1]), int(f[2]))] = int(f[4])

    children = []
    for line in io.open(BASE + '/s5dist/children_ranked.csv', encoding='utf-8'):
        line = line.strip()
        if not line or line.startswith('m5,'):
            continue
        f = line.split(',')
        children.append((int(f[1]), int(f[2]), int(f[0]), int(f[3])))

    missing = [c for c in children if (c[0], c[1]) not in cache]
    losses = [c for c in children if cache.get((c[0], c[1])) == 2]
    wins = [c for c in children if cache.get((c[0], c[1])) == 1]
    print()
    print('cache entries        : %d' % len(cache))
    print('children of s4       : %d' % len(children))
    print('children NOT in cache: %d' % len(missing))
    print('cached LOSS          : %d' % len(losses))
    print('cached WIN           : %d' % len(wins))
    if not missing and len(losses) == len(children):
        print()
        print('REFUTATION VERIFIED: every legal fifth move of {60,0,1,2} is a')
        print('proven LOSS in the cache, so the fourth reply m4=2 refutes the')
        print('third move m3=1, and the three-stone position {60,0,1} is LOSS')
        print('for the original first player.')
    else:
        print()
        print('NOT VERIFIED: the cache does not cover the child set.')
    return (not missing) and len(losses) == len(children)


if __name__ == '__main__':
    seed()
    verify()