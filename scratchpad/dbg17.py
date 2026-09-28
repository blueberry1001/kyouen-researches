import sys
sys.path.insert(0, 'research/verification/scripts')
from round3_chunk4_core import *
import numpy as np

n = 3
q = quad_masks(n)
st, idx, ch, lv = all_safe_sets(q, n * n)
lv1 = lv[1].tolist()
print('level1 globals', lv1)
tot = 0
for i in lv1:
    print('  global', st[i], 'bitcount', bin(st[i]).count('1'), 'nchildren', len(ch[i]))
    tot += len(ch[i])
print('total children of level1 =', tot)
