import sys
sys.path.insert(0, 'research/verification/scripts')
from round3_chunk4_core import *

n = 3
q = quad_masks(n)
qbp = qbp_of(q, n * n)
occ = 1 | 256   # (0,0) and (1,0)
# what point v would complete a quad?
# find v such that occ|v completes a forbidden quad
for qm in q:
    if (qm & occ).bit_count() == 3 and (qm & ~occ).bit_count() == 1:
        v = (qm & ~occ)
        print('quad', bin(qm), 'missing v', v)

# Now the reverse: enumerate all safe 2-sets by brute force
import itertools
pts = square_points(n)
V = n * n
allq = set(q)
safe2 = []
for a, b in itertools.combinations(range(V), 2):
    m = (1 << a) | (1 << b)
    if not any((qm & m) == qm for qm in allq):
        safe2.append(m)
print('brute safe 2-sets:', len(safe2))
enum2 = [m for m in Solve(q, V).states if bin(m).count('1') == 2]
print('enum safe 2-sets:', len(enum2))
print('missing:', [bin(m) for m in safe2 if m not in set(enum2)])
