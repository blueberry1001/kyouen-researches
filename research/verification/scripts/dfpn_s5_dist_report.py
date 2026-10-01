#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Summarise the fifth-move difficulty distribution.

Reads the ranked child table and one or more replay result files, then
reports, per budget stage, the WIN / LOSS / UNKNOWN split, the cheapest
WIN and cheapest LOSS in nodes, median and p90 node cost, and where the
cheapest WIN sits under each child ordering. The last number is the one
that decides whether ordering or difficulty is the problem: a cheap WIN
that the direct ordering would reach at rank 40 is an ordering problem,
while no cheap WIN at all means the position is simply hard.
"""
import collections
import io
import sys

TAB = '/mnt/d/ghq/build11/logs/s5dist/children_ranked.csv'
RES = {0: 'UNKNOWN', 1: 'WIN', 2: 'LOSS'}


def load_children():
    ch = {}
    order_direct = []
    for line in io.open(TAB, encoding='utf-8'):
        line = line.strip()
        if not line or line.startswith('m5,'):
            continue
        f = line.split(',')
        r = dict(m5=int(f[0]), lo=int(f[1]), hi=int(f[2]), legal=int(f[3]),
                 tt=int(f[4]), rank_direct=int(f[5]), rank_index=int(f[6]))
        ch[(r['lo'], r['hi'])] = r
        order_direct.append(r)
    return ch, order_direct


def load_result(path):
    """key -> (result, nodes, wall)"""
    out = {}
    for line in io.open(path, encoding='utf-8', errors='replace'):
        line = line.strip()
        if not line.startswith('replay,'):
            continue
        f = line.split(',')
        if len(f) < 11:
            continue
        out[(int(f[9]), int(f[10]))] = (int(f[6]), int(f[7]), int(f[8]))
    return out


def pct(xs, p):
    if not xs:
        return 0
    xs = sorted(xs)
    k = int(round((p / 100.0) * (len(xs) - 1)))
    return xs[k]


def report(path, ch, label):
    res = load_result(path)
    if not res:
        print('%s: no results' % label)
        return None
    rows = []
    for key, r in res.items():
        c = ch.get(key)
        if c is None:
            continue
        rows.append(dict(m5=c['m5'], legal=c['legal'],
                         rank_direct=c['rank_direct'],
                         rank_index=c['rank_index'],
                         result=r[0], nodes=r[1], wall=r[2]))
    cnt = collections.Counter(RES[r['result']] for r in rows)
    solved = [r for r in rows if r['result'] != 0]
    wins = [r for r in rows if r['result'] == 1]
    losses = [r for r in rows if r['result'] == 2]
    print('=== %s : %d children ===' % (label, len(rows)))
    print('  WIN=%d  LOSS=%d  UNKNOWN=%d'
          % (cnt['WIN'], cnt['LOSS'], cnt['UNKNOWN']))
    if solved:
        ns = [r['nodes'] for r in solved]
        print('  solved nodes: min=%d median=%d p90=%d max=%d'
              % (min(ns), pct(ns, 50), pct(ns, 90), max(ns)))
    if wins:
        w = min(wins, key=lambda r: r['nodes'])
        print('  cheapest WIN : m5=%d legal=%d nodes=%d '
              'rank_direct=%d rank_index=%d'
              % (w['m5'], w['legal'], w['nodes'], w['rank_direct'],
                 w['rank_index']))
    else:
        print('  cheapest WIN : NONE')
    if losses:
        l = min(losses, key=lambda r: r['nodes'])
        print('  cheapest LOSS: m5=%d legal=%d nodes=%d '
              'rank_direct=%d rank_index=%d'
              % (l['m5'], l['legal'], l['nodes'], l['rank_direct'],
                 l['rank_index']))
    else:
        print('  cheapest LOSS: NONE')
    print()
    return rows


def main():
    ch, _ = load_children()
    stages = [(a.split('=')[0], a.split('=')[1])
              for a in sys.argv[1:] if '=' in a]
    allrows = {}
    for label, path in stages:
        r = report(path, ch, label)
        if r:
            allrows[label] = r
    # Cross-stage: does anything the 5M stage called UNKNOWN close at 20M?
    labels = list(allrows)
    if len(labels) >= 2:
        a, b = labels[0], labels[1]
        ma = {(r['m5']): r for r in allrows[a]}
        mb = {(r['m5']): r for r in allrows[b]}
        newly = [k for k in mb
                 if k in ma and ma[k]['result'] == 0 and mb[k]['result'] != 0]
        print('=== %s -> %s ===' % (a, b))
        print('  children UNKNOWN at %s but solved at %s: %d'
              % (a, b, len(newly)))
        for k in sorted(newly):
            print('     m5=%-4d legal=%-4d -> %-7s nodes=%d '
                  'rank_direct=%d rank_index=%d'
                  % (k, mb[k]['legal'], RES[mb[k]['result']],
                     mb[k]['nodes'], mb[k]['rank_direct'],
                     mb[k]['rank_index']))


if __name__ == '__main__':
    main()