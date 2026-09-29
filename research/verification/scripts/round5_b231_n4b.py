#!/usr/bin/env python3
"""ROUND5 follow-ups: missing residual graphs, B244 terminal bound, B245 stratified."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from itertools import combinations, permutations

sys.path.insert(0, r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\scripts")
from kyouen_core import Board, board_square  # noqa: E402


def residual_graph(board: Board, occ: int):
    moves = board.legal_moves(occ)
    adj = {v: [] for v in moves}
    for i in range(len(moves)):
        for j in range(i + 1, len(moves)):
            p, q = moves[i], moves[j]
            bad = False
            for quad in board.quads_by_pt[p]:
                if (quad >> q) & 1:
                    rest = quad & ~(1 << p) & ~(1 << q)
                    if rest.bit_count() == 2 and (rest & ~occ) == 0:
                        bad = True
                        break
            if bad:
                adj[p].append(q)
                adj[q].append(p)
    return moves, adj


def canon_of(adj_local: dict[int, list[int]], vs: list[int]) -> int:
    """Canonical edge-bitmask over all labelings."""
    n = len(vs)
    idx = {v: i for i, v in enumerate(vs)}
    adjm = [[0] * n for _ in range(n)]
    for p in vs:
        for q in adj_local[p]:
            adjm[idx[p]][idx[q]] = 1
    best = None
    for perm in permutations(range(n)):
        bits = 0
        k = 0
        for i in range(n):
            for j in range(i + 1, n):
                if adjm[perm[i]][perm[j]]:
                    bits |= 1 << k
                k += 1
        if best is None or bits < best:
            best = bits
    return best


def all_graph_canons(n: int) -> dict[int, int]:
    """All unlabeled graphs on n vertices -> canon id. Returns {canon: edge_count}."""
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    seen = {}
    for mask in range(1 << len(pairs)):
        edges = {pairs[k] for k in range(len(pairs)) if (mask >> k) & 1}
        # brute force perm
        best = None
        for perm in permutations(range(n)):
            bits = 0
            k = 0
            for i in range(n):
                for j in range(i + 1, n):
                    a, b = perm[i], perm[j]
                    if a > b:
                        a, b = b, a
                    if (a, b) in edges:
                        bits |= 1 << k
                    k += 1
            if best is None or bits < best:
                best = bits
        seen[best] = len(edges)
    return seen


def describe_graph(n: int, canon: int) -> str:
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    edges = [pairs[k] for k in range(len(pairs)) if (canon >> k) & 1]
    degs = [0] * n
    for a, b in edges:
        degs[a] += 1
        degs[b] += 1
    return f"n={n} edges={len(edges)} degs={sorted(degs)}"


def main() -> None:
    n = 4
    board = board_square(n)
    grundy = board.solve_grundy()
    safe_sets = sorted(grundy.keys())
    print(f"safe={len(safe_sets)}", flush=True)

    legal = {}
    res_adj = {}
    for occ in safe_sets:
        legal[occ] = board.legal_moves(occ)
        _, adj = residual_graph(board, occ)
        res_adj[occ] = adj

    # --- which unlabeled graphs on 3 and 4 vertices appear as R(S) ---
    appear = defaultdict(set)  # nverts -> set of canons
    for occ in safe_sets:
        adj = res_adj[occ]
        vs = sorted(adj.keys())
        if 1 <= len(vs) <= 5:
            # induced? R(S) vertices are ALL legal moves; graph is on all of them
            c = canon_of(adj, vs)
            appear[len(vs)].add(c)

    missing_report = {}
    for nv in (1, 2, 3, 4):
        allc = all_graph_canons(nv)
        got = appear[nv]
        miss = set(allc) - got
        missing_report[str(nv)] = {
            "total_unlabeled": len(allc),
            "appeared": len(got),
            "missing": [describe_graph(nv, c) for c in sorted(miss)],
            "appeared_desc": [describe_graph(nv, c) for c in sorted(got)],
        }
        print(f"nv={nv} appeared {len(got)}/{len(allc)} missing={missing_report[str(nv)]['missing']}")

    # --- B244: minimal proof whose terminals all have stones < K ---
    # dp_S = set of achievable (max terminal stones) via a proof from S, minimised
    # We want min over proofs of max terminal size.
    K = board.max_safe_size()
    by_size = sorted(safe_sets, key=lambda s: -s.bit_count())

    def children(occ):
        return [occ | (1 << v) for v in legal[occ]]

    # min_max_term[occ] = minimal value of (max stones among proof terminals)
    # among proofs rooted at occ.
    min_max_term = {}
    for occ in by_size:
        ch = children(occ)
        if not ch:
            min_max_term[occ] = occ.bit_count()
            continue
        if grundy[occ] == 0:
            # must include ALL children
            min_max_term[occ] = max(min_max_term[c] for c in ch)
        else:
            win = [c for c in ch if grundy[c] == 0]
            min_max_term[occ] = min(min_max_term[c] for c in win)
    b244 = {
        "K": K,
        "min_max_term_from_empty": min_max_term[0],
        "strictly_below_K": min_max_term[0] < K,
        "max_term_if_just_any_terminal": max(o.bit_count() for o in safe_sets if not legal[o]),
    }

    # --- B245: stratified by n_win ---
    # high_rep = max multiplicity of a residual-component shape >= 2
    def comps_of(adj):
        seen = set()
        out = []
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
            out.append(comp)
        return out

    def is_tree(comp, adj):
        n = len(comp)
        e = sum(1 for v in comp for w in adj[v] if w in comp) // 2
        return e == n - 1

    def shape(comp, adj):
        if is_tree(comp, adj):
            return ("T", tuple(sorted(sum(1 for w in adj[v] if w in comp) for v in comp)))
        return ("C", len(comp), sum(len(adj[v]) for v in comp) // 2)

    # proof size
    proof_m = {}
    depth_m = {}
    for occ in by_size:
        ch = children(occ)
        if not ch:
            proof_m[occ] = 1
            depth_m[occ] = 0
            continue
        if grundy[occ] == 0:
            proof_m[occ] = 1 + sum(proof_m[c] for c in ch)
            depth_m[occ] = 1 + max(depth_m[c] for c in ch)
        else:
            win = [c for c in ch if grundy[c] == 0]
            proof_m[occ] = 1 + min(proof_m[c] for c in win)
            depth_m[occ] = 1 + min(depth_m[c] for c in win)

    # stratify N positions by (n_win, max_rep)
    strata = defaultdict(list)  # (n_win, max_rep) -> [proof]
    for occ in safe_sets:
        if grundy[occ] == 0:
            continue
        win = [c for c in children(occ) if grundy[c] == 0]
        adj = res_adj[occ]
        comps = comps_of(adj)
        sc = Counter(shape(c, adj) for c in comps)
        max_rep = max(sc.values()) if sc else 0
        strata[(len(win), 1 if max_rep >= 2 else 0)].append(proof_m[occ])

    strat_summary = {}
    for (nw, rep), proofs in sorted(strata.items()):
        strat_summary[f"win{nw}_rep{rep}"] = {
            "count": len(proofs),
            "sum_proof": sum(proofs),
            "max_proof": max(proofs),
            "min_proof": min(proofs),
        }

    # within n_win=2 and n_win=3, compare proof by rep
    b245 = {"strata": strat_summary}

    out = {
        "missing_graphs": missing_report,
        "b244": b244,
        "b245": b245,
    }
    path = r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round5_b231_n4b.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("WROTE", path)
    print("b244", b244)
    print("b245 strata", json.dumps(strat_summary, indent=1)[:2000])


if __name__ == "__main__":
    main()
