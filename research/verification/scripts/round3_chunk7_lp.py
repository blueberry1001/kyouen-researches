#!/usr/bin/env python3
"""Exact-dual LP solver for the 7x7 corridor cover problem (B440).

Primal (cover, |Q| quads, thousands of candidate constraints):
    (P)  min  sum_{q in Q} x_q   s.t.  for every candidate c:
                                     sum_{q in c} x_q >= 1,     x_q >= 0.

Dual (packing), |Q| variables, |Q| constraints:
    (D)  max  sum_{q in Q} y_q   s.t.  for every candidate c:
                                      sum_{q in c} y_q <= 1,     y_q >= 0.

Wait -- that is NOT the dual.  The dual of (P) has one variable per
CONSTRAINT of (P), i.e. one per candidate, and one constraint per variable of
(P), i.e. one per quad:

    (D)  max  sum_c y_c          s.t.  for every quad q:
                                      sum_{c : q in c} y_c <= 1,  y_c >= 0.

The dual therefore has |candidates| variables and only |Q| constraints, so it
is solved with a dense revised primal simplex on a (|Q| x |candidates|)
matrix.  A greedy integral packing of size k is a feasible point of value k,
so the dual optimum >= k; the simplex finds the exact optimum.

Implementation: numpy for the basis algebra, then an EXACT rational
recomputation (Fraction Gaussian elimination on the |Q| x |Q| basis) and an
exact feasibility check of all |Q| constraints.  A returned value is exact.
"""
from __future__ import annotations

from collections import defaultdict
from fractions import Fraction

import numpy as np


def build_matrix(cand_quads, nquads):
    """M[q, c] = 1 iff quad q is contained in candidate c."""
    M = np.zeros((nquads, len(cand_quads)))
    for ci, qs in enumerate(cand_quads):
        for q in qs:
            M[q, ci] = 1.0
    return M


def dual_packing_lp(M, nquads, max_iter=20000, tol=1e-9):
    """max 1^T y s.t. M y <= 1, y >= 0 via revised simplex.

    Returns (status, basis) with status in {'optimal','unbounded','iterlimit'}.
    """
    ncand = M.shape[1]
    basis = np.full(nquads, -1, dtype=np.int64)   # -1 = slack
    cB = np.zeros(nquads)
    Binv = np.eye(nquads)
    xB = np.ones(nquads)
    ones = np.ones(ncand)
    for _ in range(max_iter):
        pi = cB @ Binv
        rc = ones - M.T @ pi
        is_basic = np.zeros(ncand, dtype=bool)
        for b in basis:
            if b >= 0:
                is_basic[b] = True
        rc = np.where(is_basic, -1.0, rc)          # basic vars cannot re-enter
        if rc.max() <= tol:
            return "optimal", basis
        cstar = int(np.argmax(rc))
        u = Binv @ M[:, cstar]
        pos = np.where(u > tol)[0]
        if pos.size == 0:
            return "unbounded", basis
        ratios = xB[pos] / u[pos]
        k = int(np.argmin(ratios))
        r = int(pos[k])
        theta = float(ratios[k])
        piv = u[r]
        Binv = (Binv - np.outer(u, Binv[r, :])) / piv
        xB = xB - theta * u
        xB[r] = theta
        basis[r] = cstar
        cB[r] = 1.0
    return "iterlimit", basis


def exact_value(M, nquads, basis):
    """Exact basic solution of the optimal basis; returns (value, {cand: Fraction})
    or (None, None)."""
    basic = [int(b) for b in basis if b >= 0]
    if len(basic) != nquads:
        return None, None
    # exact basis matrix  Mc[i][q] = M[q, basic[i]]
    Mc = [[Fraction(1) if M[q, c] > 0 else Fraction(0) for q in range(nquads)]
          for c in basic]
    A = [row[:] + [Fraction(1)] for row in Mc]
    used = [False] * nquads
    for col in range(nquads):
        r = -1
        for i in range(nquads):
            if not used[i] and A[i][col] != 0:
                r = i
                break
        if r < 0:
            return None, None
        used[r] = True
        pv = A[r][col]
        A[r] = [v / pv for v in A[r]]
        for i in range(nquads):
            if i != r and A[i][col] != 0:
                f = A[i][col]
                A[i] = [A[i][j] - f * A[r][j] for j in range(nquads + 1)]
    xb = [A[i][nquads] for i in range(nquads)]
    pos_of = {b: i for i, b in enumerate(basic)}
    y = defaultdict(Fraction)
    for b in basis:
        b = int(b)
        if b >= 0:
            y[b] = xb[pos_of[b]]
    if any(v < 0 for v in y.values()):
        return None, None
    val = sum(y.values(), Fraction(0))
    return val, dict(y)


def verify_dual(M, nquads, y):
    """Exact check: for every quad q, sum_{c : M[q,c]>0} y_c <= 1."""
    worst = Fraction(0)
    for q in range(nquads):
        s = Fraction(0)
        for c, v in y.items():
            if v != 0 and M[q, c] > 0:
                s += v
        if s > 1:
            worst = max(worst, s - 1)
    return worst


def solve(cand_quads, nquads, verbose=False):
    M = build_matrix(cand_quads, nquads)
    status, basis = dual_packing_lp(M, nquads)
    if status != "optimal":
        return {"status": status}
    val, y = exact_value(M, nquads, basis)
    if val is None:
        return {"status": "exact_recompute_failed"}
    viol = verify_dual(M, nquads, y)
    return {
        "status": "optimal",
        "n_quads": nquads,
        "n_candidates": len(cand_quads),
        "dual_exact": str(val),
        "dual_float": float(val),
        "support_size": len(y),
        "max_constraint_violation": str(viol),
        "feasible": viol == 0,
        "support": {str(c): str(v) for c, v in sorted(y.items())},
    }


def quad_candidate_index(cand_quads, nquads):
    idx = defaultdict(list)
    for ci, qs in enumerate(cand_quads):
        for q in qs:
            idx[q].append(ci)
    return idx
