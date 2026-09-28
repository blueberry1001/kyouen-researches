import sys
sys.path.insert(0, 'research/verification/scripts')
from round3_chunk4_core import *
import numpy as np

n = 3
q = quad_masks(n)
s = Solve(q, n * n)
K = len(s.levels) - 1
print('K =', K, 'sizes', [len(lv) for lv in s.levels])
print('edge arrays len', [len(p) for p in s.edge_parent])
# edge_parent has K entries (levels 0..K-1). pn loops k in K..0 and uses edge_child[k]
# for k=K it `continue`s. for k=K-1 it uses edge_child[K-1] -> level K. correct.
# BUT: K = len(levels)-1 = 5. levels[5] is bitcount 5.
# edge_parent has 5 entries indexed 0..4. pn accesses edge_child[k] for k=0..4. correct.
print('OK structure')
