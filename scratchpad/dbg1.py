import sys
sys.path.insert(0, 'research/verification/scripts')
from round3_chunk4_core import *

n = 3
q = quad_masks(n)
s = Solve(q, n * n)
print('nstates', len(s.states))

memo = {}


def ev(occ):
    if occ in memo:
        return memo[occ]
    mv = s.legal_mask(occ)
    if mv == 0:
        memo[occ] = 0
        return 0
    r = 0
    m = mv
    v = 0
    while m:
        if m & 1:
            if ev(occ | (1 << v)) == 0:
                r = 1
        m >>= 1
        v += 1
    memo[occ] = r
    return r


print('brute g0 P?', ev(0) == 0)
pn = s.pn()
print('vector g0N', bool(pn[0]))
bad = [s.states[i] for i in range(len(s.states)) if bool(pn[i]) != (ev(s.states[i]) == 1)]
print('mismatches', len(bad), bad[:5])
