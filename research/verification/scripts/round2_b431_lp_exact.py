#!/usr/bin/env python3
"""Exact verifier for round-2 B431-B434 static cover claims.

No optimizer is required for verification. The JSON contains:
- an integer 21-cover,
- a fractional primal cover of weight 102/5,
- a fractional dual packing of weight 204/10 = 102/5.

Weak duality gives fractional optimum 102/5. Since any integer cover has
integer size, it is at least ceil(102/5)=21; the stored 21-cover is feasible,
so the integer optimum is exactly 21.
"""
from __future__ import annotations

import argparse
import itertools
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CERT = ROOT / "research/verification/round2_b431_lp_exact.json"


def det4(points, n=7):
    a = []
    for p in points:
        x, y = p % n, p // n
        a.append([x * x + y * y, x, y, 1])
    sign = 1
    prev = 1
    for k in range(3):
        pivot_row = next((r for r in range(k, 4) if a[r][k] != 0), None)
        if pivot_row is None:
            return 0
        if pivot_row != k:
            a[k], a[pivot_row] = a[pivot_row], a[k]
            sign *= -1
        pivot = a[k][k]
        for i in range(k + 1, 4):
            for j in range(k + 1, 4):
                a[i][j] = (a[i][j] * pivot - a[i][k] * a[k][j]) // prev
        prev = pivot
    return sign * a[3][3]


def build_instance(cert):
    u = cert["universe"]
    cells = u["cells"]
    a_only = set(u["A_only"])
    b_only = set(u["B_only"])

    quads = [
        q for q in itertools.combinations(cells, 4)
        if det4(q, u["board_n"]) == 0
    ]

    candidates = []
    size_hist = Counter()
    for size in range(13, 20):
        for s in itertools.combinations(cells, size):
            d = sum(p in b_only for p in s) - sum(p in a_only for p in s)
            if d in (2, 3):
                fs = frozenset(s)
                candidates.append(fs)
                size_hist[size] += 1

    return quads, candidates, size_hist


def verify(cert):
    quads, candidates, size_hist = build_instance(cert)
    u = cert["universe"]

    assert len(quads) == u["n_forbidden_quads_in_U"] == 59
    assert len(candidates) == u["n_candidates"] == 6460
    assert {str(k): v for k, v in size_hist.items()} == u["candidate_size_hist"]

    qsets = [frozenset(q) for q in quads]

    # Integer feasible cover.
    integer_idx = cert["integer_cover"]["quad_indices"]
    assert len(integer_idx) == cert["integer_cover"]["size"] == 21
    integer_q = [qsets[i] for i in integer_idx]
    assert all(any(q <= c for q in integer_q) for c in candidates)

    # Fractional primal: every candidate receives load >= denominator.
    fp = cert["fractional_primal"]
    fp_terms = [(qsets[i], num) for i, num in fp["terms"]]
    min_load = min(
        sum(num for q, num in fp_terms if q <= c)
        for c in candidates
    )
    assert min_load >= fp["denominator"]
    assert sum(num for _, num in fp["terms"]) == fp["objective_numerator"] == 102

    # Fractional dual: every quad receives candidate-weight load <= denominator.
    fd = cert["fractional_dual"]
    fd_terms = [(candidates[i], num) for i, num in fd["terms"]]
    max_load = max(
        sum(num for c, num in fd_terms if q <= c)
        for q in qsets
    )
    assert max_load <= fd["denominator"]
    assert sum(num for _, num in fd["terms"]) == fd["objective_numerator"] == 204

    # Exact equality of primal and dual objectives: 102/5 = 204/10.
    assert fp["objective_numerator"] * fd["denominator"] == (
        fd["objective_numerator"] * fp["denominator"]
    )

    result = {
        "n_quads": len(quads),
        "n_candidates": len(candidates),
        "integer_cover_feasible_size": len(integer_idx),
        "fractional_primal_min_load": f"{min_load}/{fp['denominator']}",
        "fractional_dual_max_load": f"{max_load}/{fd['denominator']}",
        "fractional_optimum": "102/5",
        "fractional_optimum_decimal": 20.4,
        "integer_optimum": 21,
        "packing_max_upper_bound": 20,
        "B431": "SUPPORTED",
        "B432": "REFUTED",
        "B433": "SUPPORTED",
        "B434": "REFUTED",
    }
    return result


def solve_with_scipy(cert):
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, linprog, milp
    from scipy.sparse import csr_matrix

    quads, candidates, _ = build_instance(cert)
    qsets = [frozenset(q) for q in quads]
    rows, cols = [], []
    for i, c in enumerate(candidates):
        for j, q in enumerate(qsets):
            if q <= c:
                rows.append(i)
                cols.append(j)
    A = csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(candidates), len(quads)))
    obj = np.ones(len(quads))

    lp = linprog(obj, A_ub=-A, b_ub=-np.ones(len(candidates)), bounds=(0, 1), method="highs")
    assert lp.success and abs(lp.fun - 20.4) < 1e-8

    ic = LinearConstraint(A, lb=np.ones(len(candidates)), ub=np.full(len(candidates), np.inf))
    ip = milp(
        obj,
        integrality=np.ones(len(quads)),
        bounds=Bounds(np.zeros(len(quads)), np.ones(len(quads))),
        constraints=ic,
    )
    assert ip.success and abs(ip.fun - 21.0) < 1e-8
    return {"lp": lp.fun, "ilp": ip.fun}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--solve", action="store_true", help="also re-solve LP/ILP with SciPy/HiGHS")
    args = ap.parse_args()

    cert = json.loads(CERT.read_text(encoding="utf-8"))
    result = verify(cert)
    if args.solve:
        result["solver_check"] = solve_with_scipy(cert)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
