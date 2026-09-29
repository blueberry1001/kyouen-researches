#!/usr/bin/env python3
"""Round5 B024: check two-stone nimbers on n=6 (all-first-win board) for even values.
Also collect data for B029, B032, B037, B039."""
import sys, json, time
sys.path.insert(0, r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\scripts")
from kyouen_core import Board, square_points
from collections import Counter

t0 = time.time()
n = 6
b = Board(square_points(n), f"n{n}")
print(f"Board n={n}: V={b.V}, quads={len(b.quads)}", flush=True)

# Compute all 1-stone and 2-stone Grundy values
# For g({p}) we need mex of g({p,q}) over legal q
# For g({p,q}) we need mex of g({p,q,r}) over legal r
# This requires 3-stone layer. Let's compute g for all safe sets up to 3 stones.

# Safe 1-stone
safe1 = [1 << i for i in range(b.V)]
# Safe 2-stone
safe2 = []
for i in range(b.V):
    for j in range(i+1, b.V):
        s = (1 << i) | (1 << j)
        if b.is_safe(s):
            safe2.append(s)
print(f"Safe 2-stone sets: {len(safe2)}", flush=True)

# Safe 3-stone
safe3 = []
for s2 in safe2:
    # find highest bit
    hi = s2.bit_length() - 1
    for j in range(hi+1, b.V):
        if s2 & (1 << j):
            continue
        s = s2 | (1 << j)
        if b.is_safe(s):
            safe3.append(s)
print(f"Safe 3-stone sets: {len(safe3)}", flush=True)

# Build map from mask -> index for fast lookup
# For Grundy of 3-stone terminal-ish: g(S) = mex{g(S+p) for legal p}
# Terminal if no legal moves. We need 4-stone too for g of 3-stone.
# Actually for g of k-stone we need (k+1)-stone. Let's go to 4.

safe4 = []
for s3 in safe3:
    hi = s3.bit_length() - 1
    for j in range(hi+1, b.V):
        if s3 & (1 << j):
            continue
        s = s3 | (1 << j)
        if b.is_safe(s):
            safe4.append(s)
print(f"Safe 4-stone sets: {len(safe4)}", flush=True)

# Terminal sets (no legal move) have g=0. A set is terminal if no empty point can be added safely.
def legal_moves(occ):
    out = []
    empty = b.full ^ occ
    v = 0
    while empty:
        if empty & 1:
            bit = 1 << v
            ok = True
            for q in b.quads_by_pt[v]:
                if (occ & q) == (q & ~bit):
                    ok = False
                    break
            if ok:
                out.append(v)
        empty >>= 1
        v += 1
    return out

# Compute Grundy bottom-up from largest size
# We'll compute g for all safe sets from k=K down to 0
# Actually just compute for k=4 (need k=5 for mex... wait)
# g(S) = mex{g(S+p) : p legal}. If no legal moves, g=0.
# So for 4-stone sets, we need 5-stone children. But if 4-stone is terminal, g=0.

# Let's compute g for 4-stone sets first (check if terminal or not, and children)
# Actually for our purpose we only need g of 2-stone sets.
# g(2-stone) = mex{g(3-stone children)}
# g(3-stone) = mex{g(4-stone children)}
# g(4-stone) = mex{g(5-stone children)} or 0 if terminal

# Let's just do full recursion with memoization up to whatever depth is needed.
# For n=6, K_6=11, so we could have up to 11 stones. But we only need g of 2-stone sets,
# which depends on children at 3,4,5,... up to terminal. This is the full game tree from 2-stone positions.

# Actually the full recursion from a 2-stone position explores all extensions. For n=6 that's a lot
# but manageable if we memoize globally.

from functools import lru_cache

# Precompute quads_by_pt for speed
quads_by_pt = b.quads_by_pt
full = b.full
quads = b.quads

def is_safe_fast(occ):
    for q in quads:
        if (occ & q) == q:
            return False
    return True

# Memoized Grundy
grundy_memo = {}

def grundy(occ):
    if occ in grundy_memo:
        return grundy_memo[occ]
    # find legal moves
    moves = []
    empty = full ^ occ
    v = 0
    e = empty
    while e:
        if e & 1:
            bit = 1 << v
            ok = True
            for q in quads_by_pt[v]:
                if (occ & q) == (q & ~bit):
                    ok = False
                    break
            if ok:
                moves.append(occ | bit)
        e >>= 1
        v += 1
    if not moves:
        grundy_memo[occ] = 0
        return 0
    child_g = set()
    for m in moves:
        child_g.add(grundy(m))
    # mex
    g = 0
    while g in child_g:
        g += 1
    grundy_memo[occ] = g
    return g

# Compute g for all 2-stone safe sets
print("Computing g for 2-stone sets...", flush=True)
g2_vals = []
for s in safe2:
    g = grundy(s)
    g2_vals.append(g)

hist = Counter(g2_vals)
print(f"n=6 two-stone nimber histogram: {dict(sorted(hist.items()))}", flush=True)
print(f"Even values present: {[v for v in hist if v > 0 and v % 2 == 0]}", flush=True)
print(f"Memo size: {len(grundy_memo)}", flush=True)
print(f"Time: {time.time()-t0:.1f}s", flush=True)

# Also compute 1-stone
print("Computing g for 1-stone sets...", flush=True)
g1_vals = []
for i in range(b.V):
    g = grundy(1 << i)
    g1_vals.append(g)
hist1 = Counter(g1_vals)
print(f"n=6 one-stone nimber histogram: {dict(sorted(hist1.items()))}", flush=True)

# Save results
result = {
    "n": n,
    "safe2_count": len(safe2),
    "safe3_count": len(safe3),
    "safe4_count": len(safe4),
    "g2_hist": dict(sorted(hist.items())),
    "g1_hist": dict(sorted(hist1.items())),
    "even_g2_present": [v for v in hist if v > 0 and v % 2 == 0],
    "memo_size": len(grundy_memo),
    "time_sec": round(time.time()-t0, 1),
}
with open(r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round5_b001_b024.json", "w") as f:
    json.dump(result, f, indent=2)
print("Done.", flush=True)
