import sys
sys.path.insert(0, 'research/verification/scripts')
from round3_chunk4_core import *
import numpy as np

n = 3
q = quad_masks(n)
s = Solve(q, n * n)
lv1 = s.levels[1].tolist()
lv2 = s.levels[2].tolist()

# For the FIRST parent position 0 (global lv1[0]=1), its children should be 8 states in level 2
cp = s.edge_child[1]
pp = s.edge_parent[1]
first = [c for c, p in enumerate(cp.tolist()) if p == 0]
print('children positions of parent 0 (level1):', first)
print('these should be positions of globals:', [lv2[c] for c in first])
print('expected globals from s.children:', [s.states[j] for j in s.children[lv1[0]]])
