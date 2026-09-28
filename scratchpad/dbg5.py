import sys
sys.path.insert(0, 'research/verification/scripts')
from round3_chunk4_core import *
import numpy as np

n = 3
q = quad_masks(n)
s = Solve(q, n * n)
pn = s.pn()
st = s.states
idx = s.idx

# state 1 -> index
i = idx[1]
print('idx of state 1 =', i, 'bitcount', bin(1).count('1'), 'level', [k for k, lv in enumerate(s.levels) if i in set(lv.tolist())])
# recompute pn manually bottom-up with plain python, compare
K = len(s.levels) - 1
pnpy = {}


def ev(occ):
    if occ in pnpy:
        return pnpy[occ]
    mv = s.legal_mask(occ)
    if mv == 0:
        pnpy[occ] = 0
        return 0
    r = 0
    m = mv
    v = 0
    while m:
        if m & 1:
            if ev(occ | (1 << v)) == 0:
                r = 1
        m >>= 1
        v += 1
    pnpy[occ] = r
    return r


ev(0)
mis = [st[i] for i in range(len(st)) if bool(pn[i]) != (pnpy[st[i]] == 1)]
print('mismatches', len(mis))
# check level assignment consistency
for k, lv in enumerate(s.levels):
    for i in lv:
        if st[i].bit_count() != k:
            print('LEVEL BUG', i, st[i], bin(st[i]).count('1'), k)
            break
print('edge counts', [len(p) for p in s.edge_parent])
