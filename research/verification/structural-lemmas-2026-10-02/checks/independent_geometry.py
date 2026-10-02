"""Independent exact checks of the quadratic construction; standard library only."""
import itertools as it
import json
import math
import random
from pathlib import Path


def det(matrix):
    a = [list(row) for row in matrix]
    denominator = 1
    sign = 1
    for k in range(len(a) - 1):
        pivot = next((i for i in range(k, len(a)) if a[i][k]), None)
        if pivot is None:
            return 0
        if pivot != k:
            a[k], a[pivot] = a[pivot], a[k]
            sign = -sign
        value = a[k][k]
        for i in range(k + 1, len(a)):
            for j in range(k + 1, len(a)):
                numerator = a[i][j] * value - a[i][k] * a[k][j]
                assert numerator % denominator == 0
                a[i][j] = numerator // denominator
            a[i][k] = 0
        denominator = value
    return sign * a[-1][-1]


def circle_det(points):
    return det([[x*x+y*y, x, y, 1] for x, y in points])


def is_prime(p):
    return p >= 2 and all(p % d for d in range(2, math.isqrt(p) + 1))


def main():
    rows = []
    for p in range(7, 128, 4):
        if not is_prime(p):
            continue
        parameters = list(range(-1, (p + 5) // 4 + 1))
        points = [(t % p, t*t % p) for t in parameters]
        checked = 0
        for inds in it.combinations(range(len(points)), 4):
            selected = [points[i] for i in inds]
            ts = [parameters[i] for i in inds]
            d = circle_det(selected)
            vandermonde = math.prod(b-a for a, b in it.combinations(ts, 2))
            assert d != 0 and d % p != 0
            assert (d + vandermonde * sum(ts)) % p == 0
            checked += 1
        assert len(points) == (p + 13) // 4
        rows.append(dict(p=p, size=len(points), checked_quads=checked, points=points))

    rng = random.Random(20261002)
    identity_checks = 0
    for p in [7, 11, 19, 23, 31]:
        for _ in range(100):
            ux, uy, vx, vy, wx, wy = [rng.randrange(p) for _ in range(6)]
            cross = ux * vy - uy * vx
            if cross % p == 0:
                continue
            ts = rng.sample(range(p), 4)
            pts = [((ux*t*t + vx*t + wx) % p,
                    (uy*t*t + vy*t + wy) % p) for t in ts]
            vandermonde = math.prod(b-a for a, b in it.combinations(ts, 2))
            expected = cross * vandermonde * (
                (ux*ux+uy*uy)*sum(ts) + 2*(ux*vx+uy*vy))
            assert (circle_det(pts)-expected) % p == 0
            assert (ux*ux+uy*uy) % p != 0
            identity_checks += 1

    upper_checks = []
    for p in [7, 11, 19]:
        m = (p+13)//4
        checked = 0
        for ts in it.combinations(range(p), m+1):
            sums = {sum(q) % p for q in it.combinations(ts, 4)}
            assert len(sums) == p
            checked += 1
        upper_checks.append(dict(p=p, forbidden_size=m+1, subsets=checked))

    output = dict(construction=rows, general_identity_checks=identity_checks,
                  exhaustive_upper_checks=upper_checks,
                  note="Finite checks only; general upper bound uses restricted sumset theorem.")
    out = Path(__file__).with_name("independent_geometry.json")
    out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"primes":len(rows), "quads":sum(r["checked_quads"] for r in rows),
                      "general_identity_checks":identity_checks,
                      "exhaustive_upper_checks":upper_checks}))


if __name__ == "__main__":
    main()
