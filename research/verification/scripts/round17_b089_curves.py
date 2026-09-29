"""Integer certificates for the prime-board construction used to refute B089.

The upper bound for bounded-degree curves is a published uniform theorem.
These checks validate the lower-bound construction, not that external theorem.
"""
from itertools import combinations
from math import comb, isqrt, prod
from pathlib import Path
import hashlib
import json


def is_prime(p):
    return p >= 2 and all(p % d for d in range(2, isqrt(p) + 1))


def det3(a, b, c):
    return (a[0] * (b[1]*c[2] - b[2]*c[1])
            - a[1] * (b[0]*c[2] - b[2]*c[0])
            + a[2] * (b[0]*c[1] - b[1]*c[0]))


def circle_det(points):
    x0, y0 = points[0]
    q0 = x0*x0 + y0*y0
    rows = [(x-x0, y-y0, x*x+y*y-q0) for x, y in points[1:]]
    return det3(*rows)  # determinant with columns [1,x,y,x*x+y*y]


def line_det(points):
    (a, b), (c, d), (e, f) = points
    return (c-a)*(f-b) - (d-b)*(e-a)


def check_prime(p):
    assert is_prime(p) and p >= 5
    m = (p-1)//4
    points = [(t, t*t % p) for t in range(1, m+1)]
    assert len(set(points)) == m
    assert all(0 <= x < p and 0 <= y < p for x, y in points)
    min_sum = max_sum = None
    for triple in combinations(points, 3):
        xs = [a[0] for a in triple]
        expected = prod(b-a for a, b in combinations(xs, 2)) % p
        actual = line_det(triple)
        assert actual % p == expected != 0
        assert actual != 0
    for four in combinations(points, 4):
        xs = [a[0] for a in four]
        t_sum = sum(xs)
        assert 0 < t_sum < p
        expected = t_sum * prod(b-a for a, b in combinations(xs, 2)) % p
        actual = circle_det(four)
        assert actual % p == expected != 0
        assert actual != 0
        min_sum = t_sum if min_sum is None else min(min_sum, t_sum)
        max_sum = t_sum if max_sum is None else max(max_sum, t_sum)
    return {"prime": p, "size": m, "points": points,
            "all_triples_checked": comb(m, 3),
            "all_quads_checked": comb(m, 4),
            "four_x_sum_range": [min_sum, max_sum],
            "no_three_collinear": True, "no_four_concyclic": True}


def main():
    primes = [p for p in range(5, 128) if is_prime(p)] + [251]
    records = [check_prime(p) for p in primes]
    # Independent exact polynomial identity on the ordinary (unreduced) parabola.
    identity_count = 0
    for xs in combinations(range(-7, 8), 4):
        expected = sum(xs) * prod(b-a for a, b in combinations(xs, 2))
        assert circle_det([(t, t*t) for t in xs]) == expected
        identity_count += 1
    # The short-interval condition matters: a full finite-field parabola has violations.
    # Here 1+2+6+8=17 gives a zero determinant modulo 17.
    xs = [1, 2, 6, 8]
    mod_zero = circle_det([(t, t*t % 17) for t in xs])
    assert mod_zero % 17 == 0
    data = {
        "claim": "B089 REFUTED by uniform curve bound plus prime-board construction",
        "proof": "round17-b089-bounded-degree.md",
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "primes_tested": len(records),
        "total_triples_checked": sum(r["all_triples_checked"] for r in records),
        "total_quads_checked": sum(r["all_quads_checked"] for r in records),
        "unreduced_parabola_identity_checks": identity_count,
        "excluded_full_interval_modular_zero": {"p": 17, "t": xs,
                                                 "integer_det": mod_zero},
        "records": records,
        "scope": "Finite checks supplement the all-prime algebraic proof; no asymptotic fit."
    }
    target = Path(__file__).resolve().parents[1] / "round17_b089_curves.json"
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: data[key] for key in
                      ["primes_tested", "total_triples_checked", "total_quads_checked",
                       "unreduced_parabola_identity_checks"]}))


if __name__ == "__main__":
    main()
