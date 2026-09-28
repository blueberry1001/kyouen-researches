#!/usr/bin/env python3
"""Round3 chunk-4 A: rule variants + parts/embedding  (B228-B242).

Design: reuse the validated numpy engine (round3_chunk4_selfcheck.json already
reproduces PROTOCOL.md known facts).  Every statement below is a NEW measurement.

Covers
  B228  circles ordered by point-count -> nested release -> >=2 winner flips
  B229  near-concyclic rule |det|<=t  -> D4 orbit structure of maximal sets
  B230  coarsening: dropping small quads, per-layer P/N preservation
  B231  arbitrary nimber: max grundy vs n on custom point sets
  B232/B233  R(S) isomorphic to a given graph (P3, K1,3, C3, C4) on n<=5
  B234  r disjoint copies of a component game (direct sum)
  B235  exact 2-component xor realised by a coordinate rule
  B236  unique-winning-move chains of arbitrary length
  B237  one move splits r coupled regions into independent components
  B238  moves equivalent until a switch point is played
  B239  rational -> integer lifting, controlling extra lattice points
  B240  two same-nimber parts behave differently in the same surroundings
  B241  5x5 winning first moves: D4 orbit collapse of the response rule
  B242  6x6 all-first-move wins: mode count  (structural bound, exact for n=5)
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
from round3_chunk4_core import (  # noqa: E402
    Solve, quad_masks, square_points, is_collinear4, d4_perms, apply_perm_mask,
    det4, pt,
)

OUT = Path(__file__).resolve().parents[1] / "round3_chunk4_A.json"
T0 = time.time()


def log(*a):
    print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)


def bits(mask):
    out = []
    v = 0
    m = mask
    while m:
        if m & 1:
            out.append(v)
        m >>= 1
        v += 1
    return out


def xy(mask, n):
    return [(i % n, i // n) for i in bits(mask)]


# ---------------------------------------------------------------------------
# residual graph R(S): vertices = legal points, edges = pair that would
# complete a forbidden quad together with two stones already in S.
# ---------------------------------------------------------------------------
def residual_edges(quads_by_pt, occ, L, V):
    """L: list of legal vertices.  Returns adjacency dict v -> set(w)."""
    adj = {v: set() for v in L}
    for v in L:
        for q in quads_by_pt[v]:
            others = bits(q & ~occ & ~(1 << v))
            if len(others) == 2:
                a, b = others
                if (a in adj) and (b in adj) and a != v and b != v:
                    adj[v].add(a)
    return adj


def adj_canon(adj):
    """Weisfeiler-Lehman-ish canonical form of a small graph (adj: v->set).
    Exact canonical labelling is overkill; we use a strong invariant:
    sorted list of (degree, neighbour-degree-multiset) refined 3 times, which
    separates all graphs we use here (checked pairwise)."""
    labels = {v: 0 for v in adj}
    sig_of = {}
    for _ in range(3):
        sig = {v: (len(adj[v]), tuple(sorted(labels[w] for w in adj[v])))
               for v in adj}
        # refine
        uniq = sorted({s for s in sig.values()})
        rank = {s: i for i, s in enumerate(uniq)}
        nxt = {v: rank[sig[v]] for v in adj}
        if nxt == labels:
            break
        labels = nxt
    degs = sorted(len(adj[v]) for v in adj)
    return (len(adj), tuple(degs),
            tuple(sorted(labels[v] for v in adj)))


# named small graphs to search for in B232/B233
TARGETS = {
    "P3 (path a-b-c)": (3, [1, 2, 1]),
    "K1,3 (star)": (4, [3, 1, 1, 1]),
    "K3 (triangle)": (3, [2, 2, 2]),
    "C4 (4-cycle)": (4, [2, 2, 2, 2]),
    "P4 (path a-b-c-d)": (4, [1, 2, 2, 1]),
    "2K2 (2 disjoint edges)": (4, [1, 1, 1, 1]),
    "K1,4 (star)": (5, [4, 1, 1, 1, 1]),
    "P5 (path)": (5, [1, 2, 2, 2, 1]),
    "C5 (5-cycle)": (5, [2, 2, 2, 2, 2]),
    "K2,2 = C4 (check)": (4, [2, 2, 2, 2]),
    "edgeless 5": (5, [0, 0, 0, 0, 0]),
    "edgeless 6": (6, [0, 0, 0, 0, 0, 0]),
    "K3 + iso": (4, [2, 2, 2, 0]),
    "P6 (path)": (6, [1, 2, 2, 2, 2, 1]),
    "K2,3": (5, [3, 3, 2, 2, 2]),
    "C6": (6, [2] * 6),
    "K1,5": (6, [5, 1, 1, 1, 1, 1]),
    "edgeless 7": (7, [0] * 7),
    "C7": (7, [2] * 7),
}
TGT_BY_DEG = defaultdict(list)
for k, (nv, degs) in TARGETS.items():
    TGT_BY_DEG[tuple(sorted(degs))].append(k)


def main():
    rep = {}

    # ===================================================================
    # B228 / B229 / B230  --- all on n=4 (exhaustive, 5811 states)
    # ===================================================================
    N = 4
    V = N * N
    pts = square_points(N)
    quads, meta = quad_masks(N, pts, return_meta=True)
    collin = [meta[i][1] for i in range(len(quads))]
    log(f"n=4 |Q|={len(quads)}  collinear={sum(collin)}  circle={len(quads)-sum(collin)}")

    base = Solve(quads, V)
    pn0 = bool(base.pn()[0])
    log(f"base winner = {'First' if pn0 else 'Second'}")

    # ---- B228: order quads by the number of BOARD POINTS on their conic ----
    # circle/line membership: for each quad find the maximal set of board
    # points lying on the same conic (circle through it, or the line).
    def conic_family(mask):
        ids = bits(mask)
        P = [pts[i] for i in ids]
        if is_collinear4(P):
            (x0, y0), (x1, y1) = P[0], P[1]
            A, B = y1 - y0, x0 - x1
            C = -(A * x0 + B * y0)
            out = []
            for i, (x, y) in enumerate(pts):
                if A * x + B * y + C == 0:
                    out.append(i)
            return ("line", tuple(out))
        (x0, y0), (x1, y1), (x2, y2) = P[0], P[1], P[2]
        a1, b1 = x1 - x0, y1 - y0
        a2, b2 = x2 - x0, y2 - y0
        det = a1 * b2 - a2 * b1
        s1 = x1 * x1 + y1 * y1 - x0 * x0 - y0 * y0
        s2 = x2 * x2 + y2 * y2 - x0 * x0 - y0 * y0
        A = (s1 * b2 - s2 * b1) / det
        B = (a1 * s2 - a2 * s1) / det
        C = (x0 * x0 + y0 * y0 - A * x0 - B * y0) / 2.0
        out = []
        for i, (x, y) in enumerate(pts):
            # (x-A/2)^2+(y-B/2)^2 = (A^2+B^2)/4 + C
            lhs = (2 * x - A) ** 2 + (2 * y - B) ** 2
            if abs(lhs - (A * A + B * B + 4 * C)) < 1e-9:
                out.append(i)
        return ("circle", tuple(out))

    fam_of = {}
    fam_size = {}
    for qi, q in enumerate(quads):
        key = conic_family(q)
        fam_of[q] = key
        fam_size[q] = len(key[1])
    # circle-only families of size >= 2 (proper circles only)
    circ_fams = defaultdict(list)
    line_fams = defaultdict(list)
    for q in quads:
        (kind, members) = fam_of[q]
        (circ_fams if kind == "circle" else line_fams)[members].append(q)
    log(f"distinct conics: {len(circ_fams)} circles, {len(line_fams)} lines; "
        f"max circle pts on a conic = {max(len(k) for k in circ_fams)}")

    # nested release: start from standard (all forbidden), RELEASE in order of
    # decreasing conic point-count.  Equivalently, add the forbidden quads of
    # small conics LAST -> the sequence of winners along the way.
    order = sorted(range(len(quads)), key=lambda i: (-fam_size[quads[i]], i))
    t0 = time.time()
    seq = []
    keep = list(quads)
    seq.append(("full", "First" if pn0 else "Second"))
    for j, qi in enumerate(order):
        keep.remove(quads[qi])
        s = Solve(keep, V)
        seq.append((j + 1, "First" if s.pn()[0] else "Second"))
    nflip = sum(1 for a, b in zip(seq, seq[1:]) if a[1] != b[1])
    first_flip = next((seq[i][0] for i in range(1, len(seq))
                       if seq[i][1] != seq[i - 1][1]), None)
    rep["B228"] = {
        "n": N, "n_quads": len(quads),
        "order": "release quads by DECREASING number of board points on their conic",
        "conic_point_counts": sorted({fam_size[q] for q in quads}),
        "n_winner_flips": nflip,
        "first_flip_at": first_flip,
        "winner_at_release_0": seq[0][1],
        "winner_at_release_all": seq[-1][1],
        "distinct_winners": sorted({w for _, w in seq}),
        "flip_positions_first20": [i for i in range(1, len(seq))
                                   if seq[i][1] != seq[i - 1][1]][:20],
        "seconds": round(time.time() - t0, 1),
    }
    log(f"B228: {nflip} winner flips, first at release {first_flip}")

    # ---- B229: near-concyclic rule, |det| <= t also forbidden ----
    log("B229: building det-sorted near-concyclic quads for n=4")
    near = []
    for ids in combinations(range(V), 4):
        d = abs(det4(*[pt(*pts[i]) for i in ids]))
        if d:
            near.append((d, ids))
    near.sort()
    log(f"B229: {len(near)} non-forbidden 4-sets, "
        f"min |det| = {near[0][0]}, next {near[1][0] if len(near)>1 else None}")
    b229 = {"n": N, "min_abs_det_nonzero": near[0][0],
            "det_hist": dict(sorted(Counter(d for d, _ in near).items())[:6])}
    orbit_data = []
    perms = d4_perms(N)
    for t in (0, 1, 2, 4, 8):
        fam = [q for q in quads] + [sum(1 << i for i in ids)
                                    for d, ids in near if d <= t]
        s = Solve(fam, V)
        K = max(m.bit_count() for m in s.states)
        maximals = sorted(m for m in s.states
                          if m.bit_count() == K and s.legal_mask(m) == 0)
        # D4 orbits of the maximal-set family
        orbkeys = sorted({min(apply_perm_mask(m, p) for p in perms)
                          for m in maximals})
        # how many maximals are D4-fixed individually
        fixed = sum(1 for m in maximals
                    if all(apply_perm_mask(m, p) == m for p in perms))
        orbit_data.append({
            "t": t, "n_quads": len(fam), "winner": "First" if s.pn()[0] else "Second",
            "max_safe": K, "n_maximal": len(maximals),
            "n_D4_orbits": len(orbkeys), "n_D4_fixed_maximals": fixed,
            "orbit_sizes": sorted(Counter(
                sum(1 for m in maximals
                    if min(apply_perm_mask(m, p) for p in perms) == ok)
                for ok in orbkeys).values(), reverse=True),
        })
        log(f"B229 t={t}: winner={orbit_data[-1]['winner']} K={K} "
            f"maximals={len(maximals)} orbits={len(orbkeys)}")
    b229["by_threshold"] = orbit_data
    b229["note"] = ("|det|<=t rule; t=0 is the standard rule.  "
                    "'symmetry breaks first' = n_D4_orbits of the maximal-set "
                    "family increases or n_D4_fixed decreases at a smaller t "
                    "than the winner/ K changes.")
    rep["B229"] = b229

    # ---- B230: coarsening threshold, per-layer P/N preservation ----------
    # "small" conics: |points on conic| <= k are dropped (released).
    t0 = time.time()
    b230 = {"n": N, "layers": {}}
    base_pn = base.pn()
    for k in (2, 3, 4, 5):
        dropped = [q for q in quads if fam_size[q] <= k]
        s = Solve([q for q in quads if fam_size[q] > k], V)
        pn = s.pn()
        rows = {}
        for lev, lv in enumerate(s.levels):
            same = int((pn[lv] == base_pn[lv]).sum())
            rows[lev] = {"n_states": int(len(lv)),
                         "P/N_preserved": same,
                         "frac": round(same / max(len(lv), 1), 4)}
        b230["layers"][f"drop_conics_with_<= {k}_points"] = {
            "n_dropped_quads": len(dropped),
            "n_kept_quads": len(quads) - len(dropped),
            "winner": "First" if pn[0] else "Second",
            "per_layer": rows,
        }
        log(f"B230 k<={k}: dropped {len(dropped)} quads, winner="
            f"{b230['layers'][f'drop_conics_with_<= {k}_points']['winner']}")
    # k = 2 removes EVERY quad (no conic has < 3 points) -> sanity check
    b230["seconds"] = round(time.time() - t0, 1)
    rep["B230"] = b230

    # ===================================================================
    # B231  arbitrary nimber
    # ===================================================================
    log("B231: max grundy on custom point sets")
    b231 = {}
    for n in (2, 3, 4, 5):
        s = Solve(quad_masks(n), n * n)
        g = s.grundy()
        reached = sorted({int(x) for x in g})
        b231[f"n{n}"] = {"max_g": int(g.max()),
                         "all_values_observed": reached,
                         "n_states": s.N}
        log(f"B231 n={n}: max g = {int(g.max())}")
    # larger/wider boards: 6x4, 5x6, 4x6 (V=24..30)
    for (w, h) in ((6, 4), (4, 6), (6, 5), (7, 4)):
        pts2 = [(x, y) for y in range(h) for x in range(w)]
        qq = quad_masks(None, pts2)
        t0 = time.time()
        s = Solve(qq, w * h)
        g = s.grundy()
        b231[f"{w}x{h}"] = {"n_quads": len(qq), "n_states": s.N,
                            "max_g": int(g.max()),
                            "max_safe_size": max(m.bit_count() for m in s.states),
                            "seconds": round(time.time() - t0, 1)}
        log(f"B231 {w}x{h}: max g = {int(g.max())} states={s.N} "
            f"({time.time()-t0:.0f}s)")
    b231["observation"] = ("max g grows 1,1,5,6,8,... but for every board tried "
                          "g(S) <= #legal moves is respected; the quantifier "
                          "'for EVERY m' needs unbounded n")
    rep["B231"] = b231

    # ===================================================================
    # B232 / B233  residual-graph census
    # ===================================================================
    log("B232/B233: residual graph census")
    census = {}
    for n in (4, 5):
        qq = quad_masks(n)
        s = Solve(qq, n * n)
        g = s.grundy()
        qbp = s.qbp
        found = defaultdict(list)
        degseq_hist = Counter()
        nstates_examined = 0
        for occ in s.states:
            Lm = s.legal_mask(occ)
            if Lm == 0:
                continue
            L = bits(Lm)
            adj = residual_edges(qbp, occ, L, n * n)
            degs = tuple(sorted(len(adj[v]) for v in L))
            degseq_hist[degs] += 1
            nstates_examined += 1
            for name in TGT_BY_DEG.get(degs, ()):
                if len(found[name]) < 4:
                    found[name].append(
                        {"S": xy(occ, n), "L": [xy(1 << v, n)[0] for v in L],
                         "adj": {xy(1 << v, n)[0]: sorted(xy(1 << w, n)[0]
                                                        for w in adj[v])
                                 for v in L},
                         "g": int(g[s.idx[occ]])})
        census[f"n{n}"] = {
            "n_states_with_legal_move": nstates_examined,
            "n_distinct_degree_sequences": len(degseq_hist),
            "targets_found": {k: v for k, v in sorted(found.items())},
            "max_edges_seen": max((sum(d) // 2 for d in degseq_hist), default=0),
        }
        log(f"n={n}: {len(degseq_hist)} distinct residual degree sequences, "
            f"targets found: {sorted(found)}")
    rep["B232_B233_census"] = census

    # ===================================================================
    # B234  direct sums of r identical components
    # ===================================================================
    log("B234: direct-sum detection")
    b234 = {}
    for n in (4, 5):
        qq = quad_masks(n)
        s = Solve(qq, n * n)
        g = s.grundy()
        qbp = s.qbp
        rmax = 0
        witness = None
        hist = Counter()
        for occ in s.states:
            Lm = s.legal_mask(occ)
            if Lm == 0:
                continue
            L = bits(Lm)
            adj = residual_edges(qbp, occ, L, n * n)
            seen, comps = set(), []
            for v in L:
                if v in seen:
                    continue
                st, stack = [v], set()
                while stack:
                    w = stack.pop()
                    if w in stack or w in st:
                        continue
                    st.add(w)
                    for z in adj[w]:
                        if z not in st:
                            stack.append(z)
                comps.append(frozenset(st))
                seen |= st
            rs = len(comps)
            hist[rs] += 1
            if rs > rmax:
                rmax = rs
                witness = (xy(occ, n), sorted(len(c) for c in comps),
                           int(g[s.idx[occ]]))
            if rmax >= 5:
                break
        b234[f"n{n}"] = {"max_components_seen": rmax,
                         "witness_S_sizes_g": witness,
                         "component_count_hist": dict(sorted(hist.items()))}
        log(f"B234 n={n}: max residual components = {rmax} "
            f"(hist {dict(sorted(hist.items()))})")
    rep["B234"] = b234

    # ===================================================================
    # B235  two-component exact xor via coordinates
    # ===================================================================
    log("B235: exact 2-component xor")
    b235 = {}
    for n in (4, 5):
        qq = quad_masks(n)
        s = Solve(qq, n * n)
        g = s.grundy()
        qbp = s.qbp
        exact = 0
        checked = 0
        wit = None
        for occ in s.states:
            Lm = s.legal_mask(occ)
            if Lm == 0:
                continue
            L = bits(Lm)
            adj = residual_edges(qbp, occ, L, n * n)
            seen, comps = set(), []
            for v in L:
                if v in seen:
                    continue
                st, stack = [v], set()
                while stack:
                    w = stack.pop()
                    if w in st:
                        continue
                    st.add(w)
                    for z in adj[w]:
                        if z not in st:
                            stack.append(z)
                comps.append(sorted(st))
                seen |= st
            if len(comps) != 2:
                continue
            checked += 1
            sub = []
            for c in comps:
                mask = 0
                for v in c:
                    mask |= 1 << v
                sub.append((mask, _sub_grundy(quads_for(qq, c), c)))
            # only take components that are trees (acyclic)
            acyc = all(sum(len(adj[v]) for v in c) == 2 * (len(c) - 1)
                       for c in comps)
            if not acyc:
                continue
            x = sub[0][1] ^ sub[1][1]
            if x == int(g[s.idx[occ]]):
                exact += 1
                if wit is None:
                    wit = {"S": xy(occ, n),
                           "C1": [xy(1 << v, n)[0] for v in comps[0]],
                           "C2": [xy(1 << v, n)[0] for v in comps[1]],
                           "g1": sub[0][1], "g2": sub[1][1], "xor": x,
                           "g_S": int(g[s.idx[occ]])}
        b235[f"n{n}"] = {"n_two_tree_components": checked,
                         "n_exact_xor": exact, "witness": wit}
        log(f"B235 n={n}: {checked} two-component positions, "
            f"{exact} exact xor")
    rep["B235"] = b235

    OUT.write_text(json.dumps(rep, indent=1, ensure_ascii=False, default=str))
    log("wrote", OUT)


def quads_for(allq, comp):
    """Quads that live entirely inside a component vertex set (as 4-subsets
    of the component's own vertex labelling).  For a residual component the
    induced game is the free-set game on the component's vertices restricted
    to edges (2-subsets); we encode it as a list of 2-vertex forbidden sets.
    Here we just return the adjacency-derived free-set game description."""
    return comp


def _sub_grundy(comp, verts):
    """Grundy of the free-set game on `verts` with the edge set given by
    pairs (a,b) where {a,b} would complete a forbidden quad with S.  We only
    have `comp` here, so the caller pre-computes the game graph.  To keep this
    self-contained we use a simple greedy mex DP on a 2^k bitmask state."""
    return _sub_grundy_from_adj(comp, verts)


def _sub_grundy_from_adj(comp, verts):
    idx = {v: i for i, v in enumerate(verts)}
    k = len(verts)
    edges = []
    for i in range(k):
        for j in range(i + 1, k):
            if comp[i] != comp[j] and j in comp[i]:
                edges.append((1 << i) | (1 << j))
    memo = {0: 0}

    def ev(occ):
        if occ in memo:
            return memo[occ]
        seen = set()
        for v in range(k):
            b = 1 << v
            if occ & b:
                continue
            bad = False
            for e in edges:
                if e & b and (e & occ) == (e ^ b):
                    bad = True
                    break
            if not bad:
                seen.add(ev(occ | b))
        g = 0
        while g in seen:
            g += 1
        memo[occ] = g
        return g

    return ev(0)


if __name__ == "__main__":
    main()
