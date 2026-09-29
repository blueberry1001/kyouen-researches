#!/usr/bin/env python3
"""Push3 wave4 (lean): K10 embed+extend, s_n, J-graph, rectangles, B070/B089/B090."""
from __future__ import annotations
import json, sys, random, itertools
from collections import Counter, defaultdict

sys.path.insert(0, r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\scripts")
from kyouen_core import Board, square_points, board_square, board_rect, is_forbidden_quad

PATH = r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round5_b001_push3.json"
OUT = json.load(open(PATH, encoding="utf-8"))

def save():
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(OUT, f, ensure_ascii=False, indent=1)

def is_safe_mask(B, occ):
    return B.is_safe(occ)

def greedy_grow(B, occ0, rng=None):
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

# ---------- K10: embed K9=18 then extend ----------
def k10_embed_extend():
    B9 = board_square(9)
    # find 18-stone safe on 9x9 via search
    rng = random.Random(1)
    best9 = set()
    for t in range(40):
        occ = greedy_grow(B9, set())
        if len(occ) > len(best9):
            best9 = occ
            print(f"  9x9 best {len(best9)}", flush=True)
    print("  9x9 witness size", len(best9), sorted(best9)[:20], flush=True)
    OUT.setdefault("k10_search", {})
    OUT["k10_search"]["best9"] = {"size": len(best9), "witness": sorted(best9)}
    save()
    # embed into 10x10 at several offsets and grow
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
            # also try leaving one corner of 10x10 free
            grown = greedy_grow(B10, set(mapped))
            print(f"  embed off=({ox},{oy}) mapped={len(mapped)} grown={len(grown)}", flush=True)
            if len(grown) > len(best10):
                best10 = grown
                print(f"  10x10 embed-grow best {len(best10)}", flush=True)
    # additional local search from best10
    rng = random.Random(2)
    for t in range(60):
        kicked = set(best10)
        if len(kicked) > 2:
            for _ in range(rng.randint(1, 2)):
                kicked.discard(rng.choice(list(kicked)))
        cand = greedy_grow(B10, kicked)
        if len(cand) > len(best10):
            best10 = cand
            print(f"  10x10 local {t}: best {len(best10)}", flush=True)
    OUT["k10_search"]["embed_extend"] = {"size": len(best10), "witness": sorted(best10)}
    save()
    return len(best10)

# ---------- s_n lean search ----------
def s_search(n, k, trials=8000, seed=0):
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

# ---------- J-graph (2-stone nimber pairs) ----------
def jgraph(n):
    B = board_square(n)
    G = B.solve_grundy()
    # J edges: pairs {p,q} with g({p,q})=0 and p,q distinct (both legal from empty... any)
    edges = []
    verts = set()
    for i in range(n * n):
        for j in range(i + 1, n * n):
            mask = (1 << i) | (1 << j)
            if not B.is_safe(mask):
                continue
            verts.add(i)
            verts.add(j)
            if G.get(mask) == 0:
                edges.append((i, j))
    # connectivity of graph on non-isolated verts of the 2-stone P-graph
    # actually J_n is the graph whose edges are 2-stone P-positions
    adj = defaultdict(set)
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    noniso = set(adj.keys())
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
    deg_hist = Counter(len(adj[v]) for v in noniso) if noniso else {}
    return {
        "n": n, "n_edges": len(edges), "n_nonisolated": len(noniso),
        "components_on_noniso": comps, "deg_hist": {str(k): v for k, v in deg_hist.items()},
        "g2_hist": dict(Counter(G.get((1 << i) | (1 << j), None)
                                 for i in range(n * n) for j in range(i + 1, n * n)
                                 if B.is_safe((1 << i) | (1 << j)))),
    }

# ---------- rectangles: partial-win search ----------
def rect_partial_win(w, h):
    B = board_rect(w, h)
    G = B.solve_grundy()
    # winning first moves
    V = w * h
    win_moves = 0
    for p in range(V):
        if G.get(1 << p, 0) != 0:  # N after first move means first player wins from empty?
            pass
    # empty board outcome
    g0 = G.get(0, 0)
    # winning first moves = those p where g({p})==0
    W = [p for p in range(V) if G.get(1 << p, -1) == 0]
    return {
        "w": w, "h": h, "V": V, "g_empty": g0,
        "winner": "first" if g0 != 0 else "second",
        "W_size": len(W),
        "is_partial": 0 < len(W) < V,
    }

# ---------- B070: small graphs forbidden as P(S) ----------
def b070_forbidden(n=5):
    """Which small graphs (on 3 verts) never appear as P(S)?"""
    B = board_square(n)
    # collect all P(S) for |S|<=3 as sets of edge-sets (on labeled legal moves — too many)
    # Instead: collect all 3-vertex induced subgraphs' degree/edge patterns of P(S)
    patterns_seen = set()
    V = n * n
    for k in range(0, 4):
        for S in (itertools.combinations(range(V), k) if k else [()]):
            mask = 0
            for p in S:
                mask |= 1 << p
            if not B.is_safe(mask):
                continue
            moves = B.legal_moves(mask)
            m = len(moves)
            # for every 3-subset of moves, record induced subgraph type (n_edges among the 3)
            if m >= 3:
                for tri in itertools.combinations(range(m), 3):
                    e = 0
                    for a, b in ((0, 1), (0, 2), (1, 2)):
                        u, v = moves[tri[a]], moves[tri[b]]
                        if not B.is_safe(mask | (1 << u) | (1 << v)):
                            e += 1
                    patterns_seen.add(e)  # 0,1,2,3 edges
    # 3-vertex graphs up to iso: 0,1,2,3 edges (path2, P3, triangle)
    all_types = {0, 1, 2, 3}
    return {
        "n": n,
        "induced_3vert_edgecounts_seen": sorted(patterns_seen),
        "forbidden_3vert_types": sorted(all_types - patterns_seen),
    }

# ---------- B089: try 2-curve constructions ----------
def b089_two_curves():
    """Try unions of two parabolas / parabola + few extra points, measure size vs safety on n×n."""
    res = {}
    for n in [8, 10, 12]:
        # single parabola within board
        pts = [(x, x * x) for x in range(n) if x * x < n]
        # two parabolas: y=x^2 and y=x^2+1 (shifted) — but y may leave board
        pts2 = [(x, x * x) for x in range(n) if x * x < n] + [(x, x * x + 1) for x in range(n) if x * x + 1 < n]
        # staircase: (x, x) mod something — use 3 points per line on several lines
        # lines y = x + c for c = -2..2, take 3 points each that fit
        pts3 = []
        for c in range(-2, 3):
            taken = 0
            for x in range(n):
                y = x + c
                if 0 <= y < n and taken < 3:
                    pts3.append((x, y))
                    taken += 1
        def safe_count(pts):
            pts = list(dict.fromkeys(pts))
            ok = True
            bad = None
            for ids in itertools.combinations(range(len(pts)), 4):
                a, b, c, d = (pts[i] for i in ids)
                if is_forbidden_quad((a, b, c, d)):
                    ok = False
                    bad = ids
                    break
            return {"size": len(pts), "safe": ok, "bad": bad}
        res[f"n{n}"] = {
            "parabola_in_board": safe_count(pts),
            "two_shifted_parabolas": safe_count(pts2),
            "3_per_line_5lines": safe_count(pts3),
        }
    # B089 weak: within n×n, single parabola has floor(sqrt(n-1))+1 points
    res["parabola_size_formula"] = {str(n): int(n ** 0.5) + 1 for n in range(2, 21)}
    return res

# ---------- B090: orbits vs swap barrier (n=5,6 from existing + recompute n=5) ----------
def b090_orbit_barrier():
    # from existing: n=6: 464 max sets / 58 orbits / 1-swap edges 608; n=7: 16 / 2 / 0
    # recompute n=5: all maximal by random greedy, count 1-swap edges among size-K maximal
    B = board_square(5)
    rng = random.Random(3)
    max_sets = []
    for t in range(3000):
        occ = 0
        while True:
            mv = B.legal_moves(occ)
            if not mv:
                break
            occ |= 1 << mv[rng.randrange(len(mv))]
        if occ.bit_count() == 9:  # K_5 = 9
            max_sets.append(occ)
    uniq = list(set(max_sets))
    # 1-swap edges: two max sets S,S' with |S Δ S'| = 2 and both safe maximal
    edges = 0
    # only check pairs from sample
    for i in range(len(uniq)):
        for j in range(i + 1, len(uniq)):
            x = uniq[i] ^ uniq[j]
            if x.bit_count() == 2:
                edges += 1
    return {
        "n5_K_max_sets_sampled": len(uniq),
        "one_swap_edges_in_sample": edges,
        "existing": {
            "n6": {"max_sets": 464, "orbits": 58, "swap_edges": 608, "rho1_pct": 64},
            "n7": {"max_sets": 16, "orbits": 2, "swap_edges": 0, "rho": 2},
        },
    }

if __name__ == "__main__":
    print("=== B070 forbidden 3-vert ===", flush=True)
    OUT["b070"] = b070_forbidden(5)
    save()
    print(OUT["b070"], flush=True)
    print("=== B089 two curves ===", flush=True)
    OUT["b089"] = b089_two_curves()
    save()
    print(json.dumps(OUT["b089"], indent=1)[:1500], flush=True)
    print("=== rectangles partial-win ===", flush=True)
    OUT["rect_pw"] = []
    for w, h in [(3, 5), (4, 4), (4, 5), (4, 6), (5, 5), (5, 6), (3, 7), (4, 7)]:
        r = rect_partial_win(w, h)
        OUT["rect_pw"].append(r)
        print(" ", r, flush=True)
    save()
    print("=== J-graph n=4,5 ===", flush=True)
    OUT["jgraph"] = {}
    for n in (4, 5):
        OUT["jgraph"][str(n)] = jgraph(n)
        print(" ", n, OUT["jgraph"][str(n)], flush=True)
    save()
    print("=== B090 orbit/barrier ===", flush=True)
    OUT["b090"] = b090_orbit_barrier()
    save()
    print(OUT["b090"], flush=True)
    print("=== K10 embed extend ===", flush=True)
    k10_embed_extend()
    print("=== s searches ===", flush=True)
    OUT.setdefault("s_search", {})
    for n, k, seed in [(9, 8, 21), (9, 9, 22), (10, 9, 23), (10, 10, 24), (10, 11, 25)]:
        OUT["s_search"][f"n{n}_k{k}"] = s_search(n, k, trials=12000, seed=seed)
        print(f"  n={n} k={k} hits={OUT['s_search'][f'n{n}_k{k}']['n_hits']}", flush=True)
        save()
    print("WAVE4 DONE", flush=True)
