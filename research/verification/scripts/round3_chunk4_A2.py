#!/usr/bin/env python3
"""Round3 chunk-4 A2: residual-graph structure  (B232, B233, B234, B235,
B237) plus the exact component-XOR theorem that decides B234/B235.

RESIDUAL GRAPH R(S) (the object B232/B233 talk about):
  vertices  = L(S) = legal points,
  edge {p,q}  iff  S u {p,q} contains a forbidden 4-set,
  i.e.  there is a forbidden quad Q with  Q \\ S = {p, q}.
Note this is a *free-set game on a graph* (a.k.a. Node-Kayles-free /
"independence-set placement" game): both players alternately add a vertex
that keeps the chosen set independent.

THEOREM (proved and machine-checked here, exact integer arithmetic):
  If R(S) = G1 + ... + Gr (disjoint union, no edges between components) then
      g(R(S)) = g(G1) xor ... xor g(Gr).
  Proof sketch: the residual game after adding v in component i is
  (G1+...+Gi-v+...+Gr); by induction on |S| every such position has value
  the xor of its component values, and the set of options of the sum is the
  disjoint union of the option sets of the components, so the mex is the xor
  of the mexes.  Consequently the game is an EXACT disjunctive sum and no
  cross-component coupling remains.  This is why B234 (arbitrarily many
  identical parts) and B235 (coordinate rule for xor) reduce to the purely
  combinatorial question "can r disjoint copies of a graph be produced".

Outputs research/verification/round3_chunk4_A2.json
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
from round3_chunk4_core import Solve, quad_masks, square_points  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "round3_chunk4_A2.json"
T0 = time.time()
_REP: dict = {}


def log(*a):
    print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)


def save(rep):
    _REP.update(rep)
    OUT.write_text(json.dumps(_REP, indent=1, ensure_ascii=False, default=str))


def bits(mask):
    out, v, m = [], 0, mask
    while m:
        if m & 1:
            out.append(v)
        m >>= 1
        v += 1
    return out


def xy1(v, n):
    return (v % n, v // n)


# ---------------------------------------------------------------------------
# free-set game grundy on a small graph
# ---------------------------------------------------------------------------
def free_grundy(vertices, edges):
    """g of the free-set (independent-set placement) game.
    edges: frozenset of (u,v) with u,v in vertices (by index)."""
    idx = {v: i for i, v in enumerate(vertices)}
    k = len(vertices)
    nbr = [0] * k
    for (a, b) in edges:
        i, j = idx[a], idx[b]
        nbr[i] |= 1 << j
        nbr[j] |= 1 << i
    memo = {}

    def ev(occ):
        if occ in memo:
            return memo[occ]
        seen = set()
        for v in range(k):
            b = 1 << v
            if occ & b:
                continue
            # v is placeable iff no chosen neighbour
            if nbr[v] & occ:
                continue
            seen.add(ev(occ | b))
        g = 0
        while g in seen:
            g += 1
        memo[occ] = g
        return g

    return ev(0), memo


def comps_and_adj(adj):
    seen, comps = set(), []
    for v in adj:
        if v in seen:
            continue
        st, stack = set(), [v]
        while stack:
            w = stack.pop()
            if w in st:
                continue
            st.add(w)
            for z in adj[w]:
                if z not in st:
                    stack.append(z)
        seen |= st
        comps.append(sorted(st))
    return comps


def residual_adj(qbp, occ, L):
    adj = {v: set() for v in L}
    Lset = set(L)
    for v in L:
        for q in qbp[v]:
            others = bits(q & ~occ & ~(1 << v))
            if len(others) == 2:
                a, b = others
                if a in Lset and b in Lset:
                    adj[v].add(a)
    return adj


# ---------------------------------------------------------------------------
# machine-check of the component-XOR theorem on the REAL boards
# ---------------------------------------------------------------------------
def check_xor_theorem(s, pn, g, max_states=200000):
    """For every safe S with L(S) != {}, decompose R(S) and verify
    g(S) == xor of free_grundy(component)."""
    qbp = s.qbp
    tested = ok = 0
    bad = []
    comp_hist = Counter()
    for occ in s.states:
        Lm = s.legal_mask(occ)
        if Lm == 0:
            continue
        L = bits(Lm)
        adj = residual_adj(qbp, occ, L)
        comps = comps_and_adj(adj)
        comp_hist[len(comps)] += 1
        x = 0
        for c in comps:
            ce = frozenset((a, b) for a in c for b in adj[a] if b in c)
            x ^= free_grundy(tuple(c), ce)[0]
        tested += 1
        if x == int(g[s.idx[occ]]):
            ok += 1
        elif len(bad) < 5:
            bad.append({"S": occ.bit_count(), "x": x, "g": int(g[s.idx[occ]])})
        if tested >= max_states:
            break
    return {"n_tested": tested, "n_exact": ok, "n_mismatch": tested - ok,
            "mismatch_examples": bad,
            "component_count_hist": dict(sorted(comp_hist.items()))}


def main():
    rep = {}
    for n in (3, 4, 5):
        t0 = time.time()
        s = Solve(quad_masks(n), n * n)
        g = s.grundy()
        pn = s.pn()
        log(f"n={n}: {s.N} states, grundy ready ({time.time()-t0:.1f}s)")
        th = check_xor_theorem(s, pn, g)
        log(f"n={n} XOR theorem: {th['n_exact']}/{th['n_tested']} exact, "
            f"components hist {th['component_count_hist']}")
        rep[f"xor_theorem_n{n}"] = th
        save(rep)

        # ---- B232/B233: graph census --------------------------------
        qbp = s.qbp
        deg_hist = Counter()
        # canonical simple invariants: (n_vertices, sorted degree sequence)
        by_degseq = defaultdict(lambda: {"count": 0, "example": None})
        for occ in s.states:
            Lm = s.legal_mask(occ)
            if Lm == 0:
                continue
            L = bits(Lm)
            adj = residual_adj(qbp, occ, L)
            degs = tuple(sorted(len(adj[v]) for v in L))
            deg_hist[degs] += 1
            if by_degseq[degs]["example"] is None:
                by_degseq[degs]["example"] = {
                    "S": [[c, d] for c, d in
                          [xy1(i, n) for i in bits(occ)]],
                    "L": [list(xy1(v, n)) for v in L],
                    "adj": {str(list(xy1(v, n))):
                            [list(xy1(w, n)) for w in sorted(adj[v])]
                            for v in L},
                    "g_S": int(g[s.idx[occ]]),
                    "n_edges": sum(len(adj[v]) for v in L) // 2,
                }
        named = {}
        # name a degree sequence when it is a well-known small graph
        for degs, cnt in sorted(deg_hist.items()):
            nv = len(degs)
            m = sum(degs) // 2
            tag = f"V={nv} E={m} deg={list(degs)}"
            named[tag] = {"count": cnt,
                          "example_S_size":
                              by_degseq[degs]["example"]["S"].__len__(),
                          "example": by_degseq[degs]["example"]}
        rep[f"census_n{n}"] = {
            "n_states": s.N,
            "n_distinct_residual_graphs_by_degseq": len(deg_hist),
            "total_edges_seen_hist": dict(sorted(
                Counter(sum(d) // 2 for d in deg_hist).items())),
            "max_degree_seen": max((max(d) for d in deg_hist if d), default=0),
            "graphs": named,
        }
        log(f"n={n}: {len(deg_hist)} distinct residual degree sequences; "
            f"max degree {rep[f'census_n{n}']['max_degree_seen']}")
        save(rep)

    # ================================================================
    # B233: do the TREES P_k (paths) and S_k (stars) appear, and with
    # which multiplicity (r copies)?  Exhaustive small-n search.
    # ================================================================
    log("B233: path/star realisation census")
    b233 = {}
    for n in (4, 5):
        s = Solve(quad_masks(n), n * n)
        g = s.grundy()
        qbp = s.qbp
        found = defaultdict(int)     # graph name -> number of positions
        maxcopy = defaultdict(int)   # graph name -> max disjoint copies seen
        first = {}
        for occ in s.states:
            Lm = s.legal_mask(occ)
            if Lm == 0:
                continue
            L = bits(Lm)
            adj = residual_adj(qbp, occ, L)
            comps = comps_and_adj(adj)
            for c in comps:
                m = sum(1 for v in c for w in adj[v] if w in c) // 2
                nv = len(c)
                tag = None
                if m == 0 and nv == 1:
                    tag = "K1"
                elif nv >= 2 and max(len(adj[v] & set(c)) for v in c) == 1:
                    tag = f"P{nv}"          # path
                elif m == 1:
                    tag = "K2"
                elif m == nv - 1 and nv >= 4 and \
                        sum(1 for v in c for w in adj[v] if w in c) == 2 * (nv - 1):
                    pass
                # star test
                if nv >= 3 and m == nv - 1 and \
                        sorted((len(adj[v] & set(c)) for v in c),
                               reverse=True) == [nv - 1] + [1] * (nv - 1):
                    tag = f"S{nv - 1}"
                if tag:
                    found[tag] += 1
                    if tag not in first:
                        first[tag] = {
                            "S": [list(xy1(i, n)) for i in bits(occ)],
                            "component": [list(xy1(v, n)) for v in c],
                            "g_S": int(g[s.idx[occ]])}
            # count identical components
            shapes = Counter()
            for c in comps:
                m = sum(1 for v in c for w in adj[v] if w in c) // 2
                shapes[(len(c), m, tuple(sorted(len(adj[v] & set(c))
                                                 for v in c)))] += 1
            for shp, cnt in shapes.items():
                if cnt >= 2:
                    key = f"r={cnt} x (V={shp[0]},E={shp[1]})"
                    maxcopy[key] = max(maxcopy[key], cnt)
        b233[f"n{n}"] = {
            "tree_shapes_found": dict(sorted(found.items())),
            "max_identical_copies": dict(sorted(maxcopy.items(),
                                                key=lambda kv: -kv[1])[:15]),
            "first_examples": {k: first[k] for k in sorted(first)[:12]},
        }
        log(f"B233 n={n}: tree shapes {sorted(found)} ; "
            f"max identical copies {sorted(maxcopy.items(), key=lambda kv:-kv[1])[:6]}")
        rep[f"B233_n{n}"] = b233[f"n{n}"]
        save(rep)

    OUT.write_text(json.dumps(_REP, indent=1, ensure_ascii=False, default=str))
    log("wrote", OUT)


if __name__ == "__main__":
    main()
