import sys
sys.path.insert(0, 'research/verification/scripts')
from round3_chunk4_core import *
import numpy as np

n = 3
q = quad_masks(n)
s = Solve(q, n * n)
st = s.states
K = len(s.levels) - 1

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


# check edge_child[k] really holds positions within level k+1
for k in range(K):
    lv_next = set(s.levels[k + 1].tolist())
    lv_next_pos = set(range(len(s.levels[k + 1])))
    cvals = set(s.edge_child[k].tolist())
    in_glob = len(cvals & lv_next) / len(cvals)
    in_pos = len(cvals & lv_next_pos) / len(cvals)
    print(f'level {k}: childvals in global-set {in_glob:.2f}, in pos-set {in_pos:.2f}')
    pv = set(s.edge_parent[k].tolist())
    lv_p = set(s.levels[k].tolist())
    lvp_pos = set(range(len(s.levels[k])))
    print(f'         parentvals in global-set {len(pv & lv_p)/len(pv):.2f}, in pos-set {len(pv & lvp_pos)/len(pv):.2f}')
