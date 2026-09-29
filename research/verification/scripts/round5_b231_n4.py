#!/usr/bin/env python3
"""ROUND5 B231-B250: n=4 full enumeration feeding several cards.

Integer-only. Writes round5_b231_n4.json.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from itertools import combinations, permutations

sys.path.insert(0, r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\scripts")
from kyouen_core import Board, board_square  # noqa: E402


def residual_graph(board: Board, occ: int) -> tuple[list[int], dict[int, list[int]]]:
    """Vertices = legal moves. Edge {p,q} iff S∪{p,q} is not safe
    (some forbidden quad contains both p,q and two stones of S)."""
    moves = board.legal_moves(occ)
    vs = moves
    adj = {v: [] for v in vs}
    vset = set(vs)
    for i in range(len(vs)):
        for j in range(i + 1, len(vs)):
            p, q = vs[i], vs[j]
            # conflict iff any quad containing both p,q is subset of occ|{p,q}
            bad = False
            for quad in board.quads_by_pt[p]:
                if (quad >> q) & 1:
                    rest = quad & ~(1 << p) & ~(1 << q)
                    if rest and (rest & ~occ) == 0 and (rest & occ) == rest:
                        # rest subset of occ (2 stones of S)
                        bad = True
                        break
            # also: quad = {p,q} + 2 stones; rest bitcount should be 2
            if not bad:
                for quad in board.quads_by_pt[p]:
                    if (quad >> q) & 1:
                        rest = quad & ~(1 << p) & ~(1 << q)
                        if rest.bit_count() == 2 and (rest & ~occ) == 0:
                            bad = True
                            break
            if bad:
                adj[p].append(q)
                adj[q].append(p)
    return vs, adj


def components(adj: dict[int, list[int]]) -> list[list[int]]:
    seen = set()
    comps = []
    for v in adj:
        if v in seen:
            continue
        stack = [v]
        seen.add(v)
        comp = []
        while stack:
            u = stack.pop()
            comp.append(u)
            for w in adj[u]:
                if w not in seen:
                    seen.add(w)
                    stack.append(w)
        comps.append(sorted(comp))
    return comps


def is_tree(comp: list[int], adj: dict[int, list[int]]) -> bool:
    if not comp:
        return False
    n = len(comp)
    edges = 0
    for v in comp:
        edges += sum(1 for w in adj[v] if w in comp)
    edges //= 2
    return edges == n - 1


def deg_seq_tree_shape(comp: list[int], adj: dict[int, list[int]]) -> tuple:
    """Sorted degree sequence of the induced subgraph (tree shape invariant)."""
    return tuple(sorted(sum(1 for w in adj[v] if w in comp) for v in comp))


def canonical_graph(nverts: int, edge_set: set[tuple[int, int]]) -> tuple:
    """Canonical adjacency bitmask over all labelings (nverts <= 6)."""
    best = None
    verts = list(range(nverts))
    # build adj matrix
    adjm = [[0] * nverts for _ in range(nverts)]
    for a, b in edge_set:
        adjm[a][b] = adjm[b][a] = 1
    for perm in permutations(verts):
        bits = 0
        k = 0
        for i in range(nverts):
            for j in range(i + 1, nverts):
                if adjm[perm[i]][perm[j]]:
                    bits |= 1 << k
                k += 1
        if best is None or bits < best:
            best = bits
    return best


def main() -> None:
    n = 4
    board = board_square(n)
    V = board.V
    print(f"n={n} V={V} quads={len(board.quads)}", flush=True)

    # Full Grundy over all safe sets
    grundy = board.solve_grundy()
    safe_sets = sorted(grundy.keys())
    print(f"safe_sets={len(safe_sets)}", flush=True)

    # Precompute legal moves / residual for each state we touch
    legal = {}
    res_adj = {}
    res_comps = {}
    for occ in safe_sets:
        mv = board.legal_moves(occ)
        legal[occ] = mv
        vs, adj = residual_graph(board, occ)
        res_adj[occ] = adj
        res_comps[occ] = components(adj)

    # --- B231: grundy histogram ---
    g_hist = Counter(grundy.values())
    max_g = max(g_hist)
    achieved = sorted(g_hist.keys())
    b231 = {
        "n": n,
        "max_g": max_g,
        "achieved_g": achieved,
        "g_hist": {str(k): g_hist[k] for k in sorted(g_hist)},
        "continuous_0_to_max": achieved == list(range(max_g + 1)),
    }

    # --- proof size / depth under optimal play ---
    # depth(S): number of stones played from S until terminal, under optimal
    #   (N: 1+min depth(child among winning); P: 1+max depth(child))
    # proof(S): number of distinct positions in a minimal AND/OR proof
    #   (N: 1+min proof(child among winning); P: 1+sum proof(child all children))
    sys.setrecursionlimit(20000)
    depth_m: dict[int, int] = {}
    proof_m: dict[int, int] = {}
    # order by |S| decreasing so children first
    by_size = sorted(safe_sets, key=lambda s: -s.bit_count())

    def children(occ: int) -> list[int]:
        return [occ | (1 << v) for v in legal[occ]]

    for occ in by_size:
        ch = children(occ)
        g = grundy[occ]
        if not ch:
            depth_m[occ] = 0
            proof_m[occ] = 1
            continue
        if g == 0:  # P
            depth_m[occ] = 1 + max(depth_m[c] for c in ch)
            proof_m[occ] = 1 + sum(proof_m[c] for c in ch)
        else:  # N: choose winning child (g(c)==0) minimising
            win = [c for c in ch if grundy[c] == 0]
            # every N position has a winning move
            depth_m[occ] = 1 + min(depth_m[c] for c in win)
            proof_m[occ] = 1 + min(proof_m[c] for c in win)

    # --- B244: max stones on proof-terminal P positions / max depth vs K ---
    K = board.max_safe_size()
    p_by_stones = Counter()
    for occ, g in grundy.items():
        if g == 0:
            p_by_stones[occ.bit_count()] += 1
    max_p_stones = max(p_by_stones) if p_by_stones else 0
    max_depth = max(depth_m.values()) if depth_m else 0
    # games that end (terminal = no moves) stones
    term_stones = [occ.bit_count() for occ in safe_sets if not legal[occ]]
    b244 = {
        "K": K,
        "max_depth_from_empty": depth_m[0],
        "max_depth_over_all": max_depth,
        "max_P_stones": max_p_stones,
        "K_gt_max_P_stones": K > max_p_stones,
        "P_stones_hist": {str(k): p_by_stones[k] for k in sorted(p_by_stones)},
        "terminal_stones_hist": {str(k): term_stones.count(k) for k in sorted(set(term_stones))},
        "max_terminal_stones": max(term_stones) if term_stones else 0,
    }

    # --- B247: minimisers of proof vs depth disjoint ---
    disjoint = []
    for occ in safe_sets:
        if grundy[occ] == 0:
            continue
        ch = children(occ)
        win = [c for c in ch if grundy[c] == 0]
        if len(win) <= 1:
            continue
        best_d = min(depth_m[c] for c in win)
        best_p = min(proof_m[c] for c in win)
        set_d = {c for c in win if depth_m[c] == best_d}
        set_p = {c for c in win if proof_m[c] == best_p}
        if set_d.isdisjoint(set_p):
            # record one witness: the move (point) not the child mask
            def move_of(child: int) -> int:
                diff = child ^ occ
                return diff.bit_length() - 1

            disjoint.append({
                "occ": occ,
                "stones": occ.bit_count(),
                "g": grundy[occ],
                "n_win": len(win),
                "depth_min": best_d,
                "proof_min": best_p,
                "depth_min_moves": [move_of(c) for c in sorted(set_d, key=lambda x: x.bit_count())],
                "proof_min_moves": [move_of(c) for c in sorted(set_p, key=lambda x: x.bit_count())],
            })
    b247 = {
        "n_disjoint_minimisers": len(disjoint),
        "witnesses": disjoint[:8],
    }

    # --- B236: longest chain of unique winning moves ---
    # Walk: at each N node, if exactly one winning move, take it; measure how
    # many consecutive player-to-move steps this holds along optimal play.
    def unique_win_chain(occ: int) -> int:
        cur = occ
        chain = 0
        while True:
            if grundy[cur] == 0:
                break
            ch = children(cur)
            win = [c for c in ch if grundy[c] == 0]
            if len(win) != 1:
                break
            chain += 1
            cur = win[0]
            # opponent replies: if multiple opponent moves, the chain is about
            # *our* unique winning moves; opponent choice may vary. We stop at
            # first opponent node with !=1 winning? No: B236 says "勝者の最初の
            # r回の手番で、相手のどの応手に対してもPへ進む手がただ一つ".
            # So after opponent replies, we must still have unique winning move
            # against EVERY opponent reply. We cannot continue on a single path.
            break
        return chain

    # Stronger measure: BFS over pairs (pos) from empty; count max r such that
    # there exists a strategy where for r consecutive winner turns the winning
    # move is unique and works against all opponent replies.
    def unique_win_depth(occ: int, winner_is_first: bool, r_cap: int = 20) -> int:
        """Max r (winner's turns with unique winning move, robust to all opp replies)."""
        from functools import lru_cache

        @lru_cache(maxsize=None)
        def rec(state: int, to_move_is_winner: bool) -> int:
            g = grundy[state]
            if to_move_is_winner:
                if g == 0:
                    return 0
                ch = children(state)
                win = [c for c in ch if grundy[c] == 0]
                if len(win) != 1:
                    return 0
                child = win[0]
                opp = children(child)
                if not opp:
                    return 1
                vals = [rec(o, True) for o in opp]
                return 1 + min(vals)
            else:
                ch = children(state)
                if not ch:
                    return 0
                vals = [rec(c, True) for c in ch]
                return min(vals)

        return rec(occ, winner_is_first)

    # From empty: first player is winner iff g(empty)!=0
    g0 = grundy[0]
    b236_depth = unique_win_depth(0, True) if g0 != 0 else 0
    # Also scan all N positions for max unique-win-robust depth
    max_uwd = 0
    uwd_witness = None
    for occ in safe_sets:
        if grundy[occ] == 0:
            continue
        d = unique_win_depth(occ, True)
        if d > max_uwd:
            max_uwd = d
            uwd_witness = occ
    b236 = {
        "g0": g0,
        "unique_win_depth_from_empty": b236_depth,
        "max_unique_win_robust_depth": max_uwd,
        "witness_occ": uwd_witness,
        "witness_stones": uwd_witness.bit_count() if uwd_witness is not None else None,
    }

    # --- B237: component count jump after one move ---
    max_comp_before = 0
    max_comp_after = 0
    max_jump = 0
    jump_witness = None
    comp_hist = Counter()
    for occ in safe_sets:
        comps = res_comps[occ]
        cn = len(comps)
        comp_hist[cn] += 1
        if cn > max_comp_before:
            max_comp_before = cn
        for v in legal[occ]:
            nxt = occ | (1 << v)
            cn2 = len(res_comps[nxt])
            if cn2 > max_comp_after:
                max_comp_after = cn2
            jump = cn2 - cn
            if jump > max_jump:
                max_jump = jump
                jump_witness = (occ, v, cn, cn2)
    b237 = {
        "max_comp_count_over_S": max_comp_before,
        "max_comp_count_after_move": max_comp_after,
        "max_jump": max_jump,
        "comp_hist": {str(k): comp_hist[k] for k in sorted(comp_hist)},
        "witness": jump_witness,
    }

    # --- B238: switch points (round4 formalization) ---
    # p is switch for (S,q1,q2) if g(S+q1)=g(S+q2), p legal in both,
    # g(S+q1+p) != g(S+q2+p)
    switch_found = []
    for occ in safe_sets:
        mv = legal[occ]
        gvals = {}
        for q in mv:
            gvals[q] = grundy[occ | (1 << q)]
        for i in range(len(mv)):
            for j in range(i + 1, len(mv)):
                q1, q2 = mv[i], mv[j]
                if gvals[q1] != gvals[q2]:
                    continue
                s1 = occ | (1 << q1)
                s2 = occ | (1 << q2)
                common = set(legal[s1]) & set(legal[s2])
                for p in common:
                    g1 = grundy[s1 | (1 << p)]
                    g2 = grundy[s2 | (1 << p)]
                    if g1 != g2:
                        switch_found.append({
                            "occ": occ, "q1": q1, "q2": q2, "p": p,
                            "g_q": gvals[q1],
                            "g_after_p_1": g1, "g_after_p_2": g2,
                        })
                        break
                if switch_found and switch_found[-1].get("occ") == occ and len(switch_found) > 50:
                    break
            if len(switch_found) > 50:
                break
        if len(switch_found) > 50:
            break
    b238 = {
        "n_switch_witnesses": len(switch_found),
        "examples": switch_found[:6],
    }

    # --- B240: same g, different option multisets; and geometric embedding ---
    # (a) same g, different multiset of child g's
    opt_sig = {}
    for occ in safe_sets:
        child_g = tuple(sorted(grundy[c] for c in children(occ)))
        opt_sig.setdefault(grundy[occ], set()).add(child_g)
    multi_sig = {g: len(sigs) for g, sigs in opt_sig.items()}
    # find explicit pair with same g, different option signatures
    pair_diff = None
    by_g = defaultdict(list)
    for occ in safe_sets:
        by_g[grundy[occ]].append(occ)
    for g, lst in by_g.items():
        sigmap = {}
        for occ in lst:
            sig = tuple(sorted(grundy[c] for c in children(occ)))
            if sig in sigmap and sigmap[sig] != occ:
                pass
            sigmap.setdefault(sig, occ)
        if len(sigmap) >= 2:
            sigs = list(sigmap.keys())
            pair_diff = {
                "g": g,
                "occ1": sigmap[sigs[0]], "sig1": sigs[0],
                "occ2": sigmap[sigs[1]], "sig2": sigs[1],
            }
            break
    # (b) geometric embedding: S1, S2 same g, exists T with
    #     g(S1+T) != g(S2+T) or outcomes differ. S1,S2,T pairwise disjoint.
    embed = None
    # search small: |S1|=|S2|=k small, T small
    occ_list = [o for o in safe_sets if 1 <= o.bit_count() <= 3]
    occ_by_g = defaultdict(list)
    for o in occ_list:
        occ_by_g[grundy[o]].append(o)
    for g, lst in occ_by_g.items():
        if len(lst) < 2:
            continue
        for a, b in combinations(lst[:40], 2):
            if a & b:
                continue
            # try small T
            used = a | b
            cands = [v for v in range(V) if not (used >> v) & 1]
            for tsize in (1, 2, 3):
                done = False
                for tverts in combinations(cands, tsize):
                    T = 0
                    for v in tverts:
                        T |= 1 << v
                    sa, sb = a | T, b | T
                    if sa in grundy and sb in grundy:
                        if grundy[sa] != grundy[sb]:
                            embed = {
                                "g_S": g,
                                "S1": a, "S2": b, "T": T,
                                "g_S1": g, "g_S2": g,
                                "g_S1T": grundy[sa], "g_S2T": grundy[sb],
                            }
                            done = True
                            break
                if done:
                    break
            if embed:
                break
        if embed:
            break
    b240 = {
        "option_sig_counts_by_g": {str(k): multi_sig[k] for k in sorted(multi_sig)},
        "pair_same_g_diff_options": pair_diff,
        "embedding_split": embed,
    }

    # --- B245: winning-move count vs proof size vs component repetition ---
    # For N positions: n_win, proof_size, number of "repeated" component shapes
    rows = []
    rep_vs_proof = []
    for occ in safe_sets:
        if grundy[occ] == 0:
            continue
        win = [c for c in children(occ) if grundy[c] == 0]
        comps = res_comps[occ]
        shapes = [deg_seq_tree_shape(c, res_adj[occ]) if is_tree(c, res_adj[occ]) else ("non-tree", len(c), sum(len(res_adj[occ][v]) for v in c) // 2) for c in comps]
        shape_counts = Counter(shapes)
        max_rep = max(shape_counts.values()) if shape_counts else 0
        n_unique = len(shape_counts)
        rows.append((len(win), proof_m[occ], max_rep, n_unique))
    # correlation: group by n_win, compare mean proof for high-rep vs low-rep
    def mean(xs):
        return sum(xs) / len(xs) if xs else 0

    hi = [r[1] for r in rows if r[2] >= 2]
    lo = [r[1] for r in rows if r[2] <= 1]
    b245 = {
        "n_N_positions": len(rows),
        "mean_proof_high_rep": mean(hi),
        "mean_proof_low_rep": mean(lo),
        "n_high_rep": len(hi),
        "n_low_rep": len(lo),
        "mean_win_high_rep": mean([r[0] for r in rows if r[2] >= 2]),
        "mean_win_low_rep": mean([r[0] for r in rows if r[2] <= 1]),
        "note": "means are rational sums/count; stored as float only for display, raw sums kept",
        "sum_proof_high_rep": sum(r[1] for r in rows if r[2] >= 2),
        "sum_proof_low_rep": sum(r[1] for r in rows if r[2] <= 1),
        "sum_win_high_rep": sum(r[0] for r in rows if r[2] >= 2),
        "sum_win_low_rep": sum(r[0] for r in rows if r[2] <= 1),
    }

    # --- B232 / B233: residual graph shapes ---
    # collect R(S) with |V|<=6: canonical form; also tree components deg-seqs
    graph_canons = set()
    graph_by_v = defaultdict(set)
    tree_shapes = set()
    nontree_comps = 0
    tree_comps = 0
    max_comp_size = 0
    for occ in safe_sets:
        adj = res_adj[occ]
        vs = list(adj.keys())
        if 1 <= len(vs) <= 6:
            # relabel
            idx = {v: i for i, v in enumerate(sorted(vs))}
            edges = set()
            for p in adj:
                for q in adj[p]:
                    if p < q:
                        edges.add((idx[p], idx[q]))
            canon = canonical_graph(len(vs), edges)
            graph_canons.add(canon)
            graph_by_v[len(vs)].add(canon)
        for c in res_comps[occ]:
            max_comp_size = max(max_comp_size, len(c))
            if is_tree(c, adj):
                tree_comps += 1
                tree_shapes.add(deg_seq_tree_shape(c, adj))
            else:
                nontree_comps += 1
    # known tree count on 1..6 vertices
    # trees: 1,1,1,2,3,6
    b232 = {
        "n_distinct_R_graphs_upto6v": len(graph_canons),
        "by_vertex_count": {str(k): len(v) for k, v in sorted(graph_by_v.items())},
    }
    b233 = {
        "tree_component_degseqs": sorted(tree_shapes),
        "n_tree_shapes": len(tree_shapes),
        "n_tree_comps": tree_comps,
        "n_nontree_comps": nontree_comps,
        "max_comp_size": max_comp_size,
    }

    # --- B248: P-positions feature split (|S|, |L|, center occupied) ---
    center = (n // 2) * n + (n // 2)  # for n=4, points (0..3); "center" = inner 2x2
    inner = {(1, 1), (1, 2), (2, 1), (2, 2)}
    inner_mask = 0
    for (x, y) in inner:
        inner_mask |= 1 << (y * n + x)
    feat_classes = defaultdict(list)
    for occ in safe_sets:
        if grundy[occ] != 0:
            continue
        f = (occ.bit_count(), len(legal[occ]), 1 if (occ & inner_mask) else 0)
        feat_classes[f].append(occ)
    # within each class, check if all P have the "same response form":
    # response form = sorted multiset of child outcomes / child g signatures
    homogeneous = 0
    heterogeneous = 0
    het_examples = []
    for f, lst in feat_classes.items():
        sigs = set()
        for occ in lst:
            sigs.add(tuple(sorted(grundy[c] for c in children(occ))))
        if len(sigs) == 1:
            homogeneous += 1
        else:
            heterogeneous += 1
            if len(het_examples) < 3:
                het_examples.append({"feat": f, "n_pos": len(lst), "n_sigs": len(sigs)})
    b248 = {
        "n_P": sum(1 for g in grundy.values() if g == 0),
        "n_feature_classes": len(feat_classes),
        "homogeneous_classes": homogeneous,
        "heterogeneous_classes": heterogeneous,
        "het_examples": het_examples,
        "feature": "(|S|, |L(S)|, touches inner 2x2)",
    }

    # --- B249: g=1, depth vs proof ---
    g1 = [occ for occ in safe_sets if grundy[occ] == 1]
    by_depth = defaultdict(list)
    for occ in g1:
        by_depth[depth_m[occ]].append(proof_m[occ])
    b249 = {
        "n_g1": len(g1),
        "max_depth_g1": max(depth_m[o] for o in g1) if g1 else 0,
        "max_proof_g1": max(proof_m[o] for o in g1) if g1 else 0,
        "max_proof_by_depth": {str(d): max(by_depth[d]) for d in sorted(by_depth)},
        "count_by_depth": {str(d): len(by_depth[d]) for d in sorted(by_depth)},
    }

    # --- B241 support data: for n=4, winning first moves and their replies ---
    # n=4 all first moves lose (g0=0), so W is empty. Record that.
    first_moves = []
    for v in range(V):
        first_moves.append(grundy[1 << v])
    b241_n4 = {
        "W_count": sum(1 for g in first_moves if g == 0),
        "note": "n=4 all 16 first moves lose (g({p}) != 0 means N after first? "
                "W = {p : g({p})=0} empty when g0=0 and all g({p})>0)",
        "g_first": first_moves,
    }

    out = {
        "n": n,
        "V": V,
        "n_quads": len(board.quads),
        "n_safe": len(safe_sets),
        "K": K,
        "b231": b231,
        "b232": b232,
        "b233": b233,
        "b236": b236,
        "b237": b237,
        "b238": b238,
        "b240": b240,
        "b244": b244,
        "b245": b245,
        "b247": b247,
        "b248": b248,
        "b249": b249,
        "b241_n4": b241_n4,
    }
    path = r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round5_b231_n4.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("WROTE", path)
    print("max_g", b231["max_g"], "K", K, "max_depth", max_depth, "max_P_stones", max_p_stones)
    print("b236", b236)
    print("b237 jump", b237["max_jump"], "comps", b237["max_comp_count_over_S"])
    print("b238 switches", b238["n_switch_witnesses"])
    print("b240 embed", b240["embedding_split"])
    print("b247 disjoint", b247["n_disjoint_minimisers"])
    print("b233 tree shapes", b233["n_tree_shapes"], b233["tree_component_degseqs"])


if __name__ == "__main__":
    main()
