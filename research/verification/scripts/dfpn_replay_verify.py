#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Soundness check for --exact-replay: does the standalone replay agree
with the result the in-search handoff recorded for the same position?

This must be verified on a board where everything is known (n=6) before
any 11x11 replay number is trusted.

Record columns (after the '#' header):
  tag,seq,stones,key_lo,key_hi,legal,depth_from_root,is_or,retries,nodes,result
Replay columns:
  replay,id,stones,legal,is_or,budget,result,nodes,wall_s,key_lo,key_hi

Agreement is judged on (stones, key) -> result. Exact node counts are
NOT expected to match: inside the search the position inherits whatever
transposition entries already exist, while the replay starts cold. A
mismatch in result is a real defect; a mismatch in nodes is not.
"""
import collections
import io
import sys


def load_records(path):
    out = {}
    for line in io.open(path, encoding='utf-8', errors='replace'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        f = line.split(',')
        if len(f) < 11:
            continue
        try:
            key = (int(f[3]), int(f[4]))
            res = int(f[10])
            out[key] = (int(f[2]), int(f[5]), res, int(f[9]))
        except ValueError:
            continue
    return out


def load_replays(path):
    out = []
    for line in io.open(path, encoding='utf-8', errors='replace'):
        line = line.strip()
        if not line.startswith('replay,'):
            continue
        f = line.split(',')
        if len(f) < 10:
            continue
        try:
            # replay,id,stones,legal,is_or,budget,result,nodes,wall_s,lo,hi
            out.append((int(f[1]), int(f[2]), int(f[3]), int(f[6]),
                        int(f[7]), int(f[8]), int(f[9]), int(f[10])))
        except (ValueError, IndexError):
            continue
    return out


def main():
    rec = load_records(sys.argv[1])
    rep = load_replays(sys.argv[2])
    print('record keys      : %d' % len(rec))
    print('replay rows      : %d' % len(rep))

    agree = disagree = skipped = 0
    bad = []
    for row in rep:
        (rid, stones, legal, res, nodes, wall, lo, hi) = row
        key = (lo, hi)
        if key not in rec:
            skipped += 1
            continue
        rstones, rlegal, rres, rnodes = rec[key]
        if rstones != stones:
            bad.append(('stone mismatch', key, rstones, stones))
            disagree += 1
            continue
        if rres != res:
            bad.append(('result mismatch', key, 'rec=%d' % rres, 'rep=%d' % res))
            disagree += 1
            continue
        agree += 1
    print('agree            : %d' % agree)
    print('disagree         : %d' % disagree)
    print('not in record set: %d' % skipped)
    if bad:
        print()
        print('first mismatches:')
        for b in bad[:15]:
            print('  %s' % (b,))
    print('REPLAY_AGREE' if disagree == 0 else 'REPLAY_MISMATCH')


if __name__ == '__main__':
    main()