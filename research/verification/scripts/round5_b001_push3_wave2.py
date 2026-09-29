#!/usr/bin/env python3
"""Push3 wave2: small maximal search, P(S) graphs, 1-swap flips, residual R(S)."""
from __future__ import annotations
import json, sys, random, itertools
from collections import Counter, defaultdict

sys.path.insert(0, r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\scripts")
from kyouen_core import Board, square_points, board_square, is_forbidden_quad

PATH = r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round5_b001_push3.json"
try:
    OUT = json.load(open(PATH, encoding="utf-8"))
except Exception:
    OUT = {}

def save():
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(OUT, f, ensure_ascii=False, indent=1)

# ---------- small maximal search (s_n) ----------
def small_maximal_search(n: int, target_sizes, trials=200000, seed=0):
    """Sample sets of given sizes and check safety + maximality. Also try grow-to-maximal then shrink."""
    rng = random.Random(seed)
    pts = square_points(n)
    B = Board(pts, f"n{n}")
    V = n * n
    found = {k: [] for k in target_sizes}
    # method 1: random sample of exactly-k sets
    for k in target_sizes:
        hit = 0
        local_found = []
        for t in range(trials // max(1, len(target_sizes))):
            s = rng.sample(range(V), k)
            mask = 0
            for p in s:
                mask |= 1 << p
            if not B.is_safe(mask):
                continue
            if B.is_maximal(mask):
                hit += 1
                if len(local_found) < 3:
                    local_found.append(sorted(s))
        found[k].extend(local_found)
        print(f"  n={n} k={k} random-sample maximal hits={hit}", flush=True)
    # method 2: greedy grow then try to reduce to target size by removing points
    # (not generally valid for maximality; skip)
    # method 3: construct by blocking — pick k points, check every empty is blocked
    return {str(k): {"examples": found[k], "n_examples": len(found[k])} for k in target_sizes}

def small_maximal_smart(n: int, k: int, trials=50000, seed=0):
    """Build sets greedily aiming for maximality at size k: each added point should block many empties."""
    rng = random.Random(seed)
    pts = square_points(n)
    B = Board(pts, f"n{n}")
    V = n * n
    examples = []
    hits = 0
    for t in range(trials):
        # start empty, add points preferring high "blocking" until k
        occ = 0
        chosen = []
        candidates = set(range(V))
        ok = True
        for step in range(k):
            # score candidates by how many currently-free points they would block
            best = None
            best_score = -1
            # sample some candidates for speed
            sample = list(candidates)
            if len(sample) > 40:
                sample = rng.sample(sample, 40)
            for p in sample:
                bit = 1 << p
                if not B.is_safe(occ | bit):
                    continue
                # score: number of quads completed that cover free points
                score = 0
                for q in B.quads_by_pt[p]:
                    if (occ | bit) & q == q:
                        # completes a quad — this would be illegal actually
                        pass
                # better score: mobility reduction
                before = len(B.legal_moves(occ)) if occ else V
                after = len(B.legal_moves(occ | bit))
                score = before - after
                if score > best_score:
                    best_score = score
                    best = p
            if best is None:
                ok = False
                break
            occ |= 1 << best
            chosen.append(best)
            candidates.discard(best)
        if not ok or len(chosen) != k:
            continue
        if B.is_maximal(occ):
            hits += 1
            if len(examples) < 5:
                examples.append(sorted(chosen))
    return {"n": n, "k": k, "hits": hits, "examples": examples, "trials": trials}

# ---------- P(S) competition graph ----------
def competition_graph(B: Board, occ: int):
    """P(S): vertices = legal moves; edge (u,v) if u,v conflict (cannot both be played later),
    i.e. occ|{u,v} is unsafe OR {u,v} together with occ completes a quad.
    Actually: u and v are 'in competition' if playing one makes the other illegal
    (i.e. some forbidden quad Q ⊆ occ ∪ {u,v})."""
    moves = B.legal_moves(occ)
    idx = {v: i for i, v in enumerate(moves)}
    edges = []
    for i, u in enumerate(moves):
        for j in range(i + 1, len(moves)):
            v = moves[j]
            # check if occ|{u,v} is unsafe
            if not B.is_safe(occ | (1 << u) | (1 << v)):
                edges.append((i, j))
    return moves, edges

def graph_isomorphism_invariants(moves, edges, B, occ):
    """Cheap invariants: n vertices, m edges, degree hist, triangle count, is_bipartite, components."""
    n = len(moves)
    adj = [[] for _ in range(n)]
    for i, j in edges:
        adj[i].append(j)
        adj[j].append(i)
    deg = [len(a) for a in adj]
    # components
    seen = [False] * n
    comps = 0
    for i in range(n):
        if seen[i]:
            continue
        comps += 1
        stack = [i]
        seen[i] = True
        while stack:
            u = stack.pop()
            for w in adj[u]:
                if not seen[w]:
                    seen[w] = True
                    stack.append(w)
    # triangles
    tri = 0
    eset = set()
    for i, j in edges:
        eset.add((min(i, j), max(i, j)))
    for i in range(n):
        for j in range(i + 1, n):
            if (i, j) not in eset:
                continue
            for k in range(j + 1, n):
                if (i, k) in eset and (j, k) in eset:
                    tri += 1
    # bipartite?
    color = [-1] * n
    bip = True
    for i in range(n):
        if color[i] != -1:
            continue
        color[i] = 0
        stack = [i]
        while stack:
            u = stack.pop()
            for w in adj[u]:
                if color[w] == -1:
                    color[w] = 1 - color[u]
                    stack.append(w)
                elif color[w] == color[u]:
                    bip = False
    return {
        "n_verts": n, "n_edges": len(edges),
        "deg_hist": dict(Counter(deg)),
        "components": comps, "triangles": tri, "bipartite": bip,
        "max_deg": max(deg) if deg else 0,
        "min_deg": min(deg) if deg else 0,
    }

def b063_search(n=5):
    """Find graphs appearing in 4-stone P(S) but not in any 3-stone P(S) (induced subgraph level)."""
    B = board_square(n)
    # collect all P(S) invariants for |S|=0..4 (sample for large)
    # |S|=0: 25 verts; |S|=3: up to 22; we enumerate all safe S of size <=4
    by_size = defaultdict(list)  # k -> list of (deg_hist_signature, invariants, example S)
    sig_examples = {}
    # enumerate all safe sets of size 0..4
    V = n * n
    for k in range(0, 5):
        count = 0
        for S in itertools.combinations(range(V), k):
            mask = 0
            for p in S:
                mask |= 1 << p
            if not B.is_safe(mask):
                continue
            moves, edges = competition_graph(B, mask)
            inv = graph_isomorphism_invariants(moves, edges, B, mask)
            # signature: sorted deg + n_verts + n_edges + tri + bip + comps
            sig = (inv["n_verts"], inv["n_edges"], inv["components"], inv["triangles"],
                   inv["bipartite"], tuple(sorted(inv["deg_hist"].items())))
            by_size[k].append(sig)
            if sig not in sig_examples:
                sig_examples[sig] = {"k": k, "S": list(S), "inv": inv}
            count += 1
        print(f"  n={n} k={k}: {count} safe sets, {len(set(by_size[k]))} distinct P(S) signatures", flush=True)
    # graphs at k=4 whose signature does not appear at k<=3
    # (proxy for "first appears at 4 stones")
    lower_sigs = set()
    for k in range(0, 4):
        lower_sigs |= set(by_size[k])
    new_at_4 = []
    seen4 = set()
    for sig in by_size[4]:
        if sig not in lower_sigs and sig not in seen4:
            seen4.add(sig)
            new_at_4.append(sig_examples[sig])
    return {
        "n": n,
        "counts_by_k": {str(k): len(by_size[k]) for k in by_size},
        "distinct_sigs_by_k": {str(k): len(set(by_size[k])) for k in by_size},
        "n_signatures_first_appearing_at_k4": len(new_at_4),
        "examples_new_at_k4": new_at_4[:8],
    }

# ---------- B039: 1-swap P/N flip rates ----------
def b039_flip_rates(n=5):
    """For safe sets S of size k, consider 1-swap: remove one stone, add one empty legal stone.
    Measure fraction of swaps that flip the P/N outcome (need outcomes solver)."""
    B = board_square(n)
    V = n * n
    # full outcomes for n=5 is 151k states — OK
    print(f"  solving n={n} outcomes...", flush=True)
    outcomes = B.solve_outcomes()
    print(f"  n={n}: {len(outcomes)} states solved", flush=True)
    # sample safe sets of each size
    rng = random.Random(1)
    flip_by_k = defaultdict(lambda: {"swaps": 0, "flips": 0, "examples": []})
    # enumerate small k fully, sample large k
    for k in range(1, 10):
        sample = list(itertools.combinations(range(V), k)) if k <= 3 else None
        if sample is None:
            # random sample
            sample = [tuple(rng.sample(range(V), k)) for _ in range(400)]
        else:
            if len(sample) > 400:
                sample = rng.sample(sample, 400)
        for S in sample:
            mask = 0
            for p in S:
                mask |= 1 << p
            if not B.is_safe(mask):
                continue
            g0 = outcomes.get(mask, None)
            if g0 is None:
                continue
            # 1-swaps: remove u in S, add v not in S, result safe
            empties = [v for v in range(V) if not (mask >> v) & 1]
            for u in S:
                base = mask ^ (1 << u)
                for v in empties:
                    if v == u:
                        continue
                    nxt = base | (1 << v)
                    if not B.is_safe(nxt):
                        continue
                    g1 = outcomes.get(nxt, None)
                    if g1 is None:
                        continue
                    flip_by_k[k]["swaps"] += 1
                    if g0 != g1:
                        flip_by_k[k]["flips"] += 1
                        if len(flip_by_k[k]["examples"]) < 2:
                            flip_by_k[k]["examples"].append({"S": list(S), "remove": u, "add": v})
        sw, fl = flip_by_k[k]["swaps"], flip_by_k[k]["flips"]
        rate = (fl / sw) if sw else None
        print(f"  n={n} k={k}: swaps={sw} flips={fl} rate={rate}", flush=True)
    return {
        str(k): {
            "swaps": v["swaps"], "flips": v["flips"],
            "flip_rate": (v["flips"] / v["swaps"]) if v["swaps"] else None,
            "examples": v["examples"],
        }
        for k, v in flip_by_k.items()
    }

# ---------- B074: max b_S(p)/|S| over n<=6 maximal (use existing n=4,5) ----------
def b074_ratio():
    """Using n=4,5 maximal lists if available; else compute via Board."""
    res = {}
    for n in (4, 5):
        B = board_square(n)
        V = n * n
        # enumerate all maximal sets is heavy for n=5 (16860) but fine
        # Instead: sample maximal sets via random greedy
        rng = random.Random(2)
        max_ratio = 0
        max_b = 0
        best = None
        ratios = []
        for t in range(2000):
            occ = 0
            while True:
                mv = B.legal_moves(occ)
                if not mv:
                    break
                occ |= 1 << mv[rng.randrange(len(mv))]
            k = occ.bit_count()
            # b_S(p) = number of quads Q containing p with |Q ∩ S| = 3
            for p in range(V):
                if (occ >> p) & 1:
                    continue
                b = 0
                for q in B.quads_by_pt[p]:
                    cnt = (q & occ).bit_count()
                    if cnt == 3:
                        b += 1
                if k > 0:
                    r = b / k
                    ratios.append(r)
                    if r > max_ratio:
                        max_ratio = r
                        max_b = b
                        best = (k, b, r)
        res[str(n)] = {
            "max_ratio": max_ratio, "best_k_b_r": best,
            "mean_ratio": (sum(ratios) / len(ratios)) if ratios else None,
            "samples": 2000,
        }
        print(f"  B074 n={n}: max_ratio={max_ratio} best={best}", flush=True)
    return res

# ---------- B037: branching proxy ----------
def b037_branching(n=5):
    """Define: at position S (winner to move), the branching factor of winner-preserving moves.
    Proxy: number of children S∪{p} with the same outcome class (P if g=0)."""
    B = board_square(n)
    outcomes = B.solve_outcomes()
    # for each state, count legal moves and how many go to P-positions
    dist = []
    for occ, val in outcomes.items():
        if bin(occ).count("1") > 8:
            continue
        mv = B.legal_moves(occ)
        if not mv:
            continue
        if val == 1:  # N: winner moves to P
            to_p = sum(1 for u in mv if outcomes.get(occ | (1 << u), 1) == 0)
            dist.append(("N", len(mv), to_p))
        else:  # P: loser to move, all children N (winner-preserving not applicable)
            dist.append(("P", len(mv), 0))
    # summarize
    by = defaultdict(list)
    for cls, nm, tp in dist:
        by[cls].append((nm, tp))
    summary = {}
    for cls, lst in by.items():
        nm_hist = Counter(x[0] for x in lst)
        tp_hist = Counter(x[1] for x in lst)
        summary[cls] = {"n_states": len(lst), "legal_moves_hist": dict(nm_hist), "winner_preserving_children_hist": dict(tp_hist)}
    return summary

if __name__ == "__main__":
    print("=== B063 P(S) signatures n=5 ===", flush=True)
    OUT["b063"] = b063_search(5)
    save()
    print("=== B039 flip rates n=4 ===", flush=True)
    OUT["b039"] = b039_flip_rates(4)
    save()
    print("=== B074 ratio ===", flush=True)
    OUT["b074"] = b074_ratio()
    save()
    print("=== B037 branching n=5 ===", flush=True)
    OUT["b037"] = b037_branching(5)
    save()
    print("=== small maximal n=9 k=8,9 ===", flush=True)
    OUT.setdefault("s_search", {})
    OUT["s_search"]["n9_k8"] = small_maximal_smart(9, 8, trials=8000, seed=1)
    save()
    OUT["s_search"]["n9_k9"] = small_maximal_smart(9, 9, trials=8000, seed=2)
    save()
    print("=== small maximal n=10 k=9,10 ===", flush=True)
    OUT["s_search"]["n10_k9"] = small_maximal_smart(10, 9, trials=8000, seed=3)
    save()
    OUT["s_search"]["n10_k10"] = small_maximal_smart(10, 10, trials=8000, seed=4)
    save()
    print("WAVE2 DONE", flush=True)
    print(json.dumps({k: OUT[k] for k in OUT if k in ("b063", "b039", "b074", "b037", "s_search")}, ensure_ascii=False, indent=1)[:4000])
