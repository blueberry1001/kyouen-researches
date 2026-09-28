import sys
sys.path.insert(0, 'research/verification/scripts')
from round3_chunk4_core import *
import numpy as np

n = 3
q = quad_masks(n)
st, idx, ch, lv = all_safe_sets(q, n * n)
print('len(states)', len(st), 'len(children)', len(ch))
print('children[0] len', len(ch[0]), '->', [st[j] for j in ch[0]])
print('children[1] len', len(ch[1]), 'state', st[1])
print('  ->', [st[j] for j in ch[1]])
# global index 1 has 8 legal moves. Does ch[1] have 8?
print('legal_mask(st[1]) popcount', bin(
    __import__('round3_chunk4_core').__dict__ and 0 or 0))
