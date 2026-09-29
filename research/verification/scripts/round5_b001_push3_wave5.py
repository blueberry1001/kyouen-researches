#!/usr/bin/env python3
"""Push3 wave5: save rect results, J-graph, B090, K10, s_n."""
from __future__ import annotations
import json, sys, random, itertools
from collections import Counter, defaultdict

sys.path.insert(0, r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\scripts")
from kyouen_core import Board, square_points, board_square, board_rect

PATH = r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round5_b001_push3.json"
OUT = json.load(open(PATH, encoding="utf-8"))

def save():
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(OUT, f, ensure_ascii=False, indent=1)

# hardcode the measured rectangle results (wave4 stdout)
OUT["rect_pw"] = [
    {"w": 3, "h": 5, "V": 15, "g_empty": 0, "winner": "second", "W_size": 0, "is_partial": False},
    {"w": 4, "h": 4, "V": 16, "g_empty": 0, "winner": "second", "W_size": 0, "is_partial": False},
    {"w": 4, "h": 5, "V": 20, "g_empty": 1, "winner": "first", "W_size": 14, "is_partial": True},
    {"w": 4, "h": 6, "V": 24, "g_empty": 0, "winner": "second", "W_size": 0, "is_partial": False},
    {"w": 5, "h": 5, "V": 25, "g_empty": 1, "winner": "first", "W_size": 9, "is_partial": True},
    {"w": 5, "h": 6, "V": 30, "g_empty": 0, "winner": "second", "W_size": 0, "is_partial": False},
    {"w": 3, "h": 7, "V": 21, "g_empty": 2, "winner": "first", "W_size": 11, "is_partial": True},
]
save()
print("rect saved", flush=True)

def greedy_grow(B, occ0):
    V = B.V
    occ = set(occ0)
    bits = 0
    for p in occ:
        bits |= 1 << p
    changed = True
    while changed:
        changed = False
        for p in range(V):
            if p in occ:
                continue
            bit = 1 << p
            ok = True
            for q in B.quads_by_pt[p]:
                if (bits | bit) & q == q:
                    ok = False
                    break
            if ok:
                occ.add(p)
                bits |= bit
                changed = True
    return occ

# J-graph n=4
print("=== J-graph n=4 ===", flush=True)
B = board_square(4)
G = B.solve_grundy()
edges = []
adj = defaultdict(set)
for i in range(16):
    for j in range(i + 1, 16):
        mask = (1 << i) | (1 << j)
        if not B.is_safe(mask):
            continue
        if G.get(mask) == 0:
            edges.append((i, j))
            adj[i].add(j)
            adj[j].add(i)
noniso = set(adj)
seen = set()
comps = 0
for v in noniso:
    if v in seen:
        continue
    comps += 1
    stack = [v]
    seen.add(v)
    while stack:
        u = stack.pop()
        for w in adj[u]:
            if w not in seen:
                seen.add(w)
                stack.append(w)
OUT["jgraph"] = {"4": {
    "n_edges": len(edges), "n_nonisolated": len(noniso),
    "components_on_noniso": comps,
    "deg_hist": {str(k): v for k, v in Counter(len(adj[v]) for v in noniso).items()},
}}
print(OUT["jgraph"]["4"], flush=True)
save()

# B090 n=5
print("=== B090 n=5 ===", flush=True)
B5 = board_square(5)
rng = random.Random(3)
max_sets = []
for t in range(2500):
    occ = 0
    while True:
        mv = B5.legal_moves(occ)
        if not mv:
            break
        occ |= 1 << mv[rng.randrange(len(mv))]
    if occ.bit_count() == 9:
        max_sets.append(occ)
uniq = list(set(max_sets))
edges = 0
for i in range(len(uniq)):
    for j in range(i + 1, len(uniq)):
        if (uniq[i] ^ uniq[j]).bit_count() == 2:
            edges += 1
OUT["b090"] = {
    "n5_K_max_sets_sampled": len(uniq),
    "one_swap_edges_in_sample": edges,
    "existing": {
        "n6": {"max_sets": 464, "orbits": 58, "swap_edges": 608},
        "n7": {"max_sets": 16, "orbits": 2, "swap_edges": 0},
    },
}
print(OUT["b090"], flush=True)
save()

# K10 embed extend
print("=== K10 embed ===", flush=True)
B9 = board_square(9)
best9 = set()
for t in range(25):
    occ = greedy_grow(B9, set())
    if len(occ) > len(best9):
        best9 = occ
        print("  9x9", len(best9), flush=True)
print("  best9", len(best9), sorted(best9), flush=True)
OUT.setdefault("k10_search", {})
OUT["k10_search"]["best9"] = {"size": len(best9), "witness": sorted(best9)}
save()
B10 = board_square(10)
best10 = set()
for ox in range(2):
    for oy in range(2):
        mapped = []
        for p in best9:
            x, y = p % 9, p // 9
            X, Y = x + ox, y + oy
            if 0 <= X < 10 and 0 <= Y < 10:
                mapped.append(Y * 10 + X)
        grown = greedy_grow(B10, set(mapped))
        print(f"  off ({ox},{oy}) map={len(mapped)} grow={len(grown)}", flush=True)
        if len(grown) > len(best10):
            best10 = grown
rng = random.Random(2)
for t in range(40):
    kicked = set(best10)
    if len(kicked) > 2:
        for _ in range(rng.randint(1, 2)):
            kicked.discard(rng.choice(list(kicked)))
    cand = greedy_grow(B10, kicked)
    if len(cand) > len(best10):
        best10 = cand
        print("  local best", len(best10), flush=True)
OUT["k10_search"]["embed_extend"] = {"size": len(best10), "witness": sorted(best10)}
save()
print("  K10 best", len(best10), flush=True)

# s searches
print("=== s searches ===", flush=True)
OUT.setdefault("s_search", {})
def s_search(n, k, trials, seed):
    B = board_square(n)
    V = n * n
    rng = random.Random(seed)
    hits = []
    for t in range(trials):
        s = rng.sample(range(V), k)
        mask = 0
        for p in s:
            mask |= 1 << p
        if B.is_safe(mask) and B.is_maximal(mask):
            hits.append(sorted(s))
            if len(hits) >= 2:
                break
    return {"n": n, "k": k, "hits": hits, "n_hits": len(hits), "trials": trials}

for n, k, seed in [(9, 8, 21), (9, 9, 22), (10, 10, 24), (10, 11, 25)]:
    OUT["s_search"][f"n{n}_k{k}"] = s_search(n, k, 10000, seed)
    print(f"  n={n} k={k} hits={OUT['s_search'][f'n{n}_k{k}']['n_hits']}", flush=True)
    save()
print("WAVE5 DONE", flush=True)
