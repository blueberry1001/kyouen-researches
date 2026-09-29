#!/usr/bin/env python3
"""Push3 wave3: K_10 witness improvement + small maximal s_9/s_10 + R(S) + misc."""
from __future__ import annotations
import json, sys, random, itertools
from collections import Counter, defaultdict

sys.path.insert(0, r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\scripts")
from kyouen_core import Board, square_points, board_square, is_forbidden_quad

PATH = r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round5_b001_push3.json"
OUT = json.load(open(PATH, encoding="utf-8"))

def save():
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(OUT, f, ensure_ascii=False, indent=1)

# ---------- shared helpers ----------
def build_board(n):
    return board_square(n)

def maxsafe_search(n, iters=30, seeds=20, base=None):
    """Improved local search for maximum safe set."""
    B = build_board(n)
    V = n * n
    rng = random.Random(99 + n)
    best = set(base) if base else set()
    if best:
        # validate
        mask = 0
        for p in best:
            mask |= 1 << p
        if not B.is_safe(mask):
            print("  WARN base invalid", flush=True)
            best = set()
    def greedy_from(occ0):
        occ = set(occ0)
        occ_bits = 0
        for p in occ:
            occ_bits |= 1 << p
        order = list(range(V))
        rng.shuffle(order)
        for p in order:
            if p in occ:
                continue
            bit = 1 << p
            ok = True
            for q in B.quads_by_pt[p]:
                if (occ_bits | bit) & q == q:
                    ok = False
                    break
            if ok:
                occ.add(p)
                occ_bits |= bit
        return occ
    def can_add(occ, p, occ_bits):
        bit = 1 << p
        for q in B.quads_by_pt[p]:
            if (occ_bits | bit) & q == q:
                return False
        return True
    def grow(occ):
        occ = set(occ)
        occ_bits = 0
        for p in occ:
            occ_bits |= 1 << p
        changed = True
        while changed:
            changed = False
            for p in range(V):
                if p not in occ and can_add(occ, p, occ_bits):
                    occ.add(p)
                    occ_bits |= 1 << p
                    changed = True
        return occ
    if not best:
        best = greedy_from(set())
    best = grow(best)
    print(f"  n={n} start best={len(best)}", flush=True)
    for t in range(iters * seeds):
        # kick and rebuild
        kicked = set(best)
        if len(kicked) > 3:
            for _ in range(rng.randint(1, 3)):
                kicked.discard(rng.choice(list(kicked)))
        cand = grow(greedy_from(kicked))
        if len(cand) > len(best):
            best = cand
            print(f"  n={n} iter {t}: new best {len(best)}", flush=True)
        elif t % 50 == 0:
            # restart from scratch occasionally
            cand2 = grow(greedy_from(set()))
            if len(cand2) > len(best):
                best = cand2
                print(f"  n={n} restart {t}: new best {len(best)}", flush=True)
    return sorted(best)

def minmax_search(n, k, trials=30000, seed=0):
    """Find a maximal safe set of size exactly k (or confirm sample failure)."""
    B = build_board(n)
    V = n * n
    rng = random.Random(seed)
    hits = []
    # method A: random exact-k sample
    for t in range(trials):
        s = rng.sample(range(V), k)
        mask = 0
        for p in s:
            mask |= 1 << p
        if B.is_safe(mask) and B.is_maximal(mask):
            hits.append(sorted(s))
            if len(hits) >= 3:
                break
    # method B: blocking construction — add points one by one keeping "all empty eventually blockable"
    if not hits:
        for t in range(trials):
            occ = 0
            chosen = []
            for step in range(k):
                # pick a random legal point that blocks the most currently-unblocked empties
                legal = B.legal_moves(occ)
                if not legal:
                    break
                # score
                scores = []
                for p in legal:
                    bit = 1 << p
                    # count empties that become blocked
                    before_free = 0
                    after_free = 0
                    # cheap: just pick random legal
                    scores.append(p)
                p = rng.choice(legal)
                occ |= 1 << p
                chosen.append(p)
            if len(chosen) == k and B.is_maximal(occ):
                hits.append(sorted(chosen))
                if len(hits) >= 3:
                    break
    return {"n": n, "k": k, "hits": hits, "n_hits": len(hits), "trials": trials}

# ---------- R(S) residual constraints ----------
def residual_constraints(B: Board, occ: int):
    """R(S): forbidden quads Q with |Q ∩ S| = 3 (each forbids the 4th point),
    plus higher: |Q ∩ S| = 2 (forbids both remaining? no — only completes if both added).
    Standard: residual game constraints are quads not yet blocked.
    A quad Q is 'active' if |Q ∩ S| = 3 (one point would complete) — these are 'edges'
    of size 1 (forbidden points). Quads with |Q∩S|=2 are '2-point constraints'.
    We count active constraints by type."""
    ones = 0  # quads with 3 in S (forbid a single point)
    twos = 0  # quads with 2 in S (pair of points cannot both be added)
    threes = 0  # quads with 1 in S
    zeros = 0
    for q in B.quads:
        c = (q & occ).bit_count()
        if c == 3:
            ones += 1
        elif c == 2:
            twos += 1
        elif c == 1:
            threes += 1
        else:
            zeros += 1
    # components of the 2-point constraint graph on empty points
    empty = [p for p in range(B.V) if not (occ >> p) & 1]
    idx = {p: i for i, p in enumerate(empty)}
    adj = defaultdict(set)
    for q in B.quads:
        c = (q & occ).bit_count()
        if c == 2:
            pts = [i for i in range(B.V) if (q >> i) & 1 and not (occ >> i) & 1]
            if len(pts) == 2:
                a, b = pts
                if a in idx and b in idx:
                    adj[idx[a]].add(idx[b])
                    adj[idx[b]].add(idx[a])
    # count components
    seen = set()
    comps = 0
    for i in range(len(empty)):
        if i in seen:
            continue
        comps += 1
        stack = [i]
        seen.add(i)
        while stack:
            u = stack.pop()
            for w in adj[u]:
                if w not in seen:
                    seen.add(w)
                    stack.append(w)
    return {
        "k": occ.bit_count(),
        "ones": ones, "twos": twos, "threes": threes, "zeros": zeros,
        "n_empty": len(empty), "constraint_components": comps,
        "n_edges_2pt": sum(len(v) for v in adj.values()) // 2,
    }

def b029_b058_b059_b066_analysis(n=5):
    """Sample safe sets; measure R(S) stats vs game outcomes / nimber if available."""
    B = board_square(n)
    V = n * n
    rng = random.Random(5)
    # solve grundy for n=5 is 151k states — acceptable
    print("  solving n=5 grundy...", flush=True)
    G = B.solve_grundy()
    print(f"  n=5 grundy states: {len(G)}", flush=True)
    samples = []
    # sample across sizes
    for k in range(0, 12):
        for t in range(300):
            if k == 0:
                s = []
            else:
                s = rng.sample(range(V), k)
            mask = 0
            for p in s:
                mask |= 1 << p
            if not B.is_safe(mask):
                continue
            r = residual_constraints(B, mask)
            r["g"] = G.get(mask)
            r["is_P"] = (r["g"] == 0)
            samples.append(r)
    # B058: high-order constraint vanishing -> parity locking of P/N
    # Group by max constraint order remaining: ones>0 means 3-point constraints exist (order-3)
    # When ones=0 and twos>0: only 2-point constraints -> predicted P/N more determined?
    # Measure: among samples with ones==0, fraction where all legal-move children have same g parity
    # Simplified: fraction of samples with ones==0 that are P, vs ones>0 that are P
    def bucket(pred):
        sub = [s for s in samples if pred(s)]
        if not sub:
            return {"n": 0}
        nP = sum(1 for s in sub if s["is_P"])
        return {"n": len(sub), "nP": nP, "P_rate": nP / len(sub),
                "mean_comps": sum(s["constraint_components"] for s in sub) / len(sub)}
    # B059: same-k residual types
    by_k = defaultdict(list)
    for s in samples:
        sig = (s["ones"], s["twos"], s["threes"], s["constraint_components"])
        by_k[s["k"]].append(sig)
    type_counts = {str(k): len(set(v)) for k, v in by_k.items()}
    total_by_k = {str(k): len(v) for k, v in by_k.items()}
    # B066: correlation between twos-overlap and P/N
    # proxy: constraint_components and ones
    return {
        "ones_zero": bucket(lambda s: s["ones"] == 0),
        "ones_pos": bucket(lambda s: s["ones"] > 0),
        "twos_zero": bucket(lambda s: s["twos"] == 0),
        "twos_pos": bucket(lambda s: s["twos"] > 0),
        "distinct_R_types_by_k": type_counts,
        "n_samples_by_k": total_by_k,
        "n_total_samples": len(samples),
    }

# ---------- B020: integer relations for 5x5 P-pairs ----------
def b020_relations():
    """Re-derive the 3-rule description and try a 2-rule version."""
    B = board_square(5)
    # P-pairs: 2-stone positions with g=0
    G = B.solve_grundy()
    ppairs = []
    for i in range(25):
        for j in range(i + 1, 25):
            mask = (1 << i) | (1 << j)
            if not B.is_safe(mask):
                continue
            if G.get(mask) == 0:
                ppairs.append((i, j))
    # classify pairs by geometric invariants
    def inv(i, j):
        xi, yi = i % 5, i // 5
        xj, yj = j % 5, j // 5
        dx, dy = abs(xi - xj), abs(yi - yj)
        # chebyshev to nearest border
        def bord(x, y):
            return min(x, y, 4 - x, 4 - y)
        return (dx, dy, bord(xi, yi), bord(xj, yj), (xi + yi) % 2 == (xj + yj) % 2)
    groups = defaultdict(list)
    for a, b in ppairs:
        groups[inv(a, b)].append((a, b))
    # try: are all P-pairs described by (dx,dy) in a small set + parity + border condition?
    dx_dy = Counter((abs(a % 5 - b % 5), abs(a // 5 - b // 5)) for a, b in ppairs)
    return {
        "n_ppairs": len(ppairs),
        "dx_dy_hist": {str(k): v for k, v in dx_dy.items()},
        "n_distinct_inv_classes": len(groups),
        "class_sizes": sorted((len(v) for v in groups.values()), reverse=True)[:10],
        "sample_pairs": [[list(divmod(a, 5)[::-1]), list(divmod(b, 5)[::-1])] for a, b in ppairs[:10]],
    }

# ---------- B047: matching / pairing on P-positions ----------
def b047_matching_check(n=5):
    """For each P-position S, check if the legal-move graph has a perfect matching
    (or pairing response strategy): every legal move u has a partner v such that
    S+u+v is... actually pairing strategy: involution f on empty points such that
    f is legal response after any first move."""
    B = board_square(n)
    G = B.solve_grundy()
    # collect P positions with |S| <= 6
    p_positions = [occ for occ, g in G.items() if g == 0 and bin(occ).count("1") <= 6]
    # for each P-position, check: does there exist a fixed-point-free involution f
    # on legal_moves(S) such that for every u, f(u) is legal after u is played
    # (i.e. S+u+f(u) is safe)? That's exactly a perfect matching on the competition graph
    # where edges are "compatible pairs" (NOT competition edges).
    # Complement: matching on compatibility graph.
    matched = 0
    unmatched_examples = []
    for occ in p_positions[:2000]:
        moves = B.legal_moves(occ)
        if len(moves) < 2 or len(moves) % 2 == 1:
            # odd count -> no perfect matching
            if len(moves) % 2 == 1:
                unmatched_examples.append({"S_size": bin(occ).count("1"), "n_moves": len(moves), "reason": "odd"})
                continue
        # compatibility edges: u,v both playable in either order -> S+u+v safe
        m = len(moves)
        adj = [[] for _ in range(m)]
        for i in range(m):
            for j in range(i + 1, m):
                if B.is_safe(occ | (1 << moves[i]) | (1 << moves[j])):
                    adj[i].append(j)
                    adj[j].append(i)
        # check perfect matching via simple blossom-less greedy + augmenting (bipartite not general)
        # use a simple recursive matching
        match = [-1] * m
        def try_aug(u, seen):
            for w in adj[u]:
                if seen[w]:
                    continue
                seen[w] = True
                if match[w] == -1 or try_aug(match[w], seen):
                    match[w] = u
                    match[u] = w
                    return True
            return False
        ok = True
        for u in range(m):
            if match[u] != -1:
                continue
            seen = [False] * m
            if not try_aug(u, seen):
                ok = False
                break
        if ok:
            matched += 1
        else:
            if len(unmatched_examples) < 5:
                unmatched_examples.append({"S_size": bin(occ).count("1"), "n_moves": len(moves), "reason": "no perfect matching"})
    return {
        "n_p_positions_sampled": min(2000, len(p_positions)),
        "n_p_positions_total_le6": len(p_positions),
        "with_perfect_matching": matched,
        "examples_without": unmatched_examples[:5],
    }

if __name__ == "__main__":
    print("=== B020 relations ===", flush=True)
    OUT["b020"] = b020_relations()
    save()
    print("=== B047 matching n=5 ===", flush=True)
    OUT["b047"] = b047_matching_check(5)
    save()
    print("=== R(S) analysis n=5 ===", flush=True)
    OUT["r_analysis"] = b029_b058_b059_b066_analysis(5)
    save()
    print("=== K10 improvement ===", flush=True)
    # start from known 18-stone if we have one
    n10 = OUT.get("k_s_search", {}).get("n10", {})
    base = n10.get("max_safe_witness")
    print("  base", base, flush=True)
    w = maxsafe_search(10, iters=15, seeds=8, base=base)
    OUT.setdefault("k10_search", {})
    OUT["k10_search"]["improved"] = {"size": len(w), "witness": w}
    save()
    print("  K10 best", len(w), flush=True)
    print("=== s_9 k=8,9 ===", flush=True)
    OUT.setdefault("s_search", {})
    OUT["s_search"]["n9_k8"] = minmax_search(9, 8, trials=20000, seed=11)
    save()
    print("  n9k8", OUT["s_search"]["n9_k8"]["n_hits"], flush=True)
    OUT["s_search"]["n9_k9"] = minmax_search(9, 9, trials=20000, seed=12)
    save()
    print("  n9k9", OUT["s_search"]["n9_k9"]["n_hits"], flush=True)
    print("=== s_10 k=9,10 ===", flush=True)
    OUT["s_search"]["n10_k9"] = minmax_search(10, 9, trials=20000, seed=13)
    save()
    print("  n10k9", OUT["s_search"]["n10_k9"]["n_hits"], flush=True)
    OUT["s_search"]["n10_k10"] = minmax_search(10, 10, trials=20000, seed=14)
    save()
    print("  n10k10", OUT["s_search"]["n10_k10"]["n_hits"], flush=True)
    print("WAVE3 DONE", flush=True)
