"""Exact checks for B477's standard-chord formula, with no floating arithmetic."""
from collections import Counter, defaultdict
from fractions import Fraction
from itertools import combinations
from math import comb, gcd, isqrt, lcm
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research/verification"


def det(a, b):
    return a[0]*b[1]-a[1]*b[0]


def sub(a, b):
    return a[0]-b[0], a[1]-b[1]


def dot(a, b):
    return a[0]*b[0]+a[1]*b[1]


def parameter(u, g, w):
    h = det(u, w)
    if not h:
        return None
    ell = dot(w, w)-g*dot(u, w)
    divisor = gcd(ell, h)
    A, B = ell//divisor, h//divisor
    return (A, B) if B > 0 else (-A, -B)


def coefficients(a, u, g, A, B):
    D, E = B*g*u[0]-A*u[1], B*g*u[1]+A*u[0]
    assert gcd(B, D, E) == 1
    q = 2*B//gcd(2*B, D, E)
    assert q == (B if B % 2 and D % 2 == 0 and E % 2 == 0 else 2*B)
    key = (B, -D-2*B*a[0], -E-2*B*a[1], B*dot(a, a)+D*a[0]+E*a[1])
    return D, E, q, key


def independent_circle(a, b, c):
    """Three-point determinant equations, without primitive chord parameters."""
    u, v = sub(b, a), sub(c, a)
    B = det(u, v)
    D = dot(u, u)*v[1]-dot(v, v)*u[1]
    E = u[0]*dot(v, v)-v[0]*dot(u, u)
    center = (Fraction(D, 2*B)+a[0], Fraction(E, 2*B)+a[1])
    key = (B, -D-2*B*a[0], -E-2*B*a[1], B*dot(a, a)+D*a[0]+E*a[1])
    divisor = gcd(*key)
    if B < 0:
        divisor = -divisor
    return tuple(t//divisor for t in key), lcm(*(t.denominator for t in center))


def concyclic_quad(quad):
    a, b, c = [sub(p, quad[0]) for p in quad[1:]]
    if not det(a, b) and not det(a, c):
        return False
    return det(b, c)*dot(a, a)-det(a, c)*dot(b, b)+det(a, b)*dot(c, c) == 0


def trapezoid_check(quad, n):
    """Return the number of parallel-edge choices; check each allowed axis."""
    choices = [((0, 1), (2, 3)), ((0, 2), (1, 3)), ((0, 3), (1, 2))]
    found = 0
    for ij, kl in choices:
        a, b = [quad[i] for i in ij]
        c, d = [quad[i] for i in kl]
        first, second = sub(b, a), sub(d, c)
        if det(first, second):
            continue
        g = gcd(*first)
        u = first[0]//g, first[1]//g
        if dot(first, second) < 0:
            c, d = d, c
            second = sub(d, c)
        h = gcd(*second)
        assert second == (h*u[0], h*u[1])
        delta = (c[0]+d[0]-a[0]-b[0], c[1]+d[1]-a[1]-b[1])
        assert dot(delta, u) == 0
        if u[0]:
            assert delta[1] % u[0] == 0
            t = delta[1]//u[0]
        else:
            assert delta[0] % u[1] == 0
            t = -delta[0]//u[1]
        assert t and delta == (-t*u[1], t*u[0])
        assert (h*h-g*g+t*t) % 2 == 0
        tau = Fraction(h*h-g*g+t*t, 2*t)
        equation, q = independent_circle(a, b, c)
        assert equation[0] == tau.denominator
        assert t % equation[0] == 0
        H = max(map(abs, u))
        assert q <= 2*abs(t) and q*H <= 4*(n-1)
        found += 1
    return found


def sharp_family():
    examples = []
    sharp_cases = 0
    for n in range(3, 1001):
        quad = [(n-2, 0), (n-1, 1), (0, n-3), (2, n-1)]
        assert len(set(quad)) == 4 and concyclic_quad(quad)
        assert min(x for x, y in quad) == min(y for x, y in quad) == 0
        assert max(x for x, y in quad) == max(y for x, y in quad) == n-1
        assert trapezoid_check(quad, n)
        equation, q = independent_circle(*quad[:3])
        t = 2*n-5
        assert q == 2*t//gcd(t, 3)
        if n >= 5 and n % 3 != 1:
            sharp_cases += 1
            assert q == 4*n-10
        if n in (3, 4, 5, 6, 8, 20, 101, 500, 998, 999, 1000):
            examples.append({"n": n, "points": quad, "q": q, "primitive_equation": equation})
    return {"n_min": 3, "n_max": 1000, "cases": 998,
            "q_equals_4n_minus_10_cases_n_ge5": sharp_cases, "examples": examples}


def quadratic_denominator_family():
    examples = []
    for j in range(101):
        t = 30*j+10
        n = 6*t+8
        quad = [(3*t+3, 1), (0, 3*t+6), (4*t+3, 0), (t-3, 6*t+7)]
        assert len(set(quad)) == 4 and concyclic_quad(quad)
        assert all(0 <= x < n and 0 <= y < n for x, y in quad)
        assert trapezoid_check(quad, n) == 0
        B = 3*t*t+2*t-3
        D = 3*t**3+23*t*t+51*t+39
        E = 21*t**3+51*t*t+37*t+3
        assert D-(t+7)*B == 20*(2*t+3)
        assert 3*E-(21*t+37)*B == 20*(5*t+6)
        assert gcd(B, D, E) == gcd(B, 60) == 1
        assert D % 2 == E % 2 == 1
        equation, q = independent_circle(*quad[:3])
        assert equation[0] == B and q == 2*B
        assert q > 4*(n-1)
        assert q <= 2*(n-1)**2
        if j in (0, 1, 2, 10, 50, 100):
            examples.append({"t": t, "n": n, "points": quad, "q": q,
                             "primitive_equation": equation,
                             "q_over_n_squared": {"numerator": q, "denominator": n*n}})
    return {"parameter_t": "30*j+10", "j_min": 0, "j_max": 100,
            "cases": 101, "all_nontrapezoid_and_exact_denominator_checks_pass": True,
            "examples": examples}


def board(n, certificates):
    pts = [(x, y) for x in range(n) for y in range(n)]
    N = len(pts)
    count = groups_count = triples = 0
    histogram = Counter()
    quads = set()
    circle_points = defaultdict(set)
    candidates = {}
    for i, a in enumerate(pts):
        for j in range(i+1, N):
            b = pts[j]
            d = sub(b, a)
            g = gcd(*d)
            u = d[0]//g, d[1]//g
            groups = defaultdict(list)
            for k in range(j+1, N):
                triples += 1
                w = sub(pts[k], a)
                param = parameter(u, g, w)
                if param is None:
                    continue
                A, B = param
                assert det(u, w) % B == 0
                assert g*B <= abs(det(d, w)) <= (n-1)**2
                groups[param].append(k)
            for (A, B), ks in groups.items():
                if len(ks) < 2:
                    continue
                D, E, q, key = coefficients(a, u, g, A, B)
                amount = comb(len(ks), 2)
                groups_count += 1
                count += amount
                histogram[q] += amount
                if n <= 8:
                    for k, ell in combinations(ks, 2):
                        quad = (i, j, k, ell)
                        assert quad not in quads
                        quads.add(quad)
                    circle_points[key].update((i, j, *ks))
                # One certificate per primitive leading coefficient on each board.
                if B not in candidates:
                    candidates[B] = {"n": n, "a": a, "b": b, "c": pts[ks[0]],
                                     "u": u, "g": g, "A": A, "B": B, "D": D, "E": E,
                                     "q": q, "global_primitive_equation": key}
    assert triples == comb(N, 3)
    result = {"n": n, "concyclic_quads": count, "contributing_chord_parameter_groups": groups_count,
              "triple_visits": triples, "quad_count_by_center_denominator": dict(sorted(histogram.items()))}
    if n <= 8:
        direct = {q for q in combinations(range(N), 4) if concyclic_quad([pts[i] for i in q])}
        assert direct == quads
        assert count == len(direct) == sum(comb(len(v), 4) for v in circle_points.values())
        for key, ids in circle_points.items():
            actual = {i for i, (x, y) in enumerate(pts)
                      if key[0]*(x*x+y*y)+key[1]*x+key[2]*y+key[3] == 0}
            assert ids == actual
        trap_count = trap_base_choices = 0
        for q in direct:
            choices = trapezoid_check([pts[i] for i in q], n)
            trap_count += choices > 0
            trap_base_choices += choices
        result.update({"independent_four_point_subsets_checked": comb(N, 4),
                       "quad_sets_equal": True, "circle_count": len(circle_points),
                       "circle_multiplicity_sum_equal": True,
                       "isosceles_trapezoids": trap_count,
                       "parallel_base_choices_checked": trap_base_choices,
                       "trapezoid_denominator_bounds_all_pass": True})
    certificates.extend(candidates.values())
    return result


def check_certificate(row):
    a, b, c = row["a"], row["b"], row["c"]
    D, E, B, A, g, u = (row[k] for k in ("D", "E", "B", "A", "g", "u"))
    independent, independent_q = independent_circle(a, b, c)
    assert independent == row["global_primitive_equation"]
    assert independent_q == row["q"]
    M = D*D+E*E
    assert M == dot(u, u)*((B*g)**2+A*A)
    radius = isqrt(M)
    norm_points = set()
    representations = 0
    for X in range(-radius, radius+1):
        Y = isqrt(M-X*X)
        if X*X+Y*Y != M:
            continue
        for signed_y in {Y, -Y}:
            representations += 1
            if (X+D) % (2*B) == 0 and (signed_y+E) % (2*B) == 0:
                norm_points.add(((X+D)//(2*B), (signed_y+E)//(2*B)))
    equation_points = set()
    for x in range((D-radius)//(2*B)-1, (D+radius)//(2*B)+2):
        delta = E*E-4*B*(B*x*x-D*x)
        if delta < 0:
            continue
        root = isqrt(delta)
        if root*root == delta:
            for signed_root in {root, -root}:
                if (E+signed_root) % (2*B) == 0:
                    equation_points.add((x, (E+signed_root)//(2*B)))
    assert norm_points == equation_points
    assert len(norm_points) >= 4
    chord_checks = 0
    # Different chords can have different A but must give the same B.
    for v, w in combinations(sorted(norm_points), 2):
        dv = sub(w, v)
        chord_g = gcd(*dv)
        chord_u = dv[0]//chord_g, dv[1]//chord_g
        other = next(z for z in norm_points if det(dv, sub(z, v)))
        Ac, Bc = parameter(chord_u, chord_g, sub(other, v))
        assert Bc == B
        _, _, qc, keyc = coefficients((v[0]+a[0], v[1]+a[1]), chord_u, chord_g, Ac, Bc)
        assert qc == row["q"] and keyc == row["global_primitive_equation"]
        assert all(det(chord_u, sub(z, v)) % B == 0 for z in norm_points)
        chord_checks += 1
    row.update({"norm": M, "all_norm_representation_count": representations,
                "complete_relative_integer_points": sorted(norm_points),
                "all_complete_circle_chords_checked": chord_checks,
                "independent_center_and_equation_pass": True, "norm_and_quadratic_solutions_equal": True})


def main():
    certificates = []
    boards = []
    for n in range(2, 13):
        boards.append(board(n, certificates))
        print("n", n, "C_n", boards[-1]["concyclic_quads"], flush=True)
    for row in certificates:
        check_certificate(row)
    source = OUT / "round3_b451_census.json"
    census = json.loads(source.read_text(encoding="utf-8"))["boards"]
    comparisons = []
    for row in boards:
        key = str(row["n"])
        if key in census:
            expected = census[key]["n_concyclic_quads"]
            comparisons.append({"n": row["n"], "census_count": expected,
                                "new_count": row["concyclic_quads"], "equal": expected == row["concyclic_quads"]})
    assert all(row["equal"] for row in comparisons)
    result = {"boards": boards, "circle_certificates": certificates,
              "certificate_count": len(certificates),
              "complete_chords_checked": sum(r["all_complete_circle_chords_checked"] for r in certificates),
              "sharp_trapezoid_family": sharp_family(),
              "quadratic_denominator_family": quadratic_denominator_family(),
              "independent_census": {"file": source.name, "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                                     "comparisons": comparisons},
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "scope": "Exact finite implementation checks. The general proof is in round15-standard-chord.md."}
    output = OUT / "round15_standard_chord.json"
    output.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print("saved", output, "certificates", len(certificates), flush=True)


if __name__ == "__main__":
    main()
