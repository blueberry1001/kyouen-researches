#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare the exact-DFS orderings over the fixed s5 benchmark.

Reads the ord_<mode>.csv files produced by
  dfpn --exact-replay=... --only=5 --exact-replay-budget=B \
        --exact-order=count|countd|key

Two things are checked:
  1. SOUNDNESS: every mode must return the same WIN/LOSS/UNKNOWN for
     every position. Ordering may change the work, never the result.
     If this fails the A/B is comparing different problems.
  2. WORK: total nodes over the whole benchmark set, which is the
     quantity an ordering change is meant to reduce.
"""
import io
import sys


def load(path):
    d = {}
    order = []
    for line in io.open(path, encoding='utf-8', errors='replace'):
        line = line.strip()
        if not line.startswith('replay,'):
            continue
        f = line.split(',')
        if len(f) < 11:
            continue
        key = (f[9], f[10])
        d[key] = dict(result=int(f[6]), nodes=int(f[7]), legal=int(f[3]))
        order.append(key)
    return d, order


def main():
    import os
    modes = {}
    for m in ('count', 'countd', 'key'):
        p = '/mnt/d/ghq/build11/ord_%s.csv' % m
        if not os.path.exists(p):
            continue
        got, _ = load(p)
        if got:
            modes[m] = got
    if not modes:
        print('no ordering results found')
        return
    base_name = 'count' if 'count' in modes else sorted(modes)[0]
    base = modes[base_name]
    keys = list(base)

    print('orderings with data: %s' % ', '.join(sorted(modes)))
    print('positions in benchmark: %d' % len(keys))
    print()
    print('%-5s %-6s %-6s %12s %12s %12s' % (
        'id', 'legal', 'result',
        'count' if base_name == 'count' else base_name,
        'count-desc', 'key-asc'))
    tot = dict.fromkeys(modes, 0)
    for k in keys:
        row = [modes[m].get(k, {}).get('nodes', -1) for m in modes]
        for m in modes:
            tot[m] += max(modes[m].get(k, {}).get('nodes', 0), 0)
        r = base[k]['result']
        print('%-5s %-6d %-6d %12d %12s %12s' % (
            k[0][-4:], base[k]['legal'], r, row[0],
            row[1] if len(row) > 1 else '-',
            row[2] if len(row) > 2 else '-'))
    print()
    print('TOTAL NODES over the benchmark set:')
    ta = tot.get(base_name, 0)
    for m in sorted(tot):
        delta = ''
        if m != base_name and ta:
            delta = '   %+.1f%% vs %s' % (100.0 * (tot[m] - ta) / ta, base_name)
        print('  %-12s : %12d%s' % (m, tot[m], delta))
    print()
    bad = []
    for k in keys:
        ra = base[k]['result']
        for m in modes:
            if m == base_name:
                continue
            r = modes[m].get(k, {}).get('result', -1)
            if r != ra:
                bad.append((k, m, ra, r))
    print('result mismatches vs %s: %d' % (base_name, len(bad)))
    for x in bad[:10]:
        print('   ', x)
    print('ORDER_SOUND' if not bad else 'ORDER_UNSOUND')


if __name__ == '__main__':
    main()