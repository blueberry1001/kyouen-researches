import sys
sys.path.insert(0, 'research/verification/scripts')
from round3_chunk4_core import *
import numpy as np

n = 3
q = quad_masks(n)
s = Solve(q, n * n)
st = s.states
K = len(s.levels) - 1

# recompute pn level by level, printing
isN = [None] * (K + 1)
for k in range(K, -1, -1):
    n_k = len(s.levels[k])
    if n_k == 0:
        isN[k] = np.zeros(0, dtype=bool)
        continue
    if k == K:
        isN[k] = np.zeros(n_k, dtype=bool)
        continue
    cp = s.edge_child[k]
    pp = s.edge_parent[k]
    ch = isN[k + 1]
    hasP = np.zeros(n_k, dtype=bool)
    if len(cp):
        isP_child = ~ch[cp]
        hasP[pp[isP_child]] = True
    isN[k] = hasP

# global reassembly
out = np.zeros(s.N, dtype=bool)
for k in range(K + 1):
    out[s.levels[k]] = isN[k]

# truth: exact grundy
sys.setrecursionlimit(100000)
memo = {}


def g(occ):
    if occ in memo:
        return memo[occ]
    mv = s.legal_mask(occ)
    if mv == 0:
        memo[occ] = 0
        return 0
    seen = set()
    m = mv
    v = 0
    while m:
        if m & 1:
            seen.add(g(occ | (1 << v)))
        m >>= 1
        v += 1
    x = 0
    while x in seen:
        x += 1
    memo[occ] = x
    return x


for i in range(s.N):
    truth = (g(st[i]) != 0)
    if bool(out[i]) != truth:
        print('MISMATCH state', st[i], 'bitcount', bin(st[i]).count('1'),
              'vec', bool(out[i]), 'truth', truth)
        break
else:
    print('all pn match')
