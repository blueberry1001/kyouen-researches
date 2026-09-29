#!/usr/bin/env python3
"""B278 / B279: exact one-point-update mixing on n=4 (and hole-board comparison).

Markov chain: state = safe set S. Proposal: add or remove one stone uniformly
among the n^2 points (or: uniform over legal moves + random deletions).
We use the standard "add/delete" chain restricted to safe sets:
  - From S, pick a point p uniformly from all V points.
  - If p not in S and S+{p} safe: go to S+{p}.
  - If p in S: go to S-{p}.
  - Else: stay.

This is reversible with uniform stationary on safe sets? Not quite — need
Metropolis. We'll use the "heat-bath / Glauber" chain that targets uniform:
  pick p uniformly; resample occupancy of p conditional on others (if both
  S and S+{p} safe, go 50-50; if only one is safe, go there; if neither, stay).

Second eigenvalue vs lambda (tilted measure) is what we want, but B278 is
about mixing of the local update as density changes. We report:
  - exact transition matrix eigenvalues for n=4 (5811 states — too big for dense)
  - power iteration for top-2 eigenvalues at several lambda
  - comparison with a "hole" board (remove one point) for B279.

For n=5 (151k) use power iteration only.
"""
import json
from pathlib import Path
from collections import defaultdict
from itertools import combinations

import numpy as np
from scipy.sparse import lil_matrix, csr_matrix
from scipy.sparse.linalg import eigs

OUT = Path(r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round5_b278_mixing.json")


def det4(rows):
    a = [[int(rows[i][j]) for j in range(4)] for i in range(4)]
    total = 0
    for i in range(4):
        mm = [[a[r2][c2] for c2 in range(1, 4)] for r2 in range(4) if r2 != i]
        d3 = (mm[0][0] * (mm[1][1] * mm[2][2] - mm[1][2] * mm[2][1])
              - mm[0][1] * (mm[1][0] * mm[2][2] - mm[1][2] * mm[2][0])
              + mm[0][2] * (mm[1][0] * mm[2][1] - mm[1][1] * mm[2][0]))
        total += (1 if i % 2 == 0 else -1) * a[i][0] * d3
    return total


def build_geometry(n, hole=None):
    V = n * n
    pts = [(x, y) for y in range(n) for x in range(n)]
    active = [True] * V
    if hole is not None:
        active[hole] = False
    rows = [(x * x + y * y, x, y, 1) for (x, y) in pts]
    triples = [[] for _ in range(V)]
    quads = []
    for a, b, c, d in combinations(range(V), 4):
        if not (active[a] and active[b] and active[c] and active[d]):
            continue
        if det4([rows[a], rows[b], rows[c], rows[d]]) == 0:
            q = (a, b, c, d)
            quads.append(q)
            for t in q:
                triples[t].append(tuple(x for x in q if x != t))
    return V, pts, active, triples, quads


def legal(mask, triples, p, V):
    """Can we place stone at p given occupancy bitmask (as frozenset)?"""
    if p in mask:
        return False
    for t in triples[p]:
        if all(x in mask for x in t):
            return False
    return True


def enumerate_safe(n, hole=None):
    V, pts, active, triples, quads = build_geometry(n, hole)
    # BFS over safe sets
    from collections import deque
    start = frozenset()
    seen = {start}
    q = deque([start])
    while q:
        s = q.popleft()
        for p in range(V):
            if not active[p] or p in s:
                continue
            if legal(s, triples, p, V):
                ns = s | {p}  # frozenset | set -> need frozenset
                ns = frozenset(s | {p})
                if ns not in seen:
                    seen.add(ns)
                    q.append(ns)
    return seen, V, triples, active, pts


def build_chain(states, V, triples, active, lam):
    """Glauber chain tilted by lam^{|S|}.
    Transition: pick p in active uniformly (V' = #active).
    Resample x_p given others (Metropolis toward pi(S) ∝ lam^{|S|}).
    """
    idx = {s: i for i, s in enumerate(states)}
    n = len(states)
    # pi(S) ∝ lam^{|S|} — work with log or exact if lam int
    # We'll build the transition matrix for power iteration with the
    # symmetric version: P'(i,j) = P(i,j) * pi(j)/sqrt(pi(i)pi(j))
    # Actually easier: standard Metropolis.
    Va = sum(1 for p in range(V) if active[p])
    # For each state, list reachable neighbors by toggling one active point
    # if the result is safe.
    # Precompute for each state the safe toggles.
    # Memory: 5811 * 36 * 8 bytes fine.
    states_list = list(states)
    # Build adjacency: list of (j, prob) per i
    # Metropolis for target pi(S)=lam^{|S|}/Z:
    # propose p uniform among Va active points;
    #   if currently 0 and can add: propose S+p, accept with min(1, lam)
    #   if currently 1: propose S-p, accept with min(1, 1/lam)
    #   else stay (or if proposal illegal, stay)
    rows = []
    cols = []
    vals = []
    for i, s in enumerate(states_list):
        acc = np.zeros(n)
        stay = 1.0
        for p in range(V):
            if not active[p]:
                continue
            if p in s:
                ns = frozenset(s - {p})
                # always legal (subset of safe is safe)
                j = idx[ns]
                acc_prob = min(1.0, 1.0 / lam) if lam > 0 else 1.0
                acc[j] += (1.0 / Va) * acc_prob
                stay -= (1.0 / Va) * acc_prob
            else:
                if legal(s, triples, p, V):
                    ns = frozenset(s | {p})
                    j = idx[ns]
                    acc_prob = min(1.0, lam) if lam > 0 else 1.0
                    acc[j] += (1.0 / Va) * acc_prob
                    stay -= (1.0 / Va) * acc_prob
                # else illegal: stay
        acc[i] += max(stay, 0.0)
        for j, v in enumerate(acc):
            if v > 0:
                rows.append(i)
                cols.append(j)
                vals.append(v)
    P = csr_matrix((vals, (rows, cols)), shape=(n, n))
    return P


def top_eigs(P, k=4):
    # eigenvalues of P
    try:
        vals = eigs(P, k=k, which="LM", return_eigenvectors=False, maxiter=5000)
        vals = sorted(vals, key=lambda z: -abs(z))
        return [{"re": float(v.real), "im": float(v.imag), "abs": float(abs(v))} for v in vals]
    except Exception as e:
        return [{"error": str(e)}]


def main():
    out = {}
    # n=4 full
    print("enumerate n=4 ...")
    states, V, triples, active, pts = enumerate_safe(4)
    out["n4_nstates"] = len(states)
    print("nstates", len(states))
    lam_list = [0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 8.0, 13.0, 21.0]
    n4_eigs = {}
    for lam in lam_list:
        print("lam", lam)
        P = build_chain(states, V, triples, active, lam)
        e = top_eigs(P, k=4)
        n4_eigs[str(lam)] = e
        print("  eigs", e)
    out["n4_eigs"] = n4_eigs

    # hole board: remove center point (id = 2*4+2 = 10)
    print("enumerate n=4 hole center ...")
    states_h, Vh, triples_h, active_h, pts_h = enumerate_safe(4, hole=10)
    out["n4hole_nstates"] = len(states_h)
    print("nstates_hole", len(states_h))
    n4h_eigs = {}
    for lam in lam_list:
        print("hole lam", lam)
        P = build_chain(states_h, Vh, triples_h, active_h, lam)
        e = top_eigs(P, k=4)
        n4h_eigs[str(lam)] = e
        print("  eigs", e)
    out["n4hole_eigs"] = n4h_eigs

    # B279: find lam where E[|S|] matches between boards, compare gap
    def gap_of(eigs):
        if not eigs or "error" in eigs[0]:
            return None
        if len(eigs) < 2:
            return None
        return eigs[1]["abs"]

    out["B278_summary"] = {
        "lam_list": lam_list,
        "n4_gaps": {str(lam): gap_of(n4_eigs[str(lam)]) for lam in lam_list},
        "n4hole_gaps": {str(lam): gap_of(n4h_eigs[str(lam)]) for lam in lam_list},
    }
    # find slowest mixing lam for each
    def argmin_gap(gaps):
        best = None
        for k, v in gaps.items():
            if v is None:
                continue
            if best is None or v < gaps[best]:
                best = k
        return best
    out["B278_slowest_n4"] = argmin_gap(out["B278_summary"]["n4_gaps"])
    out["B278_slowest_n4hole"] = argmin_gap(out["B278_summary"]["n4hole_gaps"])

    OUT.write_text(json.dumps(out, indent=2))
    print("WROTE", OUT)
    print(json.dumps(out["B278_summary"], indent=2))


if __name__ == "__main__":
    main()
