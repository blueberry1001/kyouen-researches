"""Exact certificates for first-appearance counterexamples and inert dilations.

Only integer arithmetic is used. All complete circle points are enumerated by
two methods. The unbounded statements are proved in the companion markdown.
"""
from collections import Counter
from itertools import combinations
from math import gcd, isqrt, lcm
from pathlib import Path
import hashlib
import json

OUT = Path(__file__).resolve().parents[1]


def span(points):
    xs, ys = zip(*points)
    return max(max(xs)-min(xs), max(ys)-min(ys))


def primitive(coefficients):
    g = gcd(*coefficients)
    out = tuple(x//g for x in coefficients)
    return out if next(x for x in out if x) > 0 else tuple(-x for x in out)


def complete_circle(q, a, b, M, scale=1):
    """Circle (q*x+a*scale)^2+(q*y+b*scale)^2=M*scale^2."""
    norm = M*scale*scale
    r = isqrt(norm)
    by_norm = set()
    for U in range(-r, r+1):
        if (U-a*scale) % q:
            continue
        V = isqrt(norm-U*U)
        if U*U+V*V != norm:
            continue
        for signed_V in {V, -V}:
            if (signed_V-b*scale) % q == 0:
                by_norm.add(((U-a*scale)//q, (signed_V-b*scale)//q))
    coefficients = primitive((q*q, 2*q*a*scale, 2*q*b*scale, (a*a+b*b-M)*scale*scale))
    A, B, C, D = coefficients
    radius_numerator = isqrt(B*B+C*C-4*A*D)
    by_roots = set()
    for x in range((-B-radius_numerator)//(2*A)-1, (-B+radius_numerator)//(2*A)+2):
        disc = C*C-4*A*(A*x*x+B*x+D)
        if disc < 0:
            continue
        root = isqrt(disc)
        if root*root == disc:
            for signed in {root, -root}:
                if (-C+signed) % (2*A) == 0:
                    by_roots.add((x, (-C+signed)//(2*A)))
    assert by_roots == by_norm
    actual_q = 2*A//gcd(2*A, B, C)
    return sorted(by_norm), coefficients, actual_q


def profile(points):
    out = {}
    for j in range(1, len(points)+1):
        histogram = Counter(span(T) for T in combinations(points, j))
        out[j] = {"first_board_side_at_least": min(histogram)+1,
                  "subset_span_histogram": dict(sorted(histogram.items()))}
    return out


def exact_window(points, count, side):
    d = side-1
    # Entry/exit positions enumerate all distinct memberships of integer windows.
    xs = sorted({t for x, y in points for t in (x-d, x+1)})
    ys = sorted({t for x, y in points for t in (y-d, y+1)})
    for a in xs:
        for b in ys:
            inside = [p for p in points if a <= p[0] <= a+d and b <= p[1] <= b+d]
            if len(inside) == count:
                return {"lower_left": [a, b], "side": side, "points": inside}
    raise AssertionError("No exact window found")


def circle_pair():
    result = []
    for name, a, b, M, expected in [
        ("C", 1, 2, 725, [(-9,-3),(-8,4),(-5,7),(2,8),(3,-9),(8,-4)]),
        ("D", 1, 1, 845, [(-10,-1),(-9,4),(-1,-10),(4,-9),(6,7),(7,6)]),
    ]:
        points, equation, q = complete_circle(3, a, b, M)
        assert points == expected
        assert q == equation[0] == 3 and len(points) == 6
        assert span(points) == 17
        prof = profile(points)
        expected_first = 12 if name == "C" else 15
        assert prof[4]["first_board_side_at_least"] == expected_first
        window = exact_window(points, 4, expected_first)
        scales = []
        for e in range(5):
            L = 7**e
            scaled, eq, qs = complete_circle(3, a, b, M, L)
            assert scaled == [(L*x, L*y) for x, y in points]
            assert len(scaled) == 6 and qs == eq[0] == 3
            scaled_prof = profile(scaled)
            for j in range(1, 7):
                assert scaled_prof[j]["first_board_side_at_least"] == L*(prof[j]["first_board_side_at_least"]-1)+1
            lower = [L*x for x in window["lower_left"]]
            width = L*(window["side"]-1)
            included = [p for p in scaled if lower[0] <= p[0] <= lower[0]+width and lower[1] <= p[1] <= lower[1]+width]
            assert len(included) == 4
            scales.append({"exponent": e, "scale": L, "complete_count": 6, "center_denominator": qs,
                           "primitive_equation": eq, "full_span": span(scaled),
                           "first_four_side": scaled_prof[4]["first_board_side_at_least"],
                           "exact_four_window": {"lower_left": lower, "side": width+1, "points": included}})
        # Conditions of the dilation theorem matter: neither of these scales is admissible.
        excluded = []
        for p in (3, 5):
            extra, eq, qs = complete_circle(3, a, b, M, p)
            assert len(extra) > 6
            excluded.append({"scale": p, "complete_count": len(extra), "center_denominator": qs,
                             "reason_excluded": "divides q" if p == 3 else "prime is 1 mod 4"})
        result.append({"name": name, "q_a_b_M": [3, a, b, M], "complete_points": points,
                       "primitive_equation": equation, "profile": prof, "exact_four_window": window,
                       "inert_scales": scales, "excluded_scale_examples": excluded})
    for c, d in zip(result[0]["inert_scales"], result[1]["inert_scales"]):
        assert d["first_four_side"]-c["first_four_side"] == 3*c["scale"]
        assert d["full_span"] == c["full_span"]
    return result


def forbidden(quad):
    x, y = quad[0]
    a, b, c = [(u-x, v-y, (u-x)**2+(v-y)**2) for u, v in quad[1:]]
    return (a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])
            +a[2]*(b[0]*c[1]-b[1]*c[0])) == 0


def safe(points):
    return not any(forbidden(q) for q in combinations(points, 4))


def is_legal(points, p):
    return p not in points and not any(forbidden((*t, p)) for t in combinations(points, 3))


def triple_curves(points):
    lines, circles = set(), set()
    for a, b, c in combinations(points, 3):
        x, y = a
        ux, uy = b[0]-x, b[1]-y
        vx, vy = c[0]-x, c[1]-y
        A = ux*vy-uy*vx
        if A == 0:
            lines.add(primitive((uy, -ux, ux*y-uy*x)))
            continue
        D = (ux*ux+uy*uy)*vy-(vx*vx+vy*vy)*uy
        E = ux*(vx*vx+vy*vy)-vx*(ux*ux+uy*uy)
        circles.add(primitive((A, -2*A*x-D, -2*A*y-E, A*(x*x+y*y)+D*x+E*y)))
    qs = sorted({2*A//gcd(2*A, B, C) for A, B, C, D in circles})
    return lines, circles, qs


def outer_shell(points, r):
    x0, x1 = min(x for x,y in points)-r, max(x for x,y in points)+r
    y0, y1 = min(y for x,y in points)-r, max(y for x,y in points)+r
    out = {(x, y) for x in range(x0, x1+1) for y in (y0, y1)}
    out.update((x, y) for x in (x0, x1) for y in range(y0, y1+1))
    return sorted(out)


def exterior_example():
    # Existing 7x7 maximum witness; only safety and exterior radius are used here.
    points = [(0,0),(1,0),(5,0),(1,1),(2,1),(5,2),(6,2),
              (3,3),(5,3),(0,4),(3,5),(4,5),(6,5),(0,6)]
    assert safe(points)
    shells = []
    for r in (1, 2):
        ring = outer_shell(points, r)
        legal = [p for p in ring if is_legal(points, p)]
        shells.append({"r": r, "points_checked": len(ring), "legal_points": legal})
    assert not shells[0]["legal_points"] and shells[1]["legal_points"]
    lines, circles, denominators = triple_curves(points)
    assert max(denominators) <= 72
    dilates = []
    for p in (79, 367):
        assert p % 4 == 3 and all(p % d for d in range(2, isqrt(p)+1))
        assert all(gcd(p, q) == 1 for q in denominators)
        scaled = [(p*x, p*y) for x, y in points]
        assert safe(scaled)
        assert 6*p+1 > len(lines)
        candidates = [(6*p+1, j) for j in range(len(lines)+1)]
        legal = [v for v in candidates if is_legal(scaled, v)]
        assert legal
        witness = legal[0]
        assert witness[0] == 6*p+1 and 0 <= witness[1] <= 6*p
        dilates.append({"scale": p, "safe": True, "exterior_radius": 1,
                        "candidates": candidates, "legal_candidates": legal,
                        "witness": witness, "all_triples_tested_per_candidate": 364})
    return {"points": points, "original_radius": 2, "original_shell_checks": shells,
            "three_point_line_count": len(lines), "three_point_circle_count": len(circles),
            "circle_center_denominators": denominators, "dilates": dilates}


def main():
    pair = circle_pair()
    print("complete circle/profile checks passed", flush=True)
    exterior = exterior_example()
    print("exterior-radius dilation checks passed", flush=True)
    result = {"circle_pair": pair, "exterior_example": exterior,
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "scope": "Exact finite certificates. General proofs are in round16-first-appearance.md and round16-dilation-exterior.md."}
    dest = OUT / "round16_first_appearance.json"
    dest.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print("saved", dest, flush=True)


if __name__ == "__main__":
    main()
