import sys
sys.path.insert(0, 'research/verification/scripts')
from round3_chunk4_core import *

n = 3
q = quad_masks(n)
s = Solve(q, n * n)
st = s.states
pn = s.pn()

# find a mismatch and inspect
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


for i in range(len(st)):
    b = ev(st[i]) == 1
    if b != bool(pn[i]):
        occ = st[i]
        print('mismatch state', occ, 'brute N', b, 'vec N', bool(pn[i]))
        mv = s.legal_mask(occ)
        kids = s.children[i]
        print('  legalmask', bin(mv), 'nchildren', len(kids), 'true_legal', bin(mv).count('1'))
        print('  child states bitcounts', [bin(st[j]).count('1') for j in kids])
        for j in kids:
            print('   child', st[j], 'brute N', ev(st[j]) == 1, 'vec', bool(pn[j]))
        break
