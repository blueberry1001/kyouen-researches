#!/usr/bin/env python3
"""Lightweight follow-ups + 18-witness neighborhood analysis on 10x10."""
from __future__ import annotations
import json, sys, itertools
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
from kyouen_core import Board, board_square, board_rect

OUT = ROOT / "research" / "verification" / "round5_b020b_extra.json"
results = {}

def build_nx(n):
    return board_square(n)

# ---------- 10x10 18-witness neighborhood ----------
def b082_neighborhood():
    # Build 10x10 board in Python (may take a bit)
    print("building 10x10...", flush=True)
    b = board_square(10)
    print(f"quads={len(b.quads)}", flush=True)
    S = [1,8,15,20,21,26,38,39,41,54,70,72,73,82,86,88,93,99]
    occ = 0
    for p in S:
        occ |= (1 << p)
    # for each empty point, how many quads block it (quads where 3 of 4 in S+{p})
    block_counts = {}
    almost = []
    for p in range(100):
        if (occ >> p) & 1:
            continue
        # count blocking quads: Q with p in Q and |Q ∩ S| = 3
        cnt = 0
        blockers = []
        for q in b.quads_by_pt[p]:
            if (q & occ).bit_count() == 3:
                cnt += 1
                blockers.append([i for i in range(100) if (q >> i) & 1])
        block_counts[p] = cnt
        if cnt <= 3:
            almost.append((p, cnt, blockers))
    # for each pair of points in S, try removing and see best extension
    # (already done in C++; here just report almost-legal points)
    hist = Counter(block_counts.values())
    results["b082_neighborhood"] = {
        "n_almost_le3": len(almost),
        "block_hist": dict(sorted(hist.items())),
        "almost_sample": [{"p": p, "blocks": c, "blockers": bl[:4]} for p, c, bl in almost[:12]],
    }

# ---------- B020 independent P-pair recount (n=5) ----------
def b020():
    b = board_square(5)
    g = b.solve_grundy()
    p_pairs = []
    for i in range(25):
        for j in range(i+1, 25):
            occ = (1 << i) | (1 << j)
            if b.is_safe(occ) and g.get(occ) == 0:
                p_pairs.append((i, j))
    def pt(p): return (p % 5, p // 5)
    fam = Counter()
    for i, j in p_pairs:
        xi, yi = pt(i); xj, yj = pt(j)
        dx, dy = abs(xi-xj), abs(yi-yj)
        ci = xi in (0,4) and yi in (0,4)
        cj = xj in (0,4) and yj in (0,4)
        if ci and cj:
            fam[f"corner-corner d2={dx*dx+dy*dy}"] += 1
        elif ci or cj:
            fam[f"corner-boundary dx={dx} dy={dy}"] += 1
        else:
            fam[f"interior dx={dx} dy={dy}"] += 1
    results["b020"] = {"n_p_pairs": len(p_pairs), "family_hist": dict(fam),
                       "pairs_xy": [(pt(i), pt(j)) for i,j in p_pairs]}

# ---------- B032/B034 small rectangles only ----------
def b032_b034():
    rows = []
    for w, h in [(3,3),(3,4),(3,5),(4,4),(4,5),(2,6),(3,6),(5,5)]:
        b = board_rect(w, h)
        print(f"  rect {w}x{h} V={b.V} quads={len(b.quads)}", flush=True)
        g = b.solve_outcomes()
        g_empty = g.get(0)
        # T* with round5 definition
        memo_T = {}
        def Tstar(occ):
            if occ in memo_T:
                return memo_T[occ]
            mv = b.legal_moves(occ)
            if not mv:
                memo_T[occ] = frozenset([occ.bit_count()])
                return memo_T[occ]
            is_n = g[occ] == 1
            acc = set()
            for u in mv:
                ch = occ | (1 << u)
                if is_n:
                    if g.get(ch, 0) == 0:
                        acc |= Tstar(ch)
                else:
                    acc |= Tstar(ch)
            memo_T[occ] = frozenset(acc)
            return memo_T[occ]
        T0 = Tstar(0)
        win_moves = []
        for u in b.legal_moves(0):
            ch = 1 << u
            if g.get(ch, 0) == 0:
                t = Tstar(ch)
                win_moves.append((u, min(t), max(t), sorted(t)))
        K = None
        try:
            K = b.max_safe_size()
        except Exception as e:
            K = f"err:{e}"
        rec = {
            "board": f"{w}x{h}", "V": b.V,
            "g_empty": g_empty,
            "first_wins": g_empty == 1,
            "T_empty": sorted(T0),
            "K": K,
            "K_in_T_empty": (K in T0) if isinstance(K, int) else None,
            "T_parity": sorted({x % 2 for x in T0}),
        }
        if win_moves:
            mins = [m for _, m, _, _ in win_moves]
            maxs = [M for _, _, M, _ in win_moves]
            shortest = {u for u, m, M, _ in win_moves if m == min(mins)}
            longest = {u for u, m, M, _ in win_moves if M == max(maxs)}
            rec.update({
                "n_win_first": len(win_moves),
                "min_t": min(mins), "max_t": max(maxs),
                "shortest": sorted(shortest),
                "longest": sorted(longest),
                "disjoint": len(shortest & longest) == 0,
                "first_move_T": {str(u): sorted(t) for u, m, M, t in win_moves},
            })
        rows.append(rec)
    results["b032_b034_rects"] = rows

# ---------- B047 on n=4,5 ----------
def b047():
    for n in (4, 5):
        b = board_square(n)
        g = b.solve_grundy()
        p_states = [occ for occ, gv in g.items() if gv == 0 and occ.bit_count() >= 3]
        n_two_only = 0
        n_reg = 0
        wits = []
        for occ in p_states:
            S = [i for i in range(b.V) if (occ >> i) & 1]
            # residual edge sizes |A| = |Q \ S| for quads with |Q∩S|>=2
            edge_sizes = []
            only2 = True
            for q in b.quads:
                inter = (q & occ).bit_count()
                if inter < 2:
                    continue
                rem = (q & ~occ & b.full).bit_count()
                edge_sizes.append(rem)
                if rem != 2:
                    only2 = False
            if not only2:
                continue
            n_two_only += 1
            L = b.legal_moves(occ)
            adj = {u: set() for u in L}
            for q in b.quads:
                rem = q & ~occ & b.full
                if rem.bit_count() == 2:
                    us = [i for i in range(b.V) if (rem >> i) & 1]
                    if us[0] in adj and us[1] in adj:
                        adj[us[0]].add(us[1]); adj[us[1]].add(us[0])
            degs = [len(adj[u]) for u in L] if L else []
            if L and degs and len(set(degs)) == 1 and degs[0] > 0:
                # connected?
                seen = {L[0]}; st = [L[0]]
                while st:
                    u = st.pop()
                    for v in adj[u]:
                        if v not in seen:
                            seen.add(v); st.append(v)
                if len(seen) == len(L):
                    n_reg += 1
                    if len(wits) < 5:
                        wits.append({"S": S, "L": L, "deg": degs[0],
                                     "adj": {u: sorted(adj[u]) for u in L}})
        results[f"b047_n{n}"] = {
            "n_p_ge3": len(p_states),
            "n_two_only": n_two_only,
            "n_reg_connected": n_reg,
            "witnesses": wits,
        }

# ---------- B059: residual size-seq vs abstract (n=4) ----------
def b059():
    b = board_square(4)
    def d4_images(S):
        pts = [(i % 4, i // 4) for i in S]
        ims = set()
        for fx in (0, 1):
            for fy in (0, 1):
                for sw in (0, 1):
                    out = []
                    for x, y in pts:
                        if fx: x = 3 - x
                        if fy: y = 3 - y
                        if sw: x, y = y, x
                        out.append(y * 4 + x)
                    ims.add(tuple(sorted(out)))
        return ims
    seen = set()
    size_types = Counter()
    abs_types = Counter()
    n_orb = 0
    for occ in range(1, 1 << 16):
        if occ.bit_count() < 2:
            continue
        if not b.is_safe(occ):
            continue
        key = tuple(i for i in range(16) if (occ >> i) & 1)
        if key in seen:
            continue
        for im in d4_images(key):
            seen.add(im)
        n_orb += 1
        edges = []
        for q in b.quads:
            rem = q & ~occ & b.full
            if (q & occ).bit_count() >= 2 and rem.bit_count() > 0:
                edges.append(tuple(sorted(i for i in range(16) if (rem >> i) & 1)))
        size_types[tuple(sorted(len(e) for e in edges))] += 1
        esz = Counter(len(e) for e in edges)
        deg = Counter()
        for e in edges:
            for u in e:
                deg[u] += 1
        abs_types[(tuple(sorted(esz.items())), tuple(sorted(deg.values())))] += 1
    results["b059"] = {
        "d4_orbits": n_orb,
        "size_seq_types": len(size_types),
        "abstract_types": len(abs_types),
        "top_size_seq": size_types.most_common(8),
    }

# ---------- B074: b_S(p) on samples ----------
def b074():
    def max_b(board, sets):
        best_abs = 0
        best_ratio = 0.0
        rec = None
        for S in sets:
            occ = 0
            for p in S:
                occ |= (1 << p)
            k = len(S)
            if k < 3:
                continue
            for p in range(board.V):
                if (occ >> p) & 1:
                    continue
                cnt = 0
                for q in board.quads_by_pt[p]:
                    if (q & occ).bit_count() == 3:
                        cnt += 1
                if cnt > best_abs:
                    best_abs = cnt
                    rec = (S, p, k, cnt, cnt/k if k else 0)
                if k and cnt / k > best_ratio:
                    best_ratio = cnt / k
        return {"max_abs": best_abs, "max_ratio": best_ratio,
                "rec_k": rec[2] if rec else None,
                "rec_b": rec[3] if rec else None,
                "rec_bound": (rec[2]*(rec[2]-1)//6) if rec else None}

    import random
    rng = random.Random(1)
    def rand_max(board, n):
        out = []
        for _ in range(n):
            occ = 0
            order = list(range(board.V))
            rng.shuffle(order)
            for p in order:
                if board.is_safe(occ | (1 << p)):
                    occ |= (1 << p)
            ch = True
            while ch:
                ch = False
                for p in range(board.V):
                    if not ((occ >> p) & 1) and board.is_safe(occ | (1 << p)):
                        occ |= (1 << p)
                        ch = True
            out.append([i for i in range(board.V) if (occ >> i) & 1])
        return out

    b4 = board_square(4)
    b5 = board_square(5)
    b6 = board_square(6)
    results["b074"] = {
        "n4_200": max_b(b4, rand_max(b4, 200)),
        "n5_150": max_b(b5, rand_max(b5, 150)),
        "n6_60": max_b(b6, rand_max(b6, 60)),
    }

# ---------- B063: induced subgraphs of 3-stone P(S) ----------
def b063():
    # For all 3-stone safe S with g=0 on n=3,4,5 (sample for n=5),
    # record the competition graph P(S) on L(S) (edge if pair cannot both be added).
    # Then collect the set of graph isomorphism types (by degree seq + n edges + triangle count).
    sigs_3 = Counter()
    sigs_4 = Counter()
    for n, sigs in ((3, sigs_3), (4, sigs_4)):
        b = board_square(n)
        g = b.solve_grundy()
        for occ, gv in g.items():
            if occ.bit_count() != 3 or gv != 0:
                continue
            L = b.legal_moves(occ)
            adj = {u: set() for u in L}
            for q in b.quads:
                rem = q & ~occ & b.full
                if rem.bit_count() == 2 and (q & occ).bit_count() >= 2:
                    us = [i for i in range(b.V) if (rem >> i) & 1]
                    if us[0] in adj and us[1] in adj:
                        adj[us[0]].add(us[1]); adj[us[1]].add(us[0])
            # also 1-point residual bans: points that cannot be added at all (not in L)
            # P(S) is on L only
            nv = len(L)
            ne = sum(len(v) for v in adj.values()) // 2
            degs = tuple(sorted(len(adj[u]) for u in L))
            # triangle count
            tri = 0
            for u in L:
                for v in adj[u]:
                    if v > u:
                        tri += len(adj[u] & adj[v])
            sigs[(nv, ne, degs, tri)] += 1
    results["b063"] = {
        "n3_types": len(sigs_3),
        "n4_types": len(sigs_4),
        "n3_sigs": sorted(sigs_3.keys())[:20],
        "n4_sigs_sample": sorted(sigs_4.keys())[:20],
    }

def main():
    print("b020", flush=True); b020()
    print("b032/b034", flush=True); b032_b034()
    print("b047", flush=True); b047()
    print("b059", flush=True); b059()
    print("b063", flush=True); b063()
    print("b074", flush=True); b074()
    print("b082 neighborhood", flush=True); b082_neighborhood()
    OUT.write_text(json.dumps(results, indent=2, default=str))
    print("wrote", OUT)

if __name__ == "__main__":
    main()
