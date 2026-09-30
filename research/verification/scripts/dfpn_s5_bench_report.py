#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Summarise the s5 / s6 exact-replay benchmark across budgets.

Per root: at which node budget (if any) does it close, and with what
result. Node counts here are the exact solver's own nodes for that
position in isolation, which is the quantity move-ordering work can be
graded against.

result: 0 UNKNOWN (budget exhausted), 1 WIN, 2 LOSS.
"""
import collections
import glob
import io
import os
import re
import sys

BUDGETS = [200000, 500000, 1000000, 2000000, 5000000, 10000000]


def load(path):
    out = {}
    for line in io.open(path, encoding='utf-8', errors='replace'):
        line = line.strip()
        if not line.startswith('replay,'):
            continue
        f = line.split(',')
        if len(f) < 11:
            continue
        try:
            key = (int(f[9]), int(f[10]))
            out[key] = dict(id=int(f[1]), stones=int(f[2]), legal=int(f[3]),
                            budget=int(f[5]), result=int(f[6]),
                            nodes=int(f[7]), wall=int(f[8]))
        except (ValueError, IndexError):
            continue
    return out


def main():
    pattern = sys.argv[1] if len(sys.argv) > 1 else '/mnt/d/ghq/build11/s5_b*.csv'
    per_budget = {}
    for p in sorted(glob.glob(pattern)):
        m = re.search(r'_b(\d+)\.csv$', p)
        if not m:
            continue
        b = int(m.group(1))
        per_budget[b] = load(p)
    if not per_budget:
        print('no benchmark files matched', pattern)
        return
    print('budgets present:', sorted(per_budget))
    allkeys = sorted(set().union(*[set(v) for v in per_budget.values()]))
    print('distinct roots : %d' % len(allkeys))

    print()
    print('%-6s %-6s %-9s %s' % ('id', 'stones', 'legal', '  '.join(
        '%-12s' % ('b=%d' % b) for b in sorted(per_budget))))
    solved_at = {}
    for k in allkeys:
        any_row = None
        for b in sorted(per_budget):
            if k in per_budget[b]:
                any_row = per_budget[b][k]
                break
        cells = []
        for b in sorted(per_budget):
            r = per_budget[b].get(k)
            if r is None:
                cells.append('%-12s' % '-')
            else:
                nm = {0: 'UNK', 1: 'WIN', 2: 'LOSS'}[r['result']]
                cells.append('%-12s' % ('%s %d' % (nm, r['nodes'])))
                if r['result'] in (1, 2) and k not in solved_at:
                    solved_at[k] = (b, r['result'], r['nodes'])
        print('%-6d %-6d %-9d %s' % (
            any_row['id'], any_row['stones'], any_row['legal'],
            '  '.join(cells)))

    print()
    print('SOLVED SUMMARY')
    for b in sorted(per_budget):
        n_win = sum(1 for r in per_budget[b].values() if r['result'] == 1)
        n_loss = sum(1 for r in per_budget[b].values() if r['result'] == 2)
        n_unk = sum(1 for r in per_budget[b].values() if r['result'] == 0)
        print('  budget=%-9d WIN=%-3d LOSS=%-3d UNKNOWN=%-3d' % (
            b, n_win, n_loss, n_unk))
    print()
    if solved_at:
        print('roots that closed, and at the smallest budget seen:')
        for k, (b, res, nodes) in sorted(solved_at.items(),
                                         key=lambda x: x[1][0]):
            print('  budget=%-9d %-4s nodes=%-9d key=%s' % (
                b, {1: 'WIN', 2: 'LOSS'}[res], nodes, k))
    else:
        print('NO ROOT CLOSED AT ANY BUDGET')


if __name__ == '__main__':
    main()