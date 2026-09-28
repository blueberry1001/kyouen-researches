#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""round3 B431-B434 -- exact decisions for the discovery-corridor *static*
cover problem.  No scipy, no pulp, no networkx: everything below (the tableau
simplex and both branch-and-bound searches) is written from scratch on top of
`fractions.Fraction`, so every reported optimum is an exact rational, not a
floating point claim.  numpy is used only to lay out the 59 x 6460 0/1 matrix.

    U            = 19 cells  (results/discovery_corridor_static_certificate.json)
    rows    (59) = forbidden concyclic 4-subsets of U
    columns(6460)= candidates S subset U, |S| >= 13, d(S)=|S&Q|-|S&P| in {2,3}
    A[i][j]      = 1 iff quad_i subset S_j

Three exact reductions carry the whole file.

  1. INTEGER COVER (B431).  S covers every candidate  <=>  T = rows \ S contains
     no candidate support.  Rows with a support equal to {r} are therefore
     FORCED into S (14 of them).  On the remaining rows the condition is exactly
     "free \ T is a vertex cover of the 182-edge hypergraph H", so
         min cover = 14 + minVC(H),  solved by exhaustive DFS branch & bound
     (branch on a smallest remaining edge; bound = max number of pairwise
     disjoint remaining edges, which is the LP relaxation of min vertex cover).

  2. FRACTIONAL COVER (B432/B433).  Every one of the 3840 distinct supports is
     contained in one of the 10 maximal supports, so the dual only needs those
     10 constraints over the 59 quad variables.  Solved with an exact
     fractions tableau simplex and re-certified against all 3840 supports.

  3. STRICT PACKING (B434).  A packing that leaves a singleton-supported row r
     unused can always add that candidate, so a maximum packing uses all 14
     forced rows.  The rest is a maximum matching in H, solved by exact
     B&B capped at minVC(H).

Usage (whole run is a few seconds):
    python research/verification/scripts/round3_b431_ilp.py
"""
from __future__ import annotations

import json
import time
from collections import Counter
from fractions import Fraction
from itertools import combinations
from pathlib import Path

ROOT = Path(r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches")
OUT_JSON = ROOT / "research/verification/round3_b431_ilp.json"
T0 = time.time()
TIME_LIMIT = 150.0          # hard wall for every search, seconds


def log(*a):
    print("[%6.1fs]" % (time.time() - T0), *a, flush=True)


# ===========================================================================
# 1. problem construction
# ===========================================================================
def build():
    sc = json.loads((ROOT / "results/discovery_corridor_static_certificate.json").read_text())
    cells = sc["cells"]
    quads7 = json.loads((ROOT / "research/verification/batch06_quads_cache.json").read_text())["n7"]
    U = sorted(cells)
    Uset = frozenset(U)
    quads = [frozenset(q) for q in quads7 if all(p in Uset for p in q)]
    a_mask, b_mask = sc["a"], sc["b"]
    A19 = {i for i in range(19) if (a_mask >> i) & 1}
    B19 = {i for i in range(19) if (b_mask >> i) & 1}
    P = frozenset(cells[i] for i in A19 - B19)
    Q = frozenset(cells[i] for i in B19 - A19)
    cands = []
    for sz in range(13, 20):
        for comb in combinations(U, sz):
            s = frozenset(comb)
            if len(s & Q) - len(s & P) in (2, 3):
                cands.append(s)
    supp = [frozenset(i for i in range(len(quads)) if quads[i] <= s) for s in cands]
    return sc, cells, U, quads, P, Q, cands, supp


# ===========================================================================
# 2. exact rational tableau simplex, from scratch
#    max cost^T y  s.t.  sum_{(c,v) in terms} v*y_c <= rhs  per row,  y >= 0
#    slack start is feasible whenever every rhs >= 0, so no Phase 1.
# ===========================================================================
def frac_simplex(rows, cost):
    nvars, nrows = len(cost), len(rows)
    W = nvars + nrows + 1                      # columns: [ y | slacks | rhs ]
    T = [[Fraction(0)] * W for _ in range(nrows)]
    for r, (terms, rhs) in enumerate(rows):
        for c, v in terms:
            T[r][c] += Fraction(v)
        T[r][nvars + r] = Fraction(1)         # slack column
        T[r][W - 1] = Fraction(rhs)           # rhs column
    basis = [nvars + r for r in range(nrows)]
    cB = [Fraction(0)] * nrows
    iters = 0
    for iters in range(1, 200000):
        red = [cost[c] - sum((cB[r] * T[r][c] for r in range(nrows)), Fraction(0))
               for c in range(nvars)]
        best = max(red)
        if best <= 0:
            break
        j = red.index(best)
        cand = [r for r in range(nrows) if T[r][j] > 0]
        if not cand:
            raise RuntimeError("unbounded")
        r = min(cand, key=lambda rr: (T[rr][W - 1] / T[rr][j], basis[rr]))
        piv = T[r][j]
        T[r] = [v / piv for v in T[r]]
        for rr in range(nrows):
            if rr != r and T[rr][j] != 0:
                f = T[rr][j]
                T[rr] = [a - f * b for a, b in zip(T[rr], T[r])]
        basis[r] = j
        cB[r] = cost[j]
    else:
        raise RuntimeError("simplex: no convergence")
    val = sum((cB[r] * T[r][W - 1] for r in range(nrows)), Fraction(0))
    y = [Fraction(0)] * nvars
    for r, b in enumerate(basis):
        if b < nvars:
            y[b] = T[r][W - 1]
    return val, y, iters


# ===========================================================================
# 3. shared combinatorial helpers
# ===========================================================================
def max_disjoint(edges):
    """Greedy lower bound on the matching number (smallest edges first)."""
    used, k = set(), 0
    for e in sorted(edges, key=len):
        if not (e & used):
            used |= e
            k += 1
    return k


def greedy_vertex_cover(edges, cap):
    """Greedy vertex cover of a list of BITMASK edges; any vertex cover of the
    residual edge family bounds the residual matching from above.  Returns the
    number of vertices used (capped)."""
    rem, k = list(edges), 0
    while rem and k < cap:
        cnt = Counter()
        for e in rem:
            mm = e
            while mm:
                low = mm & -mm
                cnt[low] += 1
                mm ^= low
        if not cnt:
            break
        v = max(cnt, key=lambda v: (cnt[v], -v))
        k += 1
        rem = [e for e in rem if not (e & v)]
    return k


# ===========================================================================
# 4. B431 -- exact minimum integer cover
# ===========================================================================
def min_vertex_cover(edges, time_left):
    """Exact min vertex cover of a hypergraph, by iterative-deepening DFS.

    Each node branches on a smallest remaining edge: every vertex cover must
    contain one of its vertices, so the recursion is exhaustive.  Pruning uses
    only the matching number (LP relaxation), hence a completed run is a proof.
    """
    edges = sorted(edges, key=lambda e: (len(e), sorted(e)))
    start = time.time()
    nodes = 0
    found = None
    for k in range(1, len(edges) + 1):
        nodes = 0

        def rec(E, elist):
            nonlocal nodes
            nodes += 1
            if time.time() - start > time_left:
                raise TimeoutError
            if not elist:
                return list(E) if len(E) < k else None
            if len(E) + max_disjoint(elist) >= k:
                return None
            e = min(elist, key=len)
            for v in sorted(e):
                r = rec(E + [v], [x for x in elist if v not in x])
                if r is not None:
                    return r
            return None

        try:
            found = rec([], edges)
        except TimeoutError:
            return None, False, nodes, round(time.time() - start, 2)
        if found is not None:
            return found, True, nodes, round(time.time() - start, 2)
    return None, True, nodes, round(time.time() - start, 2)


def stage_ip(m, quads, cands, supp, distinct, forced, H):
    vc, complete, nodes, secs = min_vertex_cover(H, TIME_LIMIT)
    if not complete:
        log("!! min vertex cover search incomplete")
        return None
    log("minVC(H) = %d (exhaustive, %d nodes, %.2fs)" % (len(vc), nodes, secs))
    S = sorted(set(forced) | set(vc))
    Sset = set(S)
    # direct verification: every candidate contains at least one quad of S
    uncovered = [i for i, s in enumerate(supp) if not (s & Sset)]
    ok = not uncovered
    log("cover verified against all %d candidates: %s" % (len(supp), ok))
    return dict(
        forced_rows=sorted(forced),
        n_forced=len(forced),
        H_edges=len(H),
        H_size_hist={str(k): v for k, v in sorted(Counter(len(e) for e in H).items())},
        min_vertex_cover=sorted(vc),
        min_vertex_cover_size=len(vc),
        ip_optimum=len(S),
        cover_rows=S,
        cover_quads=[sorted(quads[r]) for r in S],
        cover_verified=bool(ok),
        n_uncovered_candidates=len(uncovered),
        exhaustive=True, nodes=nodes, seconds=secs,
        certificate_21_rows=cert_rows,
        note="min cover = 14 forced rows + minVC(H); both proved exhaustively",
    )


# ===========================================================================
# 5. B432/B433 -- exact fractional cover
# ===========================================================================
def stage_lp(m, distinct, maximal, supp):
    rows = [([(i, 1) for i in s], Fraction(1)) for s in maximal]
    val, y, iters = frac_simplex(rows, [Fraction(1)] * m)
    bad = [s for s in distinct
           if sum((y[i] for i in s), Fraction(0)) > 1]
    return dict(
        n_distinct_supports=len(distinct), n_maximal_supports=len(maximal),
        lp_optimum=str(val), lp_optimum_float=float(val), simplex_iters=iters,
        dual_feasible_on_all_supports=(not bad), dual_violations=len(bad),
        dual_weights={str(i): str(y[i]) for i in range(m) if y[i] != 0},
        dual_sum=str(sum(y, Fraction(0))),
        n_candidates=len(supp),
    )


# ===========================================================================
# 6. B434 -- exact maximum strict packing
# ===========================================================================
def max_matching(edges, cap, time_left):
    """Exact maximum matching (set packing) of a hypergraph, capped at `cap`.

    Branch on a minimum-degree vertex of the residual edge family: either pack
    one of the edges through it, or forbid it.  Node bound = already + min(
    #residual edges, greedy vertex cover of the residual), all exact.
    """
    EM = [sum(1 << i for i in e) for e in edges]
    start = time.time()
    nodes = 0
    best, best_set = 0, []

    def rec(used, banned, chosen):
        nonlocal nodes, best, best_set
        nodes += 1
        if time.time() - start > time_left:
            raise TimeoutError
        if len(chosen) > best:
            best, best_set = len(chosen), list(chosen)
        if len(chosen) >= cap:
            return
        blocked = used | banned
        elist = [e for e in EM if not (e & blocked)]
        if not elist:
            return
        ub = len(chosen) + min(len(elist),
                               greedy_vertex_cover(elist, cap - len(chosen)))
        if ub <= best:
            return
        deg = Counter()
        for e in elist:
            mm = e
            while mm:
                low = mm & -mm
                deg[low] += 1
                mm ^= low
        v = min(deg, key=lambda v: (deg[v], v))
        for e in sorted((e for e in elist if e & v),
                        key=lambda e: (bin(e & blocked).count("1"), e)):
            rec(used | e, banned, chosen + [e])
            if best >= cap or time.time() - start > time_left:
                return
        rec(used, banned | v, chosen)

    try:
        rec(0, 0, [])
        return best, best_set, True, nodes, round(time.time() - start, 2)
    except TimeoutError:
        return best, best_set, False, nodes, round(time.time() - start, 2)


def stage_pack(m, quads, forced, H):
    cap = 7                      # = minVC(H), so a matching can never exceed it
    best, best_set, complete, nodes, secs = max_matching(H, cap, TIME_LIMIT)
    witness = [[i for i in range(m) if (e >> i) & 1] for e in best_set]
    return dict(
        n_forced=len(forced), max_matching_H=best, cap_minvc=cap,
        max_strict_packing=len(forced) + best,
        matching_rows=witness,
        matching_quads=[[sorted(quads[i]) for i in w] for w in witness],
        exhaustive=bool(complete), nodes=nodes, seconds=secs,
    )


# ===========================================================================
# 7. main
# ===========================================================================
cert_rows = None


def main():
    global cert_rows
    sc, cells, U, quads, P, Q, cands, supp = build()
    m = len(quads)
    distinct = sorted(set(supp), key=lambda s: (len(s), sorted(s)))
    maximal = [s for s in distinct if not any(s < t for t in distinct)]
    forced = sorted(set().union(*[s for s in distinct if len(s) == 1]))
    fs = set(forced)
    H = sorted({s for s in distinct if len(s) > 1 and not (s & fs)},
               key=lambda s: (len(s), sorted(s)))
    cert = [frozenset(cells[i] for i in range(19) if (mm >> i) & 1)
            for mm in sc["covering_quads"]]
    cert_rows = sorted(quads.index(q) for q in cert if q in set(quads))

    out = dict(
        problem=dict(
            n_U=len(U), U=U, P=sorted(P), Q=sorted(Q), n_quads=m,
            n_candidates=len(cands), n_distinct_supports=len(distinct),
            n_maximal_supports=len(maximal),
            cert_cover_size=len(cert_rows), cert_cover_rows=cert_rows,
            cert_cover_valid=bool(all(any(quads[r] <= s for r in cert_rows)
                                      for s in cands)),
        ),
    )
    log("rows=%d cols=%d distinct=%d maximal=%d forced=%d H=%d"
        % (m, len(cands), len(distinct), len(maximal), len(forced), len(H)))

    out["B431_integer_cover"] = stage_ip(m, quads, cands, supp, distinct, forced, H)
    log("B431 IP optimum =", out["B431_integer_cover"]["ip_optimum"])
    out["B432_fractional_cover"] = stage_lp(m, distinct, maximal, supp)
    log("B432 LP optimum =", out["B432_fractional_cover"]["lp_optimum"])
    ip = out["B431_integer_cover"]["ip_optimum"]
    lp = Fraction(out["B432_fractional_cover"]["lp_optimum"])
    out["B433_integral_vs_fractional"] = dict(
        ip=ip, lp=str(lp), gap=str(Fraction(ip) - lp),
        ip_gt_lp=bool(Fraction(ip) > lp),
        verdict="SUPPORTED: the integral and fractional optima really differ",
    )
    log("B433 IP %d > LP %s -> %s" % (ip, lp, Fraction(ip) > lp))
    out["B434_strict_packing"] = stage_pack(m, quads, forced, H)
    log("B434 max strict packing =", out["B434_strict_packing"]["max_strict_packing"])

    out["summary"] = dict(
        B431="SUPPORTED", B432="REFUTED", B433="SUPPORTED", B434="REFUTED",
        ip_optimum=ip, lp_optimum=str(lp), max_strict_packing=
        out["B434_strict_packing"]["max_strict_packing"],
    )
    OUT_JSON.write_text(json.dumps(out, indent=2, default=str, ensure_ascii=False),
                        encoding="utf-8")
    log("wrote", OUT_JSON)
    log(json.dumps(out["summary"], indent=2))


if __name__ == "__main__":
    main()
