import sys
sys.path.insert(0, 'research/verification/scripts')
from round3_chunk4_core import *

n = 4
q = quad_masks(n)
s = Solve(q, n * n)
st = s.states
K = len(s.levels) - 1
print('K', K, 'level K size', len(s.levels[K]))
# do all level-K states have 0 children?
nolegal = sum(1 for i in s.levels[K] if len(s.children[int(i)]) == 0)
print('level-K states with zero children:', nolegal, '/', len(s.levels[K]))
# do any NON-top-level states have zero children?
for k in range(K):
    z = sum(1 for i in s.levels[k] if len(s.children[int(i)]) == 0)
    if z:
        print('level', k, 'zero-children states:', z, 'of', len(s.levels[k]))
