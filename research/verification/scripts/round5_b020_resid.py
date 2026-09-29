#!/usr/bin/env python3
"""R(S) residual and P(S) competition-graph stats for B054/B058/B059/B063/B066/B070."""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from itertools import combinations

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kyouen_core import Board, square_points  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "round5_b020_b090_resid.json")


def residual(occ: int, quads: list[int], full: int) -> list[int]:
    """Minimal residual forbidden sets: e\\S subset L(S), |e\\S| in 2..4."""
    legal_mask = full ^ occ
    cands = []
    for q in quads:
        missing = q & legal_mask
        # e\\S = q \\ S = q & legal_mask, must be nonempty subset of L
        m = missing.bit_count()
        if 1 <= m <= 4:
            # all missing points must be legal individually? definition: e\\S ⊆ L(S)
            # L(S) = points that can be added keeping safety of S∪{p}
            # For minimal R we take inclusion-minimal among these
            cands.append(missing)
    # filter to those where all bits are in L(S)
    # L(S): p legal iff S∪{p} safe i.e. no quad ⊆ S∪{p}
    L = 0
    empty = legal_mask
    v = 0
    while empty:
        if empty & 1:
            ok = True
            bit = 1 << v
            for q in quads:
                if (q & (occ | bit)) == q:
                    ok = False
                    break
            if ok:
                L |= bit
        empty >>= 1
        v += 1
    cands = [c for c in cands if (c & ~L) == 0 and c != 0]
    # inclusion-minimal
    cands = list(set(cands))
    minimal = []
    for c in cands:
        if not any((d != c and (d & c) == d) for d in cands):
            minimal.append(c)
    return minimal


def components(edges: list[tuple[int, int]], nverts: int) -> tuple[int, list[int]]:
    """Connected components of P(S) with vertices 0..nverts-1 (only used verts)."""
    if nverts == 0:
        return 0, []
    adj = [[] for _ in range(nverts)]
    used = set()
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
        used.add(a)
        used.add(b)
    seen = set()
    sizes = []
    for s in range(nverts):
        if s in seen or s not in used:
            continue
        stack = [s]
        seen.add(s)
        sz = 0
        while stack:
            u = stack.pop()
            sz += 1
            for w in adj[u]:
                if w not in seen:
                    seen.add(w)
                    stack.append(w)
        sizes.append(sz)
    return len(sizes), sorted(sizes)


def analyze(n: int, max_states: int = 20000):
    board = Board(square_points(n), f"n{n}")
    quads = board.quads
    full = board.full
    # BFS all safe
    seen = {0}
    stack = [0]
    states = []
    while stack:
        s = stack.pop()
        states.append(s)
        for v in board.legal_moves(s):
            t = s | (1 << v)
            if t not in seen:
                seen.add(t)
                stack.append(t)
    # sample or all
    if len(states) > max_states:
        states = states[:: max(1, len(states) // max_states)]
    r_size_hist = Counter()
    r_non2 = 0
    r_multi_comp = 0
    r_comp_hist = Counter()
    high_constraint = 0  # has 3 or 4 point residual
    ps_nv = []
    ps_ne = []
    ps_tri = []
    ps_types = Counter()
    k3_types = set()
    k4_types = set()
    flip_proxy = []
    for s in states:
        k = s.bit_count()
        R = residual(s, quads, full)
        sizes = [r.bit_count() for r in R]
        r_size_hist[tuple(sorted(sizes))] += 1
        if any(x >= 3 for x in sizes):
            high_constraint += 1
        # P(S) graph on L(S)
        L = board.legal_moves(s)
        idx = {v: i for i, v in enumerate(L)}
        edges = []
        for r in R:
            pts = [v for v in range(board.V) if r & (1 << v)]
            if len(pts) == 2:
                edges.append((idx[pts[0]], idx[pts[1]]))
        ncomp, csizes = components(edges, len(L))
        if ncomp >= 2:
            r_multi_comp += 1
        r_comp_hist[ncomp] += 1
        # type of P(S) for k=3,4
        if k in (3, 4) and len(L) <= 30:
            deg = [0] * len(L)
            for a, b in edges:
                deg[a] += 1
                deg[b] += 1
            # triangle count
            adj = [set() for _ in range(len(L))]
            for a, b in edges:
                adj[a].add(b)
                adj[b].add(a)
            tri = 0
            for a in range(len(L)):
                for b in adj[a]:
                    if b > a:
                        tri += len(adj[a] & adj[b])
            is_tree = len(edges) == max(0, len(L) - ncomp) and ncomp >= 1
            # only count used vertices
            used = set()
            for a, b in edges:
                used.add(a); used.add(b)
            nv = len(used)
            ne = len(edges)
            degs = tuple(sorted(deg[v] for v in used))
            sig = (nv, ne, degs, tri, is_tree)
            if k == 3:
                k3_types.add(sig)
            else:
                k4_types.add(sig)
    return {
        "n": n,
        "n_states_sampled": len(states),
        "r_size_hist_top": r_size_hist.most_common(8),
        "high_constraint_count": high_constraint,
        "high_constraint_rate": high_constraint / max(1, len(states)),
        "r_multi_comp_count": r_multi_comp,
        "r_multi_comp_rate": r_multi_comp / max(1, len(states)),
        "r_comp_hist": dict(r_comp_hist),
        "k3_type_count": len(k3_types),
        "k4_type_count": len(k4_types),
        "k4_not_k3_count": len(k4_types - k3_types),
        "k3_not_k4_count": len(k3_types - k4_types),
    }


def main():
    out = {}
    for n in (3, 4, 5):
        print(f"n={n} ...", flush=True)
        out[f"n={n}"] = analyze(n, max_states=8000 if n == 5 else 100000)
        print(out[f"n={n}"], flush=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
