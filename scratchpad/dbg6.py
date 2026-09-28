import sys
sys.path.insert(0, 'research/verification/scripts')
from round3_chunk4_core import *
import numpy as np

n = 3
q = quad_masks(n)
s = Solve(q, n * n)
st = s.states
idx = s.idx
K = len(s.levels) - 1

# manual level-by-level with plain python sets
pnset = {}
for k in range(K, -1, -1):
    for i in s.levels[k]:
        occ = st[i]
        mv = s.legal_mask(occ)
        isN = False
        m = mv
        v = 0
        while m:
            if m & 1:
                if pnset.get(occ | (1 << v), 0) == 0:
                    isN = True
            m >>= 1
            v += 1
        pnset[occ] = 1 if isN else 0
print('py: g0 N?', pnset[0], ' state1 N?', pnset[1])
pn = s.pn()
mis = [st[i] for i in range(len(st)) if bool(pn[i]) != (pnset[st[i]] == 1)]
print('mismatches', len(mis), mis[:10])
