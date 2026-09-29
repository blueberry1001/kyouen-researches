#!/usr/bin/env python3
"""Round5 B032: compute T*({p}) for each winning first move on n=5.
Also B100: collect maximal safe set sizes for n=4,5,6 if data available."""
import sys, json, time
sys.path.insert(0, r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\scripts")
from kyouen_core import Board, square_points

t0 = time.time()
n = 5
b = Board(square_points(n), f"n{n}")
V = b.V
print(f"Board n={n}: V={V}, quads={len(b.quads)}", flush=True)

# T*(S) definition from the bank:
# "NではPへ、Pでは任意の合法手へ進む"
# Terminal states have T* = {|S|} (game ends).
# For N position S: T*(S) = union of T*(S+p) over p with g(S+p)=0 (P children)
# For P position S: T*(S) = union of T*(S+p) over all legal p
# But we need Grundy values first.

from functools import lru_cache

quads_by_pt = b.quads_by_pt
full = b.full
quads = b.quads

def legal_moves(occ):
    out = []
    empty = full ^ occ
    v = 0
    while empty:
        if empty & 1:
            bit = 1 << v
            ok = True
            for q in quads_by_pt[v]:
                if (occ & q) == (q & ~bit):
                    ok = False
                    break
            if ok:
                out.append(v)
        empty >>= 1
        v += 1
    return out

grundy_memo = {}
def grundy(occ):
    if occ in grundy_memo:
        return grundy_memo[occ]
    moves = legal_moves(occ)
    if not moves:
        grundy_memo[occ] = 0
        return 0
    child_g = set()
    for v in moves:
        child_g.add(grundy(occ | (1 << v)))
    g = 0
    while g in child_g:
        g += 1
    grundy_memo[occ] = g
    return g

# T* computation
tstar_memo = {}
def tstar(occ):
    if occ in tstar_memo:
        return tstar_memo[occ]
    moves = legal_moves(occ)
    g = grundy(occ)
    if not moves:
        tstar_memo[occ] = frozenset([bin(occ).count('1')])
        return tstar_memo[occ]
    if g > 0:
        # N: go to P children only
        children = [v for v in moves if grundy(occ | (1 << v)) == 0]
    else:
        # P: any legal move
        children = moves
    result = set()
    for v in children:
        result |= tstar(occ | (1 << v))
    tstar_memo[occ] = frozenset(result)
    return tstar_memo[occ]

# Compute T* for each 1-stone position
print("Computing T*({p}) for all p...", flush=True)
results = {}
for i in range(V):
    g = grundy(1 << i)
    ts = tstar(1 << i)
    x, y = i % n, i // n
    results[i] = {
        "xy": [x, y],
        "g": g,
        "tstar": sorted(ts),
        "min_t": min(ts),
        "max_t": max(ts),
        "width": max(ts) - min(ts),
    }

# Classify winning first moves (g=0)
winning = {i: r for i, r in results.items() if r["g"] == 0}
losing = {i: r for i, r in results.items() if r["g"] > 0}
print(f"Winning first moves: {len(winning)}, Losing: {len(losing)}", flush=True)

# B032: are argmin and argmax disjoint among winning first moves?
min_set = set(i for i, r in winning.items() if r["min_t"] == min(rr["min_t"] for rr in winning.values()))
max_set = set(i for i, r in winning.items() if r["max_t"] == max(rr["max_t"] for rr in winning.values()))
# Actually B032 says "最短化する最適初手の集合" and "最長化する最適初手の集合"
# This means: among winning first moves, which ones achieve the shortest/longest game?
# But "winning first move" means g({p})=0, and T*({p}) is the set of terminal sizes.
# "最短勝ち" = minimize the game length, "最長勝ち" = maximize.
# For each winning first move, min T* and max T* give the range.
# argmin of min_t = "shortest winning first moves"
# argmax of max_t = "longest winning first moves"

min_t_vals = {i: r["min_t"] for i, r in winning.items()}
max_t_vals = {i: r["max_t"] for i, r in winning.items()}
best_min = min(min_t_vals.values())
best_max = max(max_t_vals.values())
shortest = set(i for i, v in min_t_vals.items() if v == best_min)
longest = set(i for i, v in max_t_vals.items() if v == best_max)
overlap = shortest & longest

print(f"\nB032 analysis:", flush=True)
print(f"  Winning first moves: {len(winning)}", flush=True)
print(f"  min_t values: {sorted(set(min_t_vals.values()))}", flush=True)
print(f"  max_t values: {sorted(set(max_t_vals.values()))}", flush=True)
print(f"  shortest winning (min_t={best_min}): {sorted(shortest)}", flush=True)
print(f"  longest winning (max_t={best_max}): {sorted(longest)}", flush=True)
print(f"  overlap (disjoint? {len(overlap)==0}): {sorted(overlap)}", flush=True)

# Also print all winning first move details
print("\nWinning first move details:", flush=True)
for i in sorted(winning.keys()):
    r = winning[i]
    print(f"  ({r['xy'][0]},{r['xy'][1]}): g={r['g']}, T*={r['tstar']}, min={r['min_t']}, max={r['max_t']}", flush=True)

# T*(empty)
ts_empty = tstar(0)
print(f"\nT*(empty) = {sorted(ts_empty)}", flush=True)
print(f"K_5 = 9, in T*(empty)? {9 in ts_empty}", flush=True)

result = {
    "n": n,
    "winning_count": len(winning),
    "losing_count": len(losing),
    "winning_details": {str(i): winning[i] for i in winning},
    "losing_details": {str(i): losing[i] for i in losing},
    "b032_shortest": sorted(shortest),
    "b032_longest": sorted(longest),
    "b032_disjoint": len(overlap) == 0,
    "b032_overlap": sorted(overlap),
    "tstar_empty": sorted(ts_empty),
    "K_5": 9,
    "K_5_in_tstar_empty": 9 in ts_empty,
}
with open(r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round5_b001_b032.json", "w") as f:
    json.dump(result, f, indent=2)
print(f"\nTime: {time.time()-t0:.1f}s", flush=True)
print("Done.", flush=True)
