#!/usr/bin/env python3
"""Round5 B020-B090: independent T*/WFT/flip/bounds checks.

Outputs research/verification/round5_b020_b090.json
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from itertools import combinations

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kyouen_core import Board, square_points  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "round5_b020_b090.json")


def full_grundy(board: Board) -> dict[int, int]:
    """g for all safe sets, computed by size layer (topological)."""
    g = {}
    # collect all safe sets by BFS from 0
    by_k = defaultdict(list)
    seen = {0}
    stack = [0]
    while stack:
        s = stack.pop()
        by_k[s.bit_count()].append(s)
        for v in board.legal_moves(s):
            t = s | (1 << v)
            if t not in seen:
                seen.add(t)
                stack.append(t)
    # children have MORE stones, so compute from large k down to 0
    for k in sorted(by_k, reverse=True):
        for s in by_k[k]:
            vals = []
            for v in board.legal_moves(s):
                t = s | (1 << v)
                vals.append(g[t])
            # mex
            m = 0
            sv = set(vals)
            while m in sv:
                m += 1
            g[s] = m
    return g


def tstar_wft(board: Board, g: dict[int, int]):
    """T*(S) and WFT(S) for all S. Returns dicts."""
    # T*(S): winner-preserving reachable terminal sizes
    # N: move to P children; P: any legal move
    # WFT(S): t such that winner can force exactly t
    # N: union over winning moves of WFT(child)
    # P: intersection over all legal moves of WFT(child)
    # terminal: T*=WFT={|S|} if we count the terminal itself
    by_k = defaultdict(list)
    for s in g:
        by_k[s.bit_count()].append(s)
    T = {}
    W = {}
    for k in sorted(by_k, reverse=True):
        for s in by_k[k]:
            moves = board.legal_moves(s)
            if not moves:
                T[s] = {k}
                W[s] = {k}
                continue
            gs = g[s]
            if gs == 0:
                # P: any move
                tsets = [T[s | (1 << v)] for v in moves]
                t_union = set()
                for ts in tsets:
                    t_union |= ts
                T[s] = t_union
                wsets = [W[s | (1 << v)] for v in moves]
                w_inter = set(wsets[0])
                for ws in wsets[1:]:
                    w_inter &= ws
                W[s] = w_inter
            else:
                # N: only moves to P
                p_moves = [v for v in moves if g[s | (1 << v)] == 0]
                if not p_moves:
                    # no winning move? shouldn't happen for N
                    T[s] = set()
                    W[s] = set()
                    continue
                t_union = set()
                w_union = set()
                for v in p_moves:
                    t_union |= T[s | (1 << v)]
                    w_union |= W[s | (1 << v)]
                T[s] = t_union
                W[s] = w_union
    return T, W


def flip_rates(board: Board, g: dict[int, int]):
    """Exact P/N flip rate under 1-stone move S -> S-{p}+{q}."""
    by_k = defaultdict(list)
    for s in g:
        by_k[s.bit_count()].append(s)
    rows = {}
    for k in sorted(by_k):
        total = 0
        flips = 0
        for s in by_k[k]:
            stones = [v for v in range(board.V) if s & (1 << v)]
            empties = [v for v in range(board.V) if not (s & (1 << v))]
            for p in stones:
                base = s ^ (1 << p)
                for q in empties:
                    t = base | (1 << q)
                    if t not in g:
                        continue
                    total += 1
                    if (g[s] == 0) != (g[t] == 0):
                        flips += 1
        rows[k] = {"moves": total, "flips": flips,
                   "rate": (flips / total) if total else None}
    return rows


def b_bounds(board: Board, g: dict[int, int], max_k: int = 6):
    """b_S(p) quadratic/linear bound check on safe sets up to max_k."""
    qset = set(board.quads)
    by_k = defaultdict(list)
    for s in g:
        if s.bit_count() <= max_k:
            by_k[s.bit_count()].append(s)
    bad_quad = []
    max_b_over_k = 0.0
    examples = []
    max_b_seen = 0
    for k in sorted(by_k):
        if k < 3:
            continue
        bound = (k * (k - 1)) // 6
        for s in by_k[k]:
            stones = [v for v in range(board.V) if s & (1 << v)]
            empties = [v for v in range(board.V) if not (s & (1 << v))]
            for p in empties:
                b = 0
                for T in combinations(stones, 3):
                    m = (1 << T[0]) | (1 << T[1]) | (1 << T[2]) | (1 << p)
                    if m in qset:
                        b += 1
                if b > bound:
                    bad_quad.append({"k": k, "S": s, "p": p, "b": b, "bound": bound})
                if b > max_b_seen:
                    max_b_seen = b
                if k > 0 and b / k > max_b_over_k:
                    max_b_over_k = b / k
                    examples = [{"k": k, "b": b, "ratio": b / k}]
    return {"bad_quad_count": len(bad_quad), "bad_quad": bad_quad[:5],
            "max_b_seen": max_b_seen,
            "max_b_over_k": max_b_over_k, "examples": examples}


def main():
    results = {}
    for n in (4, 5):
        print(f"=== n={n} ===", flush=True)
        board = Board(square_points(n), f"n{n}")
        print(f"  quads={len(board.quads)}", flush=True)
        g = full_grundy(board)
        print(f"  states={len(g)}", flush=True)
        g_empty = g[0]
        win_first = [v for v in range(board.V) if g[1 << v] == 0]
        T, W = tstar_wft(board, g)
        T0 = sorted(T[0])
        W0 = sorted(W[0])
        print(f"  g_empty={g_empty} win_first={len(win_first)} T*={T0} WFT={W0}", flush=True)
        # B032: shortest/longest winning firsts
        # forced length = min/max over winner's strategies of terminal size
        # use WFT and T* of {p}
        short_c, long_c = [], []
        for p in win_first:
            sp = 1 << p
            ts = T[sp]
            short_c.append((p, min(ts)))
            long_c.append((p, max(ts)))
        if short_c:
            min_s = min(x[1] for x in short_c)
            max_l = max(x[1] for x in long_c)
            short_set = {p for p, v in short_c if v == min_s}
            long_set = {p for p, v in long_c if v == max_l}
            b032 = {
                "min_T": min_s, "max_T": max_l,
                "short_set": sorted(short_set),
                "long_set": sorted(long_set),
                "disjoint": len(short_set & long_set) == 0,
            }
        else:
            b032 = {"note": "no winning first moves"}
        # B039 exact flips
        flips = flip_rates(board, g)
        print(f"  flips done", flush=True)
        # B072 bounds
        bounds = b_bounds(board, g, max_k=min(6, board.V))
        print(f"  bounds done", flush=True)
        # B050: losing first-move games: is there a common quotient?
        # compare residual R structure size / mex signature
        lose = [v for v in range(board.V) if g[1 << v] != 0]
        lose_g = sorted(g[1 << v] for v in lose)
        win_g = sorted(g[1 << v] for v in win_first)
        max_k = max(s.bit_count() for s in g)
        results[f"n={n}"] = {
            "V": board.V,
            "quads": len(board.quads),
            "states": len(g),
            "g_empty": g_empty,
            "winner": "first" if g_empty != 0 else "second",
            "n_win_first": len(win_first),
            "win_first_ids": win_first,
            "lose_first_ids": lose,
            "g_win_first": win_g,
            "g_lose_first": lose_g,
            "T_star_empty": T0,
            "WFT_empty": W0,
            "B034_K_in_Tstar": max_k in T[0],
            "B034_K": max_k,
            "B032": b032,
            "flip_rows": flips,
            "b_bounds": bounds,
            "terminal_sizes": dict(Counter(
                s.bit_count() for s in g if not board.legal_moves(s))),
            "n_terminals": sum(1 for s in g if not board.legal_moves(s)),
        }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
