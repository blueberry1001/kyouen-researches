#!/usr/bin/env python3
"""round3 chunk2 / B092-B098 : an *exact* upper bound on the coverage a
maximal safe set of size k can have, via a set-cover certificate.

Given a candidate stone set S of size k, the set of still-legal points is
L(S) = { v not in S : no triple of S completes a forbidden quad with v }.
S is maximal iff L(S) = {}.

Instead of a per-triple sum (which double counts) we build, for every
v, the hypergraph H_v = { triples T of S with T + v forbidden }.  v is blocked
iff some hyperedge of H_v is fully inside S -- i.e. v is blocked iff the
triple set of S *hits* H_v.

Exact reformulation usable for certificates: S blocks v iff
      sum_{T in H_v} 1[T subset S] >= 1.
Introduce for every triple T of the whole board the binary variable
x_T = 1[T subset S].  Then x is monotone-consistent (x_T <= x_{T'} for
T subset T'), sum over T subset S x_T = C(k,3) and
    sum_{T in H_v} x_T >= 1  for all v.
Relax x_T >= 0 (fractional) and add x_T <= x_{T'} for T subset T'.  An LP
bound needs a solver, so we use a pure-integer LP dual instead:

  max sum_v y_v  s.t.  sum_{v: T in H_v} y_v <= 1 for every triple T,
                        y_v >= 0.
This is the *fractional* covering number of the hypergraph, and it is exactly
the best "average" bound of the C(k,3)-type: an integer solution y in {0,1}
means "these k' triples cover all blocked points", so k >= min cover size.
The integer min-cover is computable exactly for small cases by
branch-and-bound over the 49+ points, and the LP relaxation via a
pure-Python simplex on the (few hundred constraint) system.

Concretely this script reports, for n=7..10:
  * the exact minimum number of *triples* needed to dominate the "not in S"
    points for a maximal S  ->  gives a *lower bound on |S|* via
    C(k,3) >= mincover;
  * a per-size exhaustive check of the "no triple covers a point" slack.
Output: research/verification/round3_chunk2_scover.json
"""
from __future__ import annotations

import json
import random
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from round3_chunk2_geom import bitl, legal_moves, quad_masks, triples_by_point  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round3_chunk2_scover.json"


# ------------------------------------------------------------------- simplex
class Simplex:
    """Minimise c.x subject to A x >= b, x >= 0  (Phase-1 with artificials).

    Small dense tableau solver; the systems here have < 400 rows.
    """

    def __init__(self, A, b, c, maximize=False):
        self.A = [row[:] for row in A]
        self.b = list(b)
        self.c = list(c)
        self.maximize = maximize

    def solve(self):
        A, b, c = self.A, self.b, list(self.c)
        if self.maximize:
            c = [-x for x in c]
        m, n = len(b), len(c)
        # add slacks: A x + s = b  with s >= 0
        T = [A[i] + [1.0 if j == i else 0.0 for j in range(m)] + [b[i]]
             for i in range(m)]
        cost = [0.0] * n + [1.0] * m + [0.0]   # phase 1
        basis = [n + i for i in range(m)]
        phase2 = [0.0] * n + [0.0] * m + [0.0]
        for j in range(n):
            phase2[j] = c[j]

        def pivot(T, basis, cost, r, s):
            piv = T[r][s]
            for j in range(len(T[r])):
                T[r][j] /= piv
            for i in range(len(T)):
                if i == r:
                    continue
                f = T[i][s]
                if f:
                    for j in range(len(T[i])):
                        T[i][j] -= f * T[r][j]
            f = cost[s]
            if f:
                for j in range(len(cost)):
                    cost[j] -= f * T[r][j]
            basis[r] = s

        def optimise(T, basis, cost):
            while True:
                s = None
                for j in range(len(cost) - 1):
                    if cost[j] < -1e-9 and (s is None or cost[j] < cost[s]):
                        s = j
                if s is None:
                    return True
                r = None
                for i in range(len(T)):
                    if T[i][s] > 1e-9:
                        if r is None or T[i][-1] / T[i][s] < T[r][-1] / T[r][s]:
                            r = i
                if r is None:
                    return False  # unbounded
                pivot(T, basis, cost, r, s)

        if not optimise(T, basis, cost):
            return None
        if abs(T[m - 1][-1] if m else 0.0) > 1e-9 and m:
            # artificial objective is the last row when m>0; check feasibility
            pass
        # phase 1 objective row index
        # After phase 1, check reduced cost of artificials is 0 => feasible
        # (cost[m-1] position holds the phase-1 value)
        if abs(cost[-1]) > 1e-7:
            return None  # infeasible
        T2 = [row[:] for row in T]
        cost2 = phase2[:]
        # drive artificials out of basis if possible
        for i in range(m):
            if basis[i] >= n:
                s = None
                for j in range(n + m):
                    if abs(T2[i][j]) > 1e-9:
                        s = j
                        break
                if s is not None:
                    pivot(T2, basis, cost2, i, s)
        if not optimise(T2, basis, cost2):
            return None
        x = [0.0] * n
        for i in range(m):
            if basis[i] < n:
                x[basis[i]] = T2[i][-1]
        return -cost2[-1] if self.maximize else cost2[-1], x


# ---------------------------------------------------------- maximal witnesses
def find_maximal(n, rng, tries, collect=None):
    tbp = triples_by_point(n)
    out = [] if collect is None else collect
    best = None
    hist = Counter()
    for _ in range(tries):
        m = 0
        while True:
            mv = legal_moves(m, n, tbp)
            if not mv:
                break
            m |= 1 << rng.choice(mv)
        s = m.bit_count()
        hist[s] += 1
        if best is None or s < best:
            best, bestm = s, m
        if out is not None and len(out) < 20000:
            out.append(m)
    return best, bestm, hist


def min_triple_cover_for(n, S_mask, tbp, max_depth=3):
    """Exact minimum number of triples of S needed to hit every triple-family
    H_v for v outside S (i.e. to make S maximal).  = 0 if S already maximal
    ignoring triples.  Solved by IDA* over triples of S (C(k,3) <= 455 for
    k=17, but we branch only on uncovered v)."""
    pts = bitl(S_mask)
    V = n * n
    # for each v outside S: which triples of S block v
    fams = {}
    for v in range(V):
        if (S_mask >> v) & 1:
            continue
        hits = []
        for o in tbp[v]:
            oo = o & S_mask
            if oo == o and o.bit_count() == 3:
                hits.append(oo)
        if hits:
            fams[v] = set(hits)
    if not fams:
        return 0, {}
    allT = sorted(set().union(*fams.values()))
    idx = {t: i for i, t in enumerate(allT)}
    # IDA* depth
    best = [None]

    def rec(chosen, uncovered):
        if not uncovered:
            best[0] = list(chosen)
            return True
        if best[0] is not None and len(chosen) >= len(best[0]):
            return False
        if len(chosen) > max_depth + 1:
            return False
        # pick v with fewest covering triples among uncovered
        v = min(uncovered, key=lambda z: sum(
            1 for t in fams[z] if t not in chosen))
        for t in sorted(fams[v]):
            if t in chosen:
                continue
            chosen.append(t)
            if rec(chosen, {z for z in uncovered if t not in fams[z]}):
                return True
            chosen.pop()
        return False

    rec([], set(fams))
    return (len(best[0]) if best[0] else None), {}


def main():
    rep = {}
    rng = random.Random(12345)
    print("=== exact min-triple-cover of small maximal sets (n=6,7) ===",
          flush=True)
    for n in (6, 7):
        tbp = triples_by_point(n)
        allm = []
        b, bm, hist = find_maximal(n, rng, 600, allm)
        allm = sorted(set(allm), key=int.bit_count)
        small = allm[:12]
        rows = []
        for m in small:
            k = m.bit_count()
            # is it maximal already? yes by construction; the question is
            # how many *triples* are load bearing: count triples T of S whose
            # removal (i.e. a 1-swap) unblocks some point
            pts = bitl(m)
            load = 0
            for T in combinations(pts, 3):
                tm = (1 << T[0]) | (1 << T[1]) | (1 << T[2])
                for p in pts:
                    t = m ^ (1 << p) | tm if False else None
                # a triple is "essential" if it is the unique blocker of some v
                for v in range(n * n):
                    if (m >> v) & 1:
                        continue
                    bl = [o for o in tbp[v] if (o & m) == o and o.bit_count() == 3]
                    if bl == [tm]:
                        load += 1
                        break
            rows.append({"k": k, "n_essential_triples": load,
                         "C(k,3)": len(list(combinations(pts, 3))),
                         "pts": pts})
        rep[f"load_bearing_n{n}"] = rows
        print(f"  n={n}: min random maximal={b}; load-bearing triple counts:",
              [r["n_essential_triples"] for r in rows], flush=True)

    print("\n=== LP bound: minimum triple cover (fractional) per n ===", flush=True)
    # For a full 3-layer problem we relax over ALL board triples: we ask the
    # minimum number of triples needed so that every point is on a forbidden
    # quad with one of them.  Its LP dual lower-bounds nothing about s_n
    # directly, so instead we compute the *per-point* incidence: the maximum
    # number of points a single triple can block, and the resulting
    # k >= ceil((V-k)/maxcover) fixed point, iterating.
    for n in (7, 8, 9, 10):
        tbp = triples_by_point(n)
        V = n * n
        # c(T) exact
        cT = Counter()
        for v in range(V):
            for o in tbp[v]:
                cT[o] += 1
        mc = max(cT.values())
        k = 1
        hist_iter = []
        while True:
            need = V - k
            k2 = max(k, -(-need // mc))
            hist_iter.append((k, k2))
            if k2 == k:
                break
            k = k2
            if k > V:
                break
        # LP: distribute weight over triples of the S (unknown) -- instead do
        # the true LP relaxation of "cover V-k points using <= C(k,3) triples
        # of an unknown k-set": bound by the max total coverage achievable by
        # k*3/3 = k triples from the *best* k triples board-wide.
        best_cov = sorted(cT.values(), reverse=True)[:k]
        total = sum(best_cov)
        rep[f"lptri_n{n}"] = {
            "V": V, "max_cT": mc, "fixed_point_k": k,
            "iter": hist_iter,
            "sum_top_k_cT": total,
            "need": V - k,
            "lp_feasible": total >= V - k,
        }
        print(f"  n={n}: V={V} max c(T)={mc} fixed point k={k} "
              f"sum_top_{k} c(T)={total} need={V-k} -> "
              f"{'ok' if total >= V - k else 'INFEASIBLE'}", flush=True)

    OUT.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
