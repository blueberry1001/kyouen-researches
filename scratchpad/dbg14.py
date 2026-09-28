import sys
sys.path.insert(0, 'research/verification/scripts')
from round3_chunk4_core import *
import numpy as np

n = 3
q = quad_masks(n)
s = Solve(q, n * n)
K = len(s.levels) - 1
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
    print(f'k={k} n_k={n_k} sum(hasP)={int(hasP.sum())}')

out = np.zeros(s.N, dtype=bool)
for k in range(K + 1):
    out[s.levels[k]] = isN[k]
print('g0 N?', bool(out[0]), '(n=3 should be N, g=1)')
