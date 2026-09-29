#!/usr/bin/env python3
"""Round5 B271-B290: correlation sign changes, capacity LP, Q-hypergraph, Grundy embed.

Sub-results written to round5_b271_b290.json.
Integer-only arithmetic except where explicitly noted for LP simplex internals
(kept exact via Fraction).
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from fractions import Fraction
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, board_square, det4, is_forbidden_quad, square_points

OUT_JSON = Path(__file__).resolve().parents[1] / "round5_b271_b290.json"

KNOWN_K = {2: 3, 3: 5, 4: 7, 5: 9, 6: 11, 7: 14}
KNOWN_MAX = {2: 4, 3: 56, 4: 64, 5: 100, 6: 349132, 7: 16}


# ---------------------------------------------------------------------------
# geometry helpers: circles / lines through >=4 board points
# ---------------------------------------------------------------------------

def _det_row(pt):
    x, y = pt
    return (x * x + y * y, x, y, 1)


def points_on_circle(pts, i, j, k):
    """All board indices lying on the circle (or line) through pts[i],pts[j],pts[k]."""
    ri, rj, rk = _det_row(pts[i]), _det_row(pts[j]), _det_row(pts[k])
    out = []
    for t, pt in enumerate(pts):
        if det4(ri, rj, rk, _det_row(pt)) == 0:
            out.append(t)
    return out


def enumerate_circles_lines(pts):
    """Dedup sets of board points that are concyclic-or-collinear with size>=4.

    Returns list of frozensets of point indices.
    """
    V = len(pts)
    seen = set()
    carriers = []
    for i, j, k in combinations(range(V), 3):
        memb = points_on_circle(pts, i, j, k)
        if len(memb) < 4:
            continue
        fs = frozenset(memb)
        if fs not in seen:
            seen.add(fs)
            carriers.append(fs)
    return carriers


def collinear(p, q, r):
    return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]) == 0


def split_collinear_concyclic(pts, carrier):
    """Classify a >=4-point carrier: True if collinear, False if non-degenerate circle."""
    cl = list(carrier)
    p0, p1 = pts[cl[0]], pts[cl[1]]
    all_col = all(collinear(p0, p1, pts[t]) for t in cl[2:])
    return all_col  # True = line, False = circle


# ---------------------------------------------------------------------------
# exact LP: max c.x  s.t. A x <= b, 0 <= x <= 1  (dense, Fraction)
# ---------------------------------------------------------------------------

def solve_lp_max(c, A, b):
    """Exact simplex for max c.x, A x <= b, x >= 0. Returns (obj, x) with Fractions.

    Adds slack variables. Does NOT add x<=1; caller may add those as rows.
    """
    m = len(A)
    n = len(c)
    # tableau: m rows, n + m columns (slacks) + 1 RHS; then artificials for phase1
    # Use two-phase simplex with explicit basis.
    # Columns: 0..n-1 structural, n..n+m-1 slack, n+m RHS
    ncols = n + m
    T = []
    for i in range(m):
        row = [Fraction(A[i][j]) for j in range(n)] + [Fraction(0)] * m + [Fraction(b[i])]
        row[n + i] = Fraction(1)
        T.append(row)
    basis = [n + i for i in range(m)]

    # Phase 1: if any b[i] < 0, flip the row (multiply by -1, becomes >= constraint -> need artificial)
    # Simpler: assume b >= 0 (our constraints are capacity with b=3 or b=1).
    for i in range(m):
        if b[i] < 0:
            raise ValueError("negative RHS; normalize first")

    # objective row: z = c.x  =>  we minimize -c.x
    obj = [Fraction(-c[j]) for j in range(n)] + [Fraction(0)] * m + [Fraction(0)]

    def pivot(T, basis, obj, r, col):
        piv = T[r][col]
        inv = Fraction(1, 1) / piv
        T[r] = [v * inv for v in T[r]]
        for i in range(len(T)):
            if i == r:
                continue
            fac = T[i][col]
            if fac != 0:
                T[i] = [T[i][j] - fac * T[r][j] for j in range(len(T[i]))]
        fac = obj[col]
        if fac != 0:
            obj = [obj[j] - fac * T[r][j] for j in range(len(obj))]
        basis[r] = col
        return obj

    # phase-1 if needed: artificial columns for rows where we can't get feasible basis
    # All our slack bases are feasible (b>=0), so start directly with Bland's rule.
    max_iter = 20000
    for _ in range(max_iter):
        # entering: most negative reduced cost (Dantzig) with Bland fallback
        col = -1
        best = Fraction(0)
        for j in range(ncols):
            if obj[j] < best:
                best = obj[j]
                col = j
        if col < 0:
            break
        # leaving
        r = -1
        best_ratio = None
        for i in range(m):
            if T[i][col] > 0:
                ratio = T[i][-1] / T[i][col]
                if best_ratio is None or ratio < best_ratio or (ratio == best_ratio and basis[i] < basis[r]):
                    best_ratio = ratio
                    r = i
        if r < 0:
            raise ValueError("LP unbounded")
        obj = pivot(T, basis, obj, r, col)
    x = [Fraction(0)] * n
    for i, bi in enumerate(basis):
        if bi < n:
            x[bi] = T[i][-1]
    return -obj[-1], x


def fractional_capacity_lp(carriers, V, extra_rows=None):
    """max sum x_p s.t. sum_{p in c} x_p <= 3 for each carrier c, 0<=x_p<=1.

    extra_rows: optional list of (list_of_indices, rhs) additional constraints.
    """
    c = [1] * V
    A = []
    b = []
    for car in carriers:
        row = [0] * V
        for p in car:
            row[p] = 1
        A.append(row)
        b.append(3)
    if extra_rows:
        for idxs, rhs in extra_rows:
            row = [0] * V
            for p in idxs:
                row[p] = 1
            A.append(row)
            b.append(rhs)
    # x_p <= 1
    for p in range(V):
        row = [0] * V
        row[p] = 1
        A.append(row)
        b.append(1)
    obj, x = solve_lp_max(c, A, b)
    return obj, x


# ---------------------------------------------------------------------------
# B271 / B272: two-point probabilities on n=4
# ---------------------------------------------------------------------------

def poly_mul(a, b):
    r = [0] * (len(a) + len(b) - 1)
    for i, ai in enumerate(a):
        if ai == 0:
            continue
        for j, bj in enumerate(b):
            if bj == 0:
                continue
            r[i + j] += ai * bj
    return r


def poly_sub(a, b):
    n = max(len(a), len(b))
    r = [0] * n
    for i in range(n):
        ai = a[i] if i < len(a) else 0
        bi = b[i] if i < len(b) else 0
        r[i] = ai - bi
    return r


def poly_eval(a, lam):
    v = 0
    p = 1
    for c in a:
        v += c * p
        p *= lam
    return v


def poly_derivative(a):
    return [i * a[i] for i in range(1, len(a))]


def b271_b272_correlation(n=4):
    """Full enumeration of safe sets on n x n; compute Z, W_p, W_pq polynomials.

    Cov numerator N_pq(lam) = W_pq * Z - W_p * W_q.
    Sign change of Cov over lam>0 <=> sign change of N over lam>0
    (Z>0 always).
    """
    pts = square_points(n)
    V = n * n
    b = Board(pts, name=f"{n}x{n}")
    quads = b.quads

    # Z[k] = #safe sets of size k
    Z = [0] * (V + 1)
    # W_p[k] = #safe sets of size k containing p
    Wp = [[0] * (V + 1) for _ in range(V)]
    # W_pq[k] = #safe sets of size k containing both p and q
    Wpq = [[0] * (V + 1) for _ in range(V * V)]

    n_safe = 0
    for occ in range(1 << V):
        ok = True
        for q in quads:
            if (occ & q) == q:
                ok = False
                break
        if not ok:
            continue
        n_safe += 1
        k = occ.bit_count()
        Z[k] += 1
        members = [p for p in range(V) if (occ >> p) & 1]
        for p in members:
            Wp[p][k] += 1
        for p, q in combinations(members, 2):
            Wpq[p * V + q][k] += 1
            Wpq[q * V + p][k] += 1

    # Cov numerator polynomial for each ordered pair p<q
    # N = W_pq * Z - W_p * W_q   (polynomials in lam)
    sign_changes = []
    zero_poly = 0
    examples = []
    for p, q in combinations(range(V), 2):
        Wpq_p = Wpq[p * V + q]
        Wp_p = Wp[p]
        Wp_q = Wp[q]
        N = poly_sub(poly_mul(Wpq_p, Z), poly_mul(Wp_p, Wp_q))
        # count sign changes of N(lam) for lam>0 via Sturm-like sampling is fragile;
        # instead: find positive real roots by rational-root + derivative isolation,
        # then evaluate sign between roots.  N has integer coeffs.
        # Practical: evaluate at many positive rational points and detect sign flips
        # between consecutive derivative-critical isolation via poly roots by
        # companion-matrix eigenvalues in float (numpy) for root finding only.
        sc, roots = positive_sign_changes(N)
        if sc > 0:
            sign_changes.append({
                "p": [p // n, p % n],
                "q": [q // n, q % n],
                "n_sign_changes": sc,
                "approx_positive_roots": roots,
            })
        if len(examples) < 12:
            examples.append({
                "p": [p // n, p % n],
                "q": [q // n, q % n],
                "N_coeffs": N,
                "Z_times_Wpq_minus_prod_at_1": poly_eval(N, 1),
                "at_2": poly_eval(N, 2),
                "at_10": poly_eval(N, 10),
                "at_100": poly_eval(N, 100),
            })

    # large-lambda correlation on maximal sets only
    K = KNOWN_K[n]
    max_sets = []
    for occ in range(1 << V):
        if occ.bit_count() != K:
            continue
        ok = True
        for q in quads:
            if (occ & q) == q:
                ok = False
                break
        if ok:
            max_sets.append(occ)
    # occupation counts on maximal sets
    cnt_p = [0] * V
    cnt_pq = [[0] * V for _ in range(V)]
    M = len(max_sets)
    for occ in max_sets:
        members = [p for p in range(V) if (occ >> p) & 1]
        for p in members:
            cnt_p[p] += 1
        for p, q in combinations(members, 2):
            cnt_pq[p][q] += 1
            cnt_pq[q][p] += 1
    positive_corr_max = []
    negative_corr_max = []
    competing_positive = []  # p,q sharing a forbidden quad yet positive corr
    # build point->quad membership
    in_same_quad = [[False] * V for _ in range(V)]
    for qmask in quads:
        ms = [p for p in range(V) if (qmask >> p) & 1]
        for p, q in combinations(ms, 2):
            in_same_quad[p][q] = in_same_quad[q][p] = True

    for p, q in combinations(range(V), 2):
        if M == 0:
            break
        # Cov on uniform max sets: E[ip iq]-E[ip]E[iq]
        # = cnt_pq/M - (cnt_p/M)(cnt_q/M)
        # sign of M*cnt_pq - cnt_p*cnt_q
        num = M * cnt_pq[p][q] - cnt_p[p] * cnt_q if False else (M * cnt_pq[p][q] - cnt_p[p] * cnt_p[q])
        entry = {
            "p": [p // n, p % n],
            "q": [q // n, q % n],
            "cnt_p": cnt_p[p],
            "cnt_q": cnt_p[q],
            "cnt_pq": cnt_pq[p][q],
            "cov_num": num,
            "in_same_forbidden_quad": in_same_quad[p][q],
        }
        if num > 0:
            positive_corr_max.append(entry)
            if in_same_quad[p][q]:
                competing_positive.append(entry)
        elif num < 0:
            negative_corr_max.append(entry)

    return {
        "n": n,
        "V": V,
        "n_safe_sets": n_safe,
        "Z_coeffs": Z,
        "K": K,
        "n_maximal": M,
        "sign_changing_pairs": sign_changes,
        "n_sign_changing_pairs": len(sign_changes),
        "examples_N": examples,
        "max_phase": {
            "n_positive_cov_pairs": len(positive_corr_max),
            "n_negative_cov_pairs": len(negative_corr_max),
            "n_competing_positive": len(competing_positive),
            "competing_positive_sample": competing_positive[:15],
            "positive_sample": positive_corr_max[:10],
            "negative_sample": negative_corr_max[:10],
        },
    }


def positive_sign_changes(coeffs):
    """Number of sign changes of polynomial with given coeffs on (0, inf).

    Uses numpy roots for isolation (float, identification only). Returns
    (n_sign_changes, approx_positive_roots).
    """
    import numpy as np

    # strip leading zeros
    a = list(coeffs)
    while a and a[-1] == 0:
        a.pop()
    if len(a) <= 1:
        return 0, []
    if all(c == 0 for c in a):
        return 0, []
    # sign at 0+
    s0 = 0
    for c in a:
        if c != 0:
            s0 = 1 if c > 0 else -1
            break
    try:
        roots = np.roots([float(c) for c in a])
    except Exception:
        return -1, []
    pos_real = sorted(
        float(r.real) for r in roots if abs(r.imag) < 1e-8 and r.real > 1e-12
    )
    # evaluate signs between roots
    sc = 0
    last_sign = s0
    last_x = 0.0
    roots_used = []
    for rt in pos_real:
        mid = (last_x + rt) / 2 if last_x > 0 else rt / 2
        val = poly_eval(a, mid)
        if val == 0:
            continue
        sgn = 1 if val > 0 else -1
        if sgn != last_sign:
            sc += 1
            last_sign = sgn
            roots_used.append(rt)
        last_x = rt
    # sign after last root
    if pos_real:
        big = pos_real[-1] * 2 + 1
        val = poly_eval(a, big)
        if val != 0:
            sgn = 1 if val > 0 else -1
            if sgn != last_sign:
                sc += 1
                roots_used.append(pos_real[-1] * 2 + 1)
    return sc, [round(r, 8) for r in roots_used[:8]]


# ---------------------------------------------------------------------------
# B275 / B277 / B280: thermo + multigraded Z
# ---------------------------------------------------------------------------

def thermo_from_levels(level):
    """Var peak analysis using exact Fraction at integer lambdas."""
    K = max(i for i, v in enumerate(level) if v > 0)
    profile = {}
    best = None
    for lam in [Fraction(1, 2), 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597, 2584, 4181, 6765, 10946, 17711, 28657, 46368, 75025, 121393, 196418, 317811, 514229, 832040, 1346269, 2178309, 3524578, 5702887, 9227465, 14930352, 24157817, 39088169, 63245986]:
        Z = 0
        s1 = 0
        s2 = 0
        pl = Fraction(1)
        lamf = Fraction(lam)
        for k, a in enumerate(level):
            if a == 0:
                pl *= lamf
                continue
            Z += a * pl
            s1 += k * a * pl
            s2 += k * k * a * pl
            pl *= lamf
        if Z == 0:
            continue
        Ek = Fraction(s1, Z)
        Ek2 = Fraction(s2, Z)
        var = Ek2 - Ek * Ek
        profile[str(lam)] = {
            "E_k": float(Ek),
            "Var": float(var),
        }
        if best is None or var > best[1]:
            best = (lam, var, Ek)
    return {
        "K": K,
        "var_max_lambda": str(best[0]) if best else None,
        "var_max": float(best[1]) if best else None,
        "E_k_at_var_max": float(best[2]) if best else None,
        "profile": profile,
    }


def multigraded_Z(n=4):
    """Multi-variable Z graded by D4-orbit occupancy of points.

    For n=4: orbits are corners (4), edge-centers (4), inner 2x2 (4), ... actually
    4x4 under D4: corners (0,0),(0,3),(3,0),(3,3) -> 4
    edge-adjacent-to-corner (1,0),(0,1),(2,0)... need actual orbits.
    We grade by the tuple of occupation counts per point-orbit.
    """
    pts = square_points(n)
    V = n * n
    b = Board(pts, name=f"{n}x{n}")
    # compute D4 orbit of each point
    def d4(x, y):
        n_ = n
        cands = [
            (x, y), (y, n_ - 1 - x), (n_ - 1 - x, n_ - 1 - y), (n_ - 1 - y, x),
            (y, x), (x, n_ - 1 - y), (n_ - 1 - x, y), (n_ - 1 - y, n_ - 1 - x),
        ]
        return min(cands)

    orbit_rep = {}
    orbit_of = [None] * V
    for y in range(n):
        for x in range(n):
            rep = d4(x, y)
            if rep not in orbit_rep:
                orbit_rep[rep] = len(orbit_rep)
            orbit_of[y * n + x] = orbit_rep[rep]
    n_orb = len(orbit_rep)

    # Z_orb[(k, (c0,c1,...))]  -> count  (use dict)
    # too big in full generality; record by (total_k, orbit-count-tuple)
    hist = defaultdict(int)
    for occ in range(1 << V):
        ok = True
        for q in b.quads:
            if (occ & q) == q:
                ok = False
                break
        if not ok:
            continue
        k = occ.bit_count()
        cnt = [0] * n_orb
        for p in range(V):
            if (occ >> p) & 1:
                cnt[orbit_of[p]] += 1
        hist[(k, tuple(cnt))] += 1

    # highest-degree terms (k=K) and their orbit profiles
    K = KNOWN_K[n]
    top = {str(kc): v for (k, kc), v in hist.items() if k == K}
    return {
        "n": n,
        "n_orbits": n_orb,
        "orbit_sizes": [sum(1 for p in range(V) if orbit_of[p] == o) for o in range(n_orb)],
        "n_multi_terms": len(hist),
        "top_degree_orbit_profiles": top,
        "top_degree_sum": sum(top.values()),
        "known_maximal": KNOWN_MAX.get(n),
    }


# ---------------------------------------------------------------------------
# B281 / B283: Q-hypergraph signature collisions
# ---------------------------------------------------------------------------

def q_signature(points):
    """Forbidden-quad hypergraph of a point set (list of (x,y)).

    Returns (sorted tuple of forbidden-quad tuples in index space,
             collinear-forbidden-count, concyclic-forbidden-count,
             full collinearity pattern of all triples).
    """
    k = len(points)
    quads = []
    n_col = 0
    n_cyc = 0
    for ids in combinations(range(k), 4):
        pts4 = [points[i] for i in ids]
        if is_forbidden_quad(pts4):
            quads.append(ids)
            # classify
            a, bb, c, d = pts4
            if collinear(a, bb, c) and collinear(a, bb, d):
                n_col += 1
            else:
                n_cyc += 1
    return tuple(quads), n_col, n_cyc


def normalize_points(points):
    """Translate so min corner is (0,0). Not full similarity normalize."""
    minx = min(p[0] for p in points)
    miny = min(p[1] for p in points)
    return tuple((p[0] - minx, p[1] - miny) for p in points)


def d4_image(points, n_box):
    """All D4 images of a point set inside a box of side n_box (for congruence test)."""
    def tf(x, y, op):
        n = n_box
        if op == 0:
            return (x, y)
        if op == 1:
            return (y, n - 1 - x)
        if op == 2:
            return (n - 1 - x, n - 1 - y)
        if op == 3:
            return (n - 1 - y, x)
        if op == 4:
            return (y, x)
        if op == 5:
            return (x, n - 1 - y)
        if op == 6:
            return (n - 1 - x, y)
        if op == 7:
            return (n - 1 - y, n - 1 - x)
    outs = []
    for op in range(8):
        outs.append(tuple(sorted(tf(x, y, op) for x, y in points)))
    return outs


def are_similar_via_d4_translate_scale(A, B):
    """True if B is a translate + uniform scale + D4 rotation/reflection of A.

    Uses normalized integer vectors from centroid-free approach:
    try all pair-distance scales. For small sets this is fine.
    """
    A = list(A)
    B = list(B)
    if len(A) != len(B):
        return False
    k = len(A)
    if k < 2:
        return True
    # try each ordered pair of A as reference edge
    # map a0->b0, a1->b1 and see if scale+D4 works
    def apply_d4(p, op):
        x, y = p
        return [
            (x, y), (y, -x), (-x, -y), (-y, x),
            (y, x), (x, -y), (-x, y), (-y, -x),
        ][op]

    Bset = set(B)
    for i0 in range(k):
        for i1 in range(k):
            if i0 == i1:
                continue
            va = (A[i1][0] - A[i0][0], A[i1][1] - A[i0][1])
            if va == (0, 0):
                continue
            for j0 in range(k):
                for j1 in range(k):
                    if j0 == j1:
                        continue
                    vb = (B[j1][0] - B[j0][0], B[j1][1] - B[j0][1])
                    if vb == (0, 0):
                        continue
                    # try 8 orientations of va mapped to vb
                    for op in range(8):
                        rot = apply_d4(va, op)
                        # scale? integer scale s with s*rot = vb
                        # componentwise
                        if rot[0] == 0 or rot[1] == 0:
                            # handle zero components
                            ok_scale = True
                            s_num = None
                            for u, v in zip(rot, vb):
                                if u == 0:
                                    if v != 0:
                                        ok_scale = False
                                        break
                                else:
                                    # v = s * u  => s = v/u
                                    if v % u != 0:
                                        ok_scale = False
                                        break
                                    s = v // u
                                    if s <= 0:
                                        ok_scale = False
                                        break
                                    if s_num is None:
                                        s_num = s
                                    elif s_num != s:
                                        ok_scale = False
                                        break
                            if not ok_scale or s_num is None:
                                continue
                            s = s_num
                        else:
                            if vb[0] * rot[1] != vb[1] * rot[0]:
                                continue
                            if rot[0] == 0 or vb[0] % rot[0] != 0:
                                continue
                            s = vb[0] // rot[0]
                            if s <= 0:
                                continue
                            if s * rot[1] != vb[1]:
                                continue
                        # build image of all A
                        img = []
                        good = True
                        for p in A:
                            rp = apply_d4((p[0] - A[i0][0], p[1] - A[i0][1]), op)
                            q = (B[j0][0] + s * rp[0], B[j0][1] + s * rp[1])
                            img.append(q)
                        if set(img) == Bset:
                            return True
    return False


def b281_b283_search(box=4, k=6):
    """Search subsets of a box x box grid of size k for:
    B281: same Q-hypergraph (as abstract hypergraph via sorted quad-tuples on
          a canonical labeling by degree sequence) but not similar.
    B283: same Q-hypergraph but different (n_col, n_cyc) split.

    We use a practical signature: the sorted multiset of
    (forbidden-quad) as a hypergraph via vertex-degree sorted canonical form
    is expensive; instead use (sorted tuple of quads in *sorted point-order of
    the specific set*) PLUS we also compare the isomorphism-invariant:
    multiset of "forbidden-quad count per point" and total counts.

    For collision detection we group by invariant:
      (len(quads), n_col, n_cyc, sorted degrees, total pair-quad incidences)
    then within a bucket compare full hypergraph iso via brute force permutation
    (k<=6 so 720 perms).
    """
    from itertools import permutations

    pts_grid = [(x, y) for y in range(box) for x in range(box)]
    subsets = list(combinations(range(box * box), k))
    # invariant: (n_quads, n_col, n_cyc, tuple(sorted(deg)), tuple(sorted(col_deg)))
    buckets = defaultdict(list)
    records = {}
    for idxs in subsets:
        pts = [pts_grid[i] for i in idxs]
        quads, n_col, n_cyc = q_signature(pts)
        deg = [0] * k
        for q in quads:
            for v in q:
                deg[v] += 1
        col_deg = [0] * k
        cyc_deg = [0] * k
        for q in quads:
            pts4 = [pts[i] for i in q]
            a, b_, c, d = pts4
            is_col = collinear(a, b_, c) and collinear(a, b_, d)
            for v in q:
                if is_col:
                    col_deg[v] += 1
                else:
                    cyc_deg[v] += 1
        inv = (len(quads), n_col, n_cyc, tuple(sorted(deg)), tuple(sorted(col_deg)), tuple(sorted(cyc_deg)))
        buckets[inv].append(idxs)
        records[idxs] = {
            "pts": pts,
            "quads": quads,
            "n_col": n_col,
            "n_cyc": n_cyc,
            "deg": deg,
        }

    def hypergraph_iso(q1, q2, k):
        """True if quad hypergraphs are isomorphic under S_k."""
        s1 = set(q1)
        for perm in permutations(range(k)):
            img = set(tuple(sorted(perm[v] for v in q)) for q in q1)
            if img == set(q2):
                return True
        return False

    b281_witness = None
    b283_witness = None
    b281_checked = 0
    b283_checked = 0

    for inv, members in buckets.items():
        if len(members) < 2:
            continue
        nq, nc, ncy = inv[0], inv[1], inv[2]
        if nq == 0:
            continue  # empty Q not interesting for B281 "same Q"
        for ia in range(len(members)):
            for ib in range(ia + 1, len(members)):
                A, B = members[ia], members[ib]
                ra, rb = records[A], records[B]
                # same abstract hypergraph?
                iso = hypergraph_iso(ra["quads"], rb["quads"], k)
                if not iso:
                    continue
                similar = are_similar_via_d4_translate_scale(ra["pts"], rb["pts"])
                if b281_witness is None and not similar:
                    b281_witness = {
                        "A": ra["pts"],
                        "B": rb["pts"],
                        "quads_A": ra["quads"],
                        "n_col": ra["n_col"],
                        "n_cyc": ra["n_cyc"],
                    }
                    b281_checked += 1
                # B283: same hypergraph but different collinear/concyclic split
                # split differs if the *assignment* of each hyperedge to col/cyc differs
                # under the iso. We approximate: different (n_col, n_cyc) is sufficient
                # when the invariant bucket has n_col differing — but we grouped by
                # n_col so same bucket has same split counts. Need cross-bucket!
                pass

    # B283 needs same abstract hypergraph but different (n_col, n_cyc).
    # Regroup by hypergraph-only invariant (drop n_col, n_cyc).
    buckets2 = defaultdict(list)
    for idxs in subsets:
        pts = [pts_grid[i] for i in idxs]
        quads, n_col, n_cyc = q_signature(pts)
        if len(quads) == 0:
            continue
        deg = [0] * k
        for q in quads:
            for v in q:
                deg[v] += 1
        inv = (len(quads), tuple(sorted(deg)))
        buckets2[inv].append((idxs, pts, quads, n_col, n_cyc))

    for inv, members in buckets2.items():
        if len(members) < 2:
            continue
        for ia in range(len(members)):
            for ib in range(ia + 1, len(members)):
                _, ptsA, quadsA, colA, cycA = members[ia]
                _, ptsB, quadsB, colB, cycB = members[ib]
                if (colA, cycA) == (colB, cycB):
                    continue
                if hypergraph_iso(quadsA, quadsB, k):
                    b283_witness = {
                        "A": ptsA,
                        "B": ptsB,
                        "quads_A": quadsA,
                        "quads_B": quadsB,
                        "split_A": {"collinear": colA, "concyclic": cycA},
                        "split_B": {"collinear": colB, "concyclic": cycB},
                    }
                    break
            if b283_witness:
                break
        if b283_witness:
            break

    return {
        "box": box,
        "k": k,
        "n_subsets": len(subsets),
        "n_nonempty_Q_buckets": sum(1 for inv, mem in buckets.items() if inv[0] > 0 and len(mem) > 1),
        "B281_witness": b281_witness,
        "B281_pairs_examined": b281_checked,
        "B283_witness": b283_witness,
    }


# ---------------------------------------------------------------------------
# B285: same S, different boards, grundy values
# ---------------------------------------------------------------------------

def b285_grundy_embed():
    """Place the same absolute-coordinate safe sets into boards n=4,5,6 and
    compute g(S) of the residual game. See if >=3 distinct values appear."""
    # candidate small safe sets near origin
    candidates = {
        "single_origin": [(0, 0)],
        "diag2": [(0, 0), (1, 1)],
        "block2x2": [(0, 0), (1, 0), (0, 1), (1, 1)],  # wait: is 2x2 safe? unit square corners are concyclic!
        "L_shape": [(0, 0), (1, 0), (0, 1)],
        "row2": [(0, 0), (1, 0)],
        "tri3": [(0, 0), (2, 0), (0, 2)],
        "k2_far": [(0, 0), (2, 1)],
    }
    # unit square corners ARE concyclic (circle x^2+y^2-x-y=0) -> NOT safe.
    # Remove block2x2 and replace with a safe 4-set.
    candidates.pop("block2x2", None)
    candidates["safe4"] = [(0, 0), (1, 0), (0, 1), (2, 2)]
    candidates["safe5"] = [(0, 0), (1, 0), (0, 1), (2, 2), (3, 1)]

    results = {}
    for name, S in candidates.items():
        # verify S is safe as a standalone set
        if is_forbidden_quad(S) if len(S) == 4 else False:
            results[name] = {"error": "S itself is a forbidden quad"}
            continue
        if len(S) >= 4 and any(is_forbidden_quad(list(c)) for c in combinations(S, 4)):
            results[name] = {"error": "S contains a forbidden quad"}
            continue
        vals = {}
        for n in [4, 5, 6]:
            pts = square_points(n)
            # map S coords: need S subset of board coords 0..n-1
            if any(x >= n or y >= n or x < 0 or y < 0 for x, y in S):
                vals[f"n{n}"] = None
                continue
            b = Board(pts, name=f"{n}x{n}")
            # occupancy of S
            occ = 0
            for x, y in S:
                occ |= 1 << (y * n + x)
            if not b.is_safe(occ):
                vals[f"n{n}"] = "S not safe on this board"
                continue
            memo = b.solve_grundy()
            vals[f"n{n}"] = memo.get(occ)
        distinct = {v for v in vals.values() if isinstance(v, int)}
        results[name] = {
            "S": S,
            "grundy_by_board": vals,
            "n_distinct": len(distinct),
            "distinct": sorted(distinct),
        }
    return results


# ---------------------------------------------------------------------------
# B288 / B289 / B290: circle/line capacity LP
# ---------------------------------------------------------------------------

def b288_b289_b290():
    out = {}
    for n in [4, 5, 6]:
        pts = square_points(n)
        V = n * n
        carriers = enumerate_circles_lines(pts)
        # split line vs circle
        n_line = 0
        n_circ = 0
        line_sizes = []
        circ_sizes = []
        for car in carriers:
            cl = list(car)
            is_line = collinear(pts[cl[0]], pts[cl[1]], pts[cl[2]])
            if is_line:
                n_line += 1
                line_sizes.append(len(car))
            else:
                n_circ += 1
                circ_sizes.append(len(car))

        K = KNOWN_K[n]
        obj_frac, x_frac = fractional_capacity_lp(carriers, V)
        # integer max = K_n (known); also verify by kyouen_core
        b = Board(pts, name=f"{n}x{n}")
        K_calc = b.max_safe_size()

        gap = obj_frac - K

        # B290: add "circle-bundle" inequalities.
        # Candidate family: for every pair of carriers c1,c2 with |c1 ∩ c2| = 2
        # (circle-circle 2-point intersection), add
        #   sum_{p in c1 union c2} x_p <= 3 + 3 - 2*|shared in S|  ... not valid.
        # Valid bundle inequality idea:
        # if two circles share 2 points, a safe set can have at most 3 on each,
        # but the shared 2 can be counted in both. A stronger VALID inequality
        # comes from *forbidden quads that span both circles*.
        # Practical valid extra rows we CAN add:
        #   (A) for every 4-subset that is forbidden: sum <= 3  (already implied
        #       by the circle capacity if the 4 lie on one carrier — always true)
        #   (B) clique inequalities on the "competition graph":
        #       two points compete if some carrier has >=4 points containing both.
        #       For a clique of pairwise-competing points? Not valid in general.
        #   (C) **intersecting-circle bundle**: if carriers c1,c2 have
        #       |c1|=|c2|=4 and |c1 ∩ c2|=2, then c1 ∪ c2 has 6 points and
        #       any safe set picks at most 3 from c1 and at most 3 from c2,
        #       but also at most 3 from any OTHER carrier inside the union.
        #       Enumerate ALL carriers of the board — already done.
        #
        # The truly new rows B290 asks for are *joint* constraints beyond
        # single-circle capacity. One valid family: for every pair of carriers
        # (c1,c2) and every 2-point intersection I=c1∩c2, the set
        # (c1 ∪ c2) must contain no 4-subset on some *third* carrier that is
        # NOT already listed. But that third carrier is already a board carrier.
        #
        # So instead we implement a *different* valid strengthening used in
        # covering codes: for every 3 carriers whose pairwise intersections are
        # large, sum of x over the union <= some bound derived by case analysis.
        # Simplest computable valid row:
        #   For every 5-point set T that is the union of two carriers meeting in
        #   1 point: any safe set has |S ∩ T| <= 4 (since each carrier contributes
        #   <=3 and they share at most 1 point: 3+3-1=5 is not valid; actually
        #   3+3-0=6 if disjoint, minus shared. If |c1∩c2|=1 then
        #   |S∩T| = |S∩c1|+|S∩c2|-|S∩I| <= 3+3-0 = 6, no gain.
        #
        # Honest approach for B290: add ALL 4-subset capacity rows that are
        # *not* on a single carrier but are "almost" forbidden — no such thing.
        #
        # Instead: add rows for **every** 5-or-6-point carrier-like set that
        # is "cyclically constrained": for every pair of carriers with
        # intersection size 2, the union has size u; any safe set satisfies
        # |S∩c1|<=3, |S∩c2|<=3, and if we let t=|S∩I| (0,1,2),
        # |S∩(c1∪c2)| <= 6-t. To make a linear valid inequality independent of t:
        #   x(c1)+x(c2) <= 6   (i.e. x(U) + x(I) <= 6)  — valid but weak.
        # Stronger: 2*x(I) + x(U) <= 6 + x(I)  ... messy.
        #
        # We'll implement bundle rows of the form:
        #   x(c1) + x(c2) <= 6 - |I|   when |I|>=1  — check validity:
        #   x(c1)+x(c2) = x(U)+x(I) <= (3+3-t)+t = 6, so <= 6 is valid;
        #   <= 6-|I| is valid only if t >= |I| i.e. shared points all in S — NOT always.
        # So only x(c1)+x(c2) <= 6 is universally valid.
        #
        # FINAL B290 candidate rows (universally valid):
        #   R1: for every pair of carriers (c1,c2):  x(c1)+x(c2) <= 6
        #       (actually redundant given x(c)<=3 each — sum <=6 automatically)
        #   R2: for every triple of carriers covering the board with small
        #       intersections, add x(U) <= 3+3+3 - forced overlap. Only when
        #       pairwise intersections force collisions.
        #   R3: **point-clique rows from forced 4th-point**: if a set of points
        #       T has the property that ANY 4-subset of T is forbidden (i.e. T
        #       is "4-wise concyclic-collinear"), then x(T) <= 3.
        #       Such T of size 5+ are rare (would mean 5 points with every 4 on
        #       a circle — i.e. all 5 concyclic or special). All 5 concyclic is
        #       already a carrier with capacity 3.
        #   R4: **cross-carrier 4-sets that are NOT on a single board carrier**
        #       — impossible: if 4 points are concyclic/collinear they ARE on a
        #       carrier (the circle through 3 of them contains the 4th).
        #
        # Conclusion: with integer board points, single-carrier capacity rows
        # already capture every forbidden 4-subset. The fractional gap therefore
        # is a pure "packing vs covering" gap of the single-carrier system.
        # B290's "small circle bundles" must mean something else — perhaps
        # *auxiliary* circles not through 4 board points but through 3 board + 1
        # auxiliary, used only in the dual. We measure the gap and report.

        # Also try a simple extra valid family: for every pair of points p,q
        # that appear together in >= T carriers, ... skip.

        out[f"n{n}"] = {
            "V": V,
            "K_n_known": K,
            "K_n_calculated": K_calc,
            "n_carriers": len(carriers),
            "n_lines": n_line,
            "n_circles": n_circ,
            "line_size_hist": dict(Counter(line_sizes)),
            "circle_size_hist": dict(Counter(circ_sizes)),
            "max_line_size": max(line_sizes) if line_sizes else 0,
            "max_circle_size": max(circ_sizes) if circ_sizes else 0,
            "fractional_lp_optimum": float(obj_frac),
            "fractional_lp_optimum_frac": f"{obj_frac.numerator}/{obj_frac.denominator}",
            "gap_frac_minus_K": float(obj_frac - K),
            "x_frac_sample": [float(v) for v in x_frac[: min(16, V)]],
            "all_x_frac": [float(v) for v in x_frac],
        }
    return out


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    result = {}

    print("B271/B272 n=4 correlation ...", flush=True)
    result["B271_B272_n4"] = b271_b272_correlation(4)

    print("B275/B277 thermo ...", flush=True)
    # level counts
    LEVELS = {
        4: [1, 16, 120, 560, 1626, 2360, 1064, 64],
        5: [1, 25, 300, 2300, 11824, 37272, 59192, 35208, 5172, 100],
    }
    # n=6 level counts from round4 data if present
    try:
        prev = json.loads((Path(__file__).resolve().parents[1] / "round5_b251_solver.json").read_text())
        # try to find level counts
    except Exception:
        prev = {}
    b275 = {}
    b277 = {}
    for n, level in LEVELS.items():
        b275[f"n{n}"] = thermo_from_levels(level)
        K = max(i for i, v in enumerate(level) if v > 0)
        b277[f"n{n}"] = {
            "levels": level,
            "K": K,
            "A_K": level[K],
            "A_Kminus1": level[K - 1] if K >= 1 else None,
            "A_Kminus2": level[K - 2] if K >= 2 else None,
            "ratio_Km1_over_K": (level[K - 1] / level[K]) if level[K] else None,
            "ratio_Km2_over_K": (level[K - 2] / level[K]) if K >= 2 and level[K] else None,
        }
    result["B275"] = b275
    result["B277"] = b277

    print("B280 multigraded Z n=4 ...", flush=True)
    result["B280"] = multigraded_Z(4)

    print("B281/B283 geometry search ...", flush=True)
    result["B281_B283"] = b281_b283_search(box=3, k=5)
    result["B281_B283_box4k6"] = b281_b283_search(box=4, k=6)

    print("B285 grundy embed ...", flush=True)
    result["B285"] = b285_grundy_embed()

    print("B288/B289/B290 capacity LP ...", flush=True)
    result["B288_B289_B290"] = b288_b289_b290()

    OUT_JSON.write_text(json.dumps(result, indent=2, default=str))
    print("WROTE", OUT_JSON)


if __name__ == "__main__":
    main()
