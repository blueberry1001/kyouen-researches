"""Exact finite checks for the uniform safety-correction proof (not asymptotic evidence).

Run with Python 3.11+; only the standard library is needed.
All assertions use integers or fractions. Floating values are descriptive only.
"""
from collections import Counter
from fractions import Fraction as F
from functools import cache
from itertools import combinations
from math import comb, gcd
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research/verification"


@cache
def mass(m, k, p):
    return F(0) if k < 0 or k > m else comb(m, k) * p**k * (1-p)**(m-k)


@cache
def tail(m, k, p):
    return sum((mass(m, j, p) for j in range(max(k, 0), m+1)), F(0))


@cache
def covariance(m, l, t, p):
    # Direct conditioning on the number of selected shared vertices.
    joint = sum((mass(t, j, p)*tail(m-t, 4-j, p)*tail(l-t, 4-j, p)
                 for j in range(t+1)), F(0))
    return joint-tail(m, 4, p)*tail(l, 4, p)


def covariance_formula(m, l, t, p):
    am, al = mass(m-1, 3, p), mass(l-1, 3, p)
    bm = mass(m-2, 2, p)-mass(m-2, 3, p)
    bl = mass(l-2, 2, p)-mass(l-2, 3, p)
    return t*p*(1-p)*am*al + (t == 2)*(p*(1-p))**2*bm*bl


def analytic_checks():
    cases = bounded = tails = 0
    for p in (F(1, 2), F(1, 5), F(1, 41)):
        for m in range(4, 21):
            for l in range(4, 21):
                for t in range(3):
                    cov = covariance(m, l, t, p)
                    assert cov == covariance_formula(m, l, t, p)
                    assert cov >= 0
                    cases += 1
                    if max(m, l)*p <= 1:
                        bound = t*comb(m-1, 3)*comb(l-1, 3)*p**7
                        bound += (t == 2)*4*comb(m-2, 2)*comb(l-2, 2)*p**6
                        assert cov <= bound
                        bounded += 1
    for p in (F(1, 2), F(1, 7), F(1, 101)):
        for m in range(4, 61):
            expansion = sum(((-1)**(r-4)*comb(r-1, 3)*comb(m, r)*p**r
                             for r in range(4, m+1)), F(0))
            assert expansion == tail(m, 4, p)
            if m*p <= 1:
                rest = tail(m, 4, p)-comb(m, 4)*p**4+4*comb(m, 5)*p**5
                assert abs(rest) <= 20*comb(m, 6)*p**6
                tails += 1
    return {"covariance_identities": cases, "covariance_bounds": bounded,
            "tail_polynomial_identities": 3*57, "tail_remainder_bounds": tails}


def primitive(coeffs):
    g = gcd(*coeffs)
    out = tuple(c//g for c in coeffs)
    return out if next(c for c in out if c) > 0 else tuple(-c for c in out)


def curve_key(a, b, c):
    x, y = a
    ux, uy = b[0]-x, b[1]-y
    vx, vy = c[0]-x, c[1]-y
    A = ux*vy-uy*vx
    if A == 0:
        return primitive((0, uy, -ux, ux*y-uy*x))
    u2, v2 = ux*ux+uy*uy, vx*vx+vy*vy
    D, E = u2*vy-v2*uy, ux*v2-vx*u2
    return primitive((A, -2*A*x-D, -2*A*y-E, A*(x*x+y*y)+D*x+E*y))


def forbidden(quad):
    # Independent determinant criterion, including collinear quadruples.
    x, y = quad[0]
    a, b, c = [(u-x, v-y, (u-x)**2+(v-y)**2) for u, v in quad[1:]]
    return (a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])
            +a[2]*(b[0]*c[1]-b[1]*c[0])) == 0


def curves(n):
    pts = [(x, y) for x in range(n) for y in range(n)]
    keys = {curve_key(*q) for q in combinations(pts, 3)}
    result = []
    for A, B, C, D in sorted(keys):
        mask = sum(1 << i for i, (x, y) in enumerate(pts)
                   if A*(x*x+y*y)+B*x+C*y+D == 0)
        if mask.bit_count() >= 4:
            result.append((mask, A == 0))
    return pts, result


def frac(q):
    return {"numerator": q.numerator, "denominator": q.denominator}


def exact_small_board(n):
    pts, rows = curves(n)
    masks = [mask for mask, _ in rows]
    sizes = [mask.bit_count() for mask in masks]
    edges = []
    for quad in combinations(range(n*n), 4):
        mask = sum(1 << i for i in quad)
        contain = sum((mask & C) == mask for C in masks)
        is_edge = forbidden([pts[i] for i in quad])
        assert contain == int(is_edge)
        if is_edge:
            edges.append(mask)
    overlaps = Counter()
    for i, j in combinations(range(len(masks)), 2):
        t = (masks[i] & masks[j]).bit_count()
        assert t <= 2
        overlaps[tuple(sorted((sizes[i], sizes[j])))+(t,)] += 1
    g = {r: sum(comb(m, r) for m in sizes) for r in (4, 5, 6)}
    assert g[4] == len(edges)
    d5 = sum(comb(mask.bit_count(), 5) for mask, line in rows if line)
    assert d5 == collinear_sets(n, 5)
    five_edges = []
    for C in masks:
        vertices = [i for i in range(n*n) if C & (1 << i)]
        five_edges.extend(sum(1 << i for i in q) for q in combinations(vertices, 5))
    assert len(five_edges) == len(set(five_edges)) == g[5]
    five_pairs = Counter((A & B).bit_count() for A, B in combinations(five_edges, 2))
    assert all(j <= 4 for j in five_pairs)
    result = {"n": n, "curve_count": len(rows), "size_histogram": dict(Counter(sizes)),
              "G": g, "collinear_five_sets": d5,
              "forbidden_edges_independently_checked": len(edges),
              "five_edge_pair_intersections": dict(sorted(five_pairs.items())),
              "curve_pair_histogram": [[*key, value] for key, value in sorted(overlaps.items())]}
    if n > 4:
        return result
    # Entire probability space. No approximate sampling and no asymptotic fitting.
    hist = Counter()
    five_hist = Counter()
    safe_by_size = Counter()
    for S in range(1 << (n*n)):
        occ = [(S & C).bit_count() for C in masks]
        w = sum(m >= 4 for m in occ)
        z = sum(comb(m, 4) for m in occ)
        safe = not any((S & E) == E for E in edges)
        assert (w == 0) == (z == 0) == safe
        k = S.bit_count()
        hist[(k, w)] += 1
        five_hist[(k, sum(comb(m, 5) for m in occ))] += 1
        if safe:
            safe_by_size[k] += 1
    checks = []
    for p in (F(1, 7), F(1, 11)):
        weights = [p**k*(1-p)**(n*n-k) for k in range(n*n+1)]
        EW = sum((count*w*weights[k] for (k, w), count in hist.items()), F(0))
        EW2 = sum((count*w*w*weights[k] for (k, w), count in hist.items()), F(0))
        variance = EW2-EW*EW
        Lambda = sum((tail(m, 4, p) for m in sizes), F(0))
        diagonal = sum((tail(m, 4, p)*(1-tail(m, 4, p)) for m in sizes), F(0))
        offdiag = 2*sum((count*covariance_formula(m, l, t, p)
                        for (m, l, t), count in overlaps.items()), F(0))
        assert EW == Lambda and variance == diagonal+offdiag
        safe = sum((count*weights[k] for k, count in safe_by_size.items()), F(0))
        error_sum = sum((tail(m, 4, p)**2 for m in sizes), F(0))+offdiag
        assert error_sum == variance-Lambda+2*sum((tail(m, 4, p)**2 for m in sizes), F(0))
        EY = sum((count*y*weights[k] for (k, y), count in five_hist.items()), F(0))
        EYchoose2 = sum((count*comb(y, 2)*weights[k] for (k, y), count in five_hist.items()), F(0))
        bundle = sum((count*weights[k] for (k, y), count in five_hist.items() if y), F(0))
        assert EY == g[5]*p**5
        assert EYchoose2 == sum((count*p**(10-j) for j, count in five_pairs.items()), F(0))
        assert EY-EYchoose2 <= bundle <= EY
        if max(sizes)*p <= 1:
            assert abs(Lambda-g[4]*p**4+4*g[5]*p**5) <= 20*g[6]*p**6
        checks.append({"p": frac(p), "Lambda": frac(Lambda), "variance": frac(variance),
                       "sum_q_squared_plus_ordered_covariances": frac(error_sum),
                       "safe_probability": frac(safe), "moment_identity_pass": True,
                       "five_set_mean": frac(EY), "five_set_second_binomial_moment": frac(EYchoose2),
                       "bundle_probability": frac(bundle), "bonferroni_pass": True})
    for k in range(n*n+1):
        def supersets(s):
            return comb(n*n-s, k-s) if s <= k and s <= n*n else 0
        first = sum(count*y for (ks, y), count in five_hist.items() if ks == k)
        second = sum(count*comb(y, 2) for (ks, y), count in five_hist.items() if ks == k)
        assert first == g[5]*supersets(5)
        assert second == sum(count*supersets(10-j) for j, count in five_pairs.items())
    result.update({"all_subsets_checked": 1 << (n*n), "exact_probability_checks": checks,
                   "fixed_k_five_set_moments_all_pass": True,
                   "safe_sets_by_size": {k: safe_by_size[k] for k in range(n*n+1)}})
    return result


def collinear_sets(n, r):
    """Count each set once by its two extreme points and primitive direction."""
    total = 0
    max_height = (n-1)//(r-1)
    for a in range(max_height+1):
        for b in range(max_height+1):
            if gcd(a, b) != 1:
                continue
            mult = 2 if a and b else 1
            for gap in range(r-1, (n-1)//max(a, b)+1):
                total += mult*comb(gap-1, r-2)*(n-gap*a)*(n-gap*b)
    return total


def main():
    identities = analytic_checks()
    print("rational analytic identities passed", identities, flush=True)
    boards = []
    for n in (3, 4, 5):
        boards.append(exact_small_board(n))
        print("exact board check passed", n, flush=True)
    line_counts = []
    for n in (8, 16, 32, 64, 128, 256, 512):
        d5 = collinear_sets(n, 5)
        line_counts.append({"n": n, "D5": d5, "D5_over_n6": frac(F(d5, n**6))})
    result = {"analytic_identities": identities, "small_boards": boards,
              "collinear_five_set_counts": line_counts,
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "scope": "Exact finite cross-checks only. General proofs and external inputs are in round14-safety-correction.md."}
    output = OUT / "round14_safety_correction.json"
    output.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print("saved", output, flush=True)


if __name__ == "__main__":
    main()
