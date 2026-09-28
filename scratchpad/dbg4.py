import sys, itertools
sys.path.insert(0, 'research/verification/scripts')
from round3_chunk4_core import *

n = 3
q = set(quad_masks(n))
V = n * n
brute = {}
for k in range(0, V + 1):
    c = 0
    for ids in itertools.combinations(range(V), k):
        m = 0
        for i in ids:
            m |= 1 << i
        if not any((qm & m) == qm for qm in q):
            c += 1
    brute[k] = c

s = Solve(list(q), V)
print('brute:', brute)
print('enum :', {k: len(lv) for k, lv in enumerate(s.levels)})
