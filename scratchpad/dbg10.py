import sys
sys.path.insert(0, 'research/verification/scripts')
from round3_chunk4_core import *
import numpy as np

n = 3
q = quad_masks(n)
s = Solve(q, n * n)
st = s.states
K = len(s.levels) - 1

print('levels[1] =', s.levels[1].tolist())
print('state 1 global idx should be 1 (first child of 0)')
lv1 = s.levels[1].tolist()
print('position of state1 in level1 =', lv1.index(1))
# children of state 1
i1 = 1
print('state1 children globals =', [st[j] for j in s.children[i1]])
print('level2 members include them?',
      all(st[j] in lv1 for j in s.children[i1]))

# level-2 (bitcount 2) truth: all N?
# build truth via grundy
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


# level 2 (bitcount 2) all have g=1? then state1 is P (correct)
# But the vector said state1 is N. Look at level-1 computation:
# state1's children are in level 2. If all level2 states are N, hasP=False -> isN[1]=False -> state1 P. Correct!
# So the error must be that isN[2] (bitcount 2) is wrong.
# check a level-2 node
from collections import Counter
g2 = Counter()
for i in lv1:
    g2[bin(st[i]).count('1')] += 1
# iterate level 2
lv2 = s.levels[2].tolist()
print('level2 size', len(lv2))
c2 = Counter(g(st[i]) for i in lv2)
print('level2 grundy dist', c2)
lv3 = s.levels[3].tolist()
print('level3 grundy dist', Counter(g(st[i]) for i in lv3))
print('level1 grundy dist', Counter(g(st[i]) for i in lv1))
