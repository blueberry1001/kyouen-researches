import sys
sys.path.insert(0, 'research/verification/scripts')
from round3_chunk4_core import *

n = 3
q = quad_masks(n)
s = Solve(q, n * n)
st = s.states

# exact g for n=3 by pure recursion
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


print('n=3 g(0) =', g(0), '  PROTOCOL says g=1 for n=3')
print('n=3 g(1) =', g(1))
print('max g =', max(memo.values()))
