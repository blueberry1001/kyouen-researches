#!/usr/bin/env python3
"""Round5 B077/B100: analyze maximal safe sets on n=5,6.
B077: does any maximal safe set have min b_S(p) >= 2?
B100: what sizes appear among maximal safe sets (spectrum)?"""
import sys, json, time
sys.path.insert(0, r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\scripts")
from kyouen_core import Board, square_points
from collections import Counter

def analyze_maximal(n, max_enum=None):
    t0 = time.time()
    b = Board(square_points(n), f"n{n}")
    V = b.V
    print(f"n={n}: V={V}, quads={len(b.quads)}", flush=True)
    
    # Enumerate maximal safe sets via DFS
    # For small n (<=5), we can enumerate all safe sets and check maximality
    # For n=6, we use the known count to verify
    
    maximal = []
    
    def is_safe(occ):
        for q in b.quads:
            if (occ & q) == q:
                return False
        return True
    
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
    
    def is_maximal(occ):
        return len(legal_moves(occ)) == 0
    
    # DFS to enumerate all maximal safe sets
    def dfs(occ, start):
        moves = [v for v in legal_moves(occ) if v >= start]
        if not moves:
            if is_maximal(occ):
                maximal.append(occ)
            return
        # If no moves from here but we haven't reached maximal... 
        # Actually legal_moves empty means maximal (or terminal)
        for v in moves:
            dfs(occ | (1 << v), v + 1)
        # Also check if current is maximal (no moves at all)
        if not legal_moves(occ) and is_maximal(occ):
            maximal.append(occ)
    
    # Better: enumerate by adding points in order
    def dfs2(occ, start):
        # Find ALL legal moves (not just those >= start)
        all_moves = []
        empty = b.full ^ occ
        for v in range(V):
            if empty & (1 << v):
                bit = 1 << v
                ok = True
                for q in b.quads_by_pt[v]:
                    if (occ & q) == (q & ~bit):
                        ok = False
                        break
                if ok:
                    all_moves.append(v)
        if not all_moves:
            # No point can be added -> maximal
            maximal.append(occ)
            return
        # Only extend with points >= start (to avoid duplicates)
        for v in all_moves:
            if v >= start:
                dfs2(occ | (1 << v), v + 1)
    
    # For empty start
    dfs2(0, 0)
    
    # Analyze
    size_hist = Counter(bin(s).count('1') for s in maximal)
    print(f"  Maximal safe sets: {len(maximal)}", flush=True)
    print(f"  Size spectrum: {dict(sorted(size_hist.items()))}", flush=True)
    
    # B077: min b_S(p) >= 2 for all empty p
    b077_count = 0
    b077_witness = None
    for s in maximal:
        k = bin(s).count('1')
        empty = b.full ^ s
        min_b = float('inf')
        v = 0
        e = empty
        while e:
            if e & 1:
                # count triples in s that complete to forbidden quad with v
                b_count = 0
                for q in b.quads_by_pt[v]:
                    t = q & ~(1 << v)  # the other 3 points
                    if (s & t) == t:
                        b_count += 1
                if b_count < min_b:
                    min_b = b_count
            e >>= 1
            v += 1
        if min_b >= 2:
            b077_count += 1
            if b077_witness is None:
                b077_witness = {
                    "mask": s,
                    "points": [(i%n, i//n) for i in range(V) if s & (1<<i)],
                    "k": k,
                    "min_b": min_b,
                }
    
    print(f"  B077 (min b_S(p) >= 2): {b077_count} sets", flush=True)
    if b077_witness:
        print(f"  B077 witness: {b077_witness}", flush=True)
    
    print(f"  Time: {time.time()-t0:.1f}s", flush=True)
    return {
        "n": n,
        "V": V,
        "maximal_count": len(maximal),
        "size_spectrum": dict(sorted(size_hist.items())),
        "b077_count": b077_count,
        "b077_witness": b077_witness,
    }

results = {}
for n in [4, 5]:
    results[n] = analyze_maximal(n)

# n=6 is too large for full enumeration in Python (349k sets)
# But we can check if there's existing data
print("\nSkipping n=6 full enumeration (349,596 sets, would take too long in Python)", flush=True)

with open(r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round5_b001_b077.json", "w") as f:
    json.dump(results, f, indent=2)
print("Done.", flush=True)
