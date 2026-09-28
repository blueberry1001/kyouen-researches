import sys
sys.path.insert(0, 'research/verification/scripts')
from round3_chunk4_core import *
import numpy as np

n = 3
q = quad_masks(n)
s = Solve(q, n * n)
st = s.states
K = len(s.levels) - 1
print('K', K, 'levels sizes', [len(lv) for lv in s.levels])

# check: for level k, edge_child[k] children all in levels[k+1]?
for k in range(K):
    lv = s.levels[k + 1]
    sset = set(lv.tolist())
    bad = [c for c in s.edge_child[k].tolist() if c not in sset]
    if bad:
        print('level', k, 'child out of range', bad[:5])
        break
else:
    print('all child indices valid')

# check parents
for k in range(K):
    lv = s.levels[k]
    sset = set(lv.tolist())
    bad = [p for p in s.edge_parent[k].tolist() if p not in sset]
    if bad:
        print('level', k, 'parent out of range', bad[:5])
        break
else:
    print('all parent indices valid')

# Now: number of edges per level vs expected = sum of children counts
for k in range(K):
    exp = sum(len(s.children[int(i)]) for i in s.levels[k])
    got = len(s.edge_parent[k])
    print('level', k, 'edges exp', exp, 'got', got)
