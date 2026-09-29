#!/usr/bin/env python3
"""B290 rank cuts for n=5 without full 2^25 safe-set enumeration.
width(U) is computed by brute force on U only (|U|<=20).

Writes round5_b271_fu_b290n5.json
"""
from __future__ import annotations

import json
import sys
from fractions import Fraction
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, det4, square_points

OUT = Path(__file__).resolve().parents[1] / "round5_b271_fu_b290n5.json"


def _det_row(pt):
    x, y = pt
    return (x * x + y * y, x, y, 1)


def enumerate_carriers(pts):
    V = len(pts)
    seen = set()
    carriers = []
    for i, j, k in combinations(range(V), 3):
        ri, rj, rk = _det_row(pts[i]), _det_row(pts[j]), _det_row(pts[k])
        memb = [t for t, pt in enumerate(pts) if det4(ri, rj, rk, _det_row(pt)) == 0]
        if len(memb) < 4:
            continue
        fs = frozenset(memb)
        if fs not in seen:
            seen.add(fs)
            carriers.append(fs)
    return carriers


def solve_lp_max_frac(c, A, b, max_iter=200000):
    m = len(A)
    n = len(c)
    T = []
    for i in range(m):
        row = [Fraction(A[i][j]) for j in range(n)] + [Fraction(int(k == i)) for k in range(m)] + [Fraction(b[i])]
        T.append(row)
    z = [Fraction(c[j]) for j in range(n)] + [Fraction(0)] * m + [Fraction(0)]
    basis = [n + i for i in range(m)]
    for _ in range(max_iter):
        col = -1
        for j in range(n + m):
            if z[j] > 0 and (col < 0 or z[j] > z[col]):
                col = j
        if col < 0:
            break
        r = -1
        br = None
        for i in range(m):
            if T[i][col] > 0:
                ratio = T[i][-1] / T[i][col]
                if br is None or ratio < br:
                    br = ratio
                    r = i
        if r < 0:
            raise ValueError("LP unbounded")
        piv = T[r][col]
        T[r] = [v / piv for v in T[r]]
        z = [z[j] - z[col] * T[r][j] for j in range(len(z))]
        for i in range(m):
            if i != r and T[i][col] != 0:
                fac = T[i][col]
                T[i] = [T[i][j] - fac * T[r][j] for j in range(len(T[i]))]
        basis[r] = col
    x = [Fraction(0)] * n
    for i, bi in enumerate(basis):
        if bi < n:
            x[bi] = T[i][-1]
    return -z[-1], x


def width_on_U(pts, quads, U):
    """max |S ∩ U| over safe S. Brute force on U only."""
    U = list(U)
    k = len(U)
    if k > 22:
        return None
    # induced quads fully inside U
    idx = {p: i for i, p in enumerate(U)}
    ind_quads = []
    for q in quads:
        ms = [p for p in range(len(pts)) if (q >> p) & 1]
        if all(p in idx for p in ms):
            m = 0
            for p in ms:
                m |= 1 << idx[p]
            ind_quads.append(m)
    best = 0
    for occ in range(1 << k):
        sz = occ.bit_count()
        if sz <= best:
            continue
        ok = True
        for q in ind_quads:
            if (occ & q) == q:
                ok = False
                break
        if ok:
            best = sz
    return best


def main():
    n = 5
    pts = square_points(n)
    V = n * n
    b = Board(pts, name="5x5")
    print("carriers ...", flush=True)
    carriers = enumerate_carriers(pts)
    print(f"  {len(carriers)}", flush=True)
    A = []
    bb = []
    for car in carriers:
        row = [0] * V
        for p in car:
            row[p] = 1
        A.append(row)
        bb.append(3)
    for p in range(V):
        row = [0] * V
        row[p] = 1
        A.append(row)
        bb.append(1)
    print("initial LP ...", flush=True)
    obj, x = solve_lp_max_frac([1] * V, A, bb)
    print(f"  frac={float(obj)}", flush=True)

    cuts = []
    iterations = []
    for it in range(15):
        support = [p for p in range(V) if x[p] > 0]
        heavy = [p for p in range(V) if x[p] >= Fraction(1, 2)]
        cands = []
        if 5 <= len(support) <= 20:
            cands.append(frozenset(support))
        if 5 <= len(heavy) <= 20:
            cands.append(frozenset(heavy))
        # carrier pairs, limit candidates
        for c1, c2 in combinations(carriers, 2):
            U = c1 | c2
            if 8 <= len(U) <= 18:
                cands.append(U)
        added = 0
        seen_u = set()
        # prioritize: smaller |U| first (cheaper width) and those with high x-sum
        scored = []
        for U in cands:
            if U in seen_u:
                continue
            seen_u.add(U)
            su = sum(x[p] for p in U)
            scored.append((float(su), U))
        scored.sort(key=lambda t: -t[0])
        # only compute width for top candidates with high x-sum and small |U|
        scored = [(su, U) for su, U in scored if len(U) <= 16][:40]
        for su_f, U in scored:
            su = sum(x[p] for p in U)
            w = width_on_U(pts, b.quads, U)
            if w is None:
                continue
            if su > w:
                cuts.append({
                    "U": sorted(U),
                    "rhs": w,
                    "violated_sum": f"{su.numerator}/{su.denominator}",
                    "it": it,
                })
                row = [0] * V
                for p in U:
                    row[p] = 1
                A.append(row)
                bb.append(w)
                added += 1
        print(f"  it={it} frac={float(obj)} added={added} total={len(cuts)}", flush=True)
        iterations.append({"it": it, "frac": float(obj), "n_added": added, "n_total": len(cuts)})
        if added == 0:
            break
        obj, x = solve_lp_max_frac([1] * V, A, bb)

    res = {
        "n": n,
        "K_n": 9,
        "n_carriers": len(carriers),
        "final_frac": f"{obj.numerator}/{obj.denominator}",
        "final_frac_float": float(obj),
        "gap_after_cuts": float(obj - 9),
        "n_cuts": len(cuts),
        "cuts_sample": cuts[:25],
        "iterations": iterations,
    }
    OUT.write_text(json.dumps(res, indent=2, default=str))
    print("WROTE", OUT, "final", res["final_frac"], "gap", res["gap_after_cuts"], flush=True)


if __name__ == "__main__":
    main()
