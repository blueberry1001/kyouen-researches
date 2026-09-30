#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyse a --exact-record CSV: how many handoff attempts, how many
UNIQUE canonical roots, and how many are repeats.

The question this answers is Phase 2 of the plan: if the 29 aborted s5
handoffs are 29 distinct positions, then a persistent exact cache or a
resume mechanism has little value. If instead a handful of s5 roots are
handed off over and over, those are worth making resumable.

Input columns (after the leading '#' comment header):
    tag,seq,stones,key_lo,key_hi,legal,depth_from_root,is_or,retries,nodes,result
result: 0=UNKNOWN(aborted) 1=WIN 2=LOSS
"""
import collections
import io
import sys


def load(path):
    rows = []
    for line in io.open(path, encoding='utf-8', errors='replace'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        f = line.split(',')
        if len(f) < 11:
            continue
        try:
            rows.append(dict(
                tag=f[0], seq=int(f[1]), stones=int(f[2]),
                key=(int(f[3]), int(f[4])), legal=int(f[5]),
                depth=int(f[6]), is_or=int(f[7]), retries=int(f[8]),
                nodes=int(f[9]), result=int(f[10])))
        except ValueError:
            continue
    return rows


RES = {0: 'UNKNOWN', 1: 'WIN', 2: 'LOSS'}


def report(rows, label):
    print('=' * 68)
    print('%s   attempts=%d' % (label, len(rows)))
    if not rows:
        print('  (none)')
        return

    by_stones = collections.defaultdict(list)
    for r in rows:
        by_stones[r['stones']].append(r)

    print()
    print('%-7s %7s %7s %8s %7s %7s  %-12s' % (
        'stones', 'calls', 'unique', 'repeats', 'maxrep', 'aborts',
        'win/loss/unk'))
    for s in sorted(by_stones):
        g = by_stones[s]
        keys = collections.Counter(r['key'] for r in g)
        unk = sum(1 for r in g if r['result'] == 0)
        win = sum(1 for r in g if r['result'] == 1)
        loss = sum(1 for r in g if r['result'] == 2)
        print('s%-6d %7d %7d %8d %7d %7d  %-12s' % (
            s, len(g), len(keys), len(g) - len(keys),
            max(keys.values()), unk, '%d/%d/%d' % (win, loss, unk)))

    # Focus on aborted roots only, since those are the bottleneck.
    unk_rows = [r for r in rows if r['result'] == 0]
    print()
    print('ABORTED handoffs: %d attempts' % len(unk_rows))
    if unk_rows:
        ak = collections.Counter(r['key'] for r in unk_rows)
        print('  unique aborted roots      : %d' % len(ak))
        print('  repeat attempts           : %d' % (len(unk_rows) - len(ak)))
        bys = collections.defaultdict(set)
        for r in unk_rows:
            bys[r['stones']].add(r['key'])
        for s in sorted(bys):
            print('    s%-3d unique aborted roots: %d' % (s, len(bys[s])))
        print('  most repeated aborted roots:')
        for k, c in ak.most_common(10):
            g = [r for r in unk_rows if r['key'] == k]
            print('    stones=%d legal=%d repeats=%d nodes(last)=%d' % (
                g[0]['stones'], g[0]['legal'], c, g[-1]['nodes']))


def main():
    for p in sys.argv[1:]:
        report(load(p), p.split('/')[-1])


if __name__ == '__main__':
    main()