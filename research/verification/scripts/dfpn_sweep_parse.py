#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse a shared-TT center20 sweep into a tidy per-(round, reply) table.

Reads the two output streams the solver actually writes:
  * [done] ... WIN/LOSS   -> the LOG  stream
  * # [...] TIMEOUT ...   -> the CSV  stream
(see dfpn_center20.sh for why these are different streams.)

Both streams list the roots in the order the solver processed them, which
is the order of the roots csv, so the i-th entry of each stream belongs to
the i-th root. We therefore walk both streams in lockstep rather than
trying to match individual replies by text.
"""
import io
import re
import sys

DONE = re.compile(r'\[done\]\s+\[roots\{60,(\d+)\}\]\s+(WIN|LOSS)\b'
                  r'.*?expansions=(\d+)'
                  r'.*?root_pn=(\d+)\s+root_dn=(\d+)')
TIMEOUT = re.compile(r'\[roots\{60,(\d+)\}\]\s+TIMEOUT'
                     r'.*?expansions=(\d+)'
                     r'.*?visited=(\d+)'
                     r'.*?root_pn=(\d+)\s+root_dn=(\d+)'
                     r'.*?solved=(\d+)')


def parse(path):
    out = []
    if not path:
        return out
    try:
        txt = io.open(path, encoding='utf-8', errors='replace').read()
    except IOError:
        return out
    for line in txt.splitlines():
        m = DONE.search(line)
        if m:
            r, oc, ex, pn, dn = m.groups()
            out.append(dict(reply=int(r), outcome=oc, pn=int(pn),
                            dn=int(dn), expansions=int(ex), solved='-'))
            continue
        m = TIMEOUT.search(line)
        if m:
            r, ex, _vis, pn, dn, sv = m.groups()
            out.append(dict(reply=int(r), outcome='TIMEOUT', pn=int(pn),
                            dn=int(dn), expansions=int(ex), solved=int(sv)))
    return out


def main():
    log, csv, replies, rounds = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
    rl = [int(x) for x in replies.split(',')]

    dones = parse(log)
    tos = parse(csv)
    print('log [done] entries : %d' % len(dones))
    print('csv TIMEOUT entries: %d' % len(tos))

    n = len(rl) * rounds
    rows = []
    for i in range(n):
        r = rl[i % len(rl)]
        rnd = i // len(rl) + 1
        d = dones[i] if i < len(dones) else None
        t = tos[i] if i < len(tos) else None
        if d:
            rows.append((rnd, r, d['outcome'], d['pn'], d['dn'],
                         d['expansions'], d['solved']))
        elif t:
            rows.append((rnd, r, 'TIMEOUT', t['pn'], t['dn'],
                         t['expansions'], t['solved']))
        else:
            rows.append((rnd, r, 'MISSING', '-', '-', '-', '-'))
        # sanity: the reply the stream claimed must match the schedule
        src = d or t
        if src and src['reply'] != r:
            print('WARNING: slot %d expected reply %d but stream says %d'
                  % (i, r, src['reply']))

    print()
    print('round\treply\toutcome\tpn\tdn\texpansions\tsolved')
    for row in rows:
        print('\t'.join(str(x) for x in row))
    print()
    for rnd in range(1, rounds + 1):
        sub = [x for x in rows if x[0] == rnd]
        w = sum(1 for x in sub if x[2] == 'WIN')
        l = sum(1 for x in sub if x[2] == 'LOSS')
        t = sum(1 for x in sub if x[2] == 'TIMEOUT')
        m = sum(1 for x in sub if x[2] == 'MISSING')
        print('round=%d WIN=%d LOSS=%d TIMEOUT=%d MISSING=%d' % (rnd, w, l, t, m))


if __name__ == '__main__':
    main()
