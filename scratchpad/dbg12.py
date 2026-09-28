import sys
sys.path.insert(0, 'research/verification/scripts')
from round3_chunk4_core import *
import numpy as np

n = 3
q = quad_masks(n)
s = Solve(q, n * n)
st = s.states
K = len(s.levels) - 1

# Manually: level 1 (bitcount 1), 9 states. All their children at level 2 are g=1 (N).
# So isN[1] should be all False.
# Build level-2 truth positions
lv2 = s.levels[2]
lv1 = s.levels[1]
# truth N at level 2: all True
isN2 = np.ones(len(lv2), dtype=bool)

cp = s.edge_child[1]
pp = s.edge_parent[1]
isP_child = ~isN2[cp]
hasP = np.zeros(len(lv1), dtype=bool)
hasP[pp[isP_child]] = True
print('isN[1] computed:', hasP)  # expect all False

# Now full pipeline
pn = s.pn()
print('pn at level1 globals:', [(int(i), bool(pn[i])) for i in lv1])
