"""Exact checks for B141/B145/B150/B471/B472/B473; no floating point.

Three independent counts: endpoint formula, maximal lattice lines, and
direct enumeration of collinear quadruples on small boards. The infinite
claims are proved in round4-collinear-asymptotic.md, not fitted here.
"""
from collections import Counter
from fractions import Fraction
from itertools import combinations
from math import comb, gcd
from pathlib import Path
import json


def phi_sieve(limit):
    phi = list(range(limit + 1))
    for p in range(2, limit + 1):
        if phi[p] == p:
            for k in range(p, limit + 1, p):
                phi[k] -= phi[k] // p
    if limit:
        phi[1] = 1
    return phi


def direction_count(n, a, b):
    a, b = abs(a), abs(b)
    assert gcd(a, b) == 1
    height = max(a, b)
    return sum(comb(t - 1, 2) * (n - t * a) * (n - t * b)
               for t in range(3, (n - 1) // height + 1))


def total_via_power_sums(n, phi):
    total = 0
    for h in range(1, (n - 1) // 3 + 1):
        q = (n - 1) // h
        s1 = q * (q + 1) // 2
        s2 = q * (q + 1) * (2 * q + 1) // 6
        s3 = s1 * s1
        s4 = q * (q + 1) * (2 * q + 1) * (3 * q * q + 3 * q - 1) // 30
        subtotal = (h*h*s4 - 3*h*(n+h)*s3 + (2*n*n+9*n*h+2*h*h)*s2
                    - 6*n*(n+h)*s1 + 4*n*n*q)
        total += phi[h] * subtotal
    return total


def directions(n):
    yield 0, 1
    for a in range(1, n):
        for b in range(-(n-1), n):
            if gcd(a, abs(b)) == 1:
                yield a, b


def maximal_line_counts(n):
    result = {}
    for a, b in directions(n):
        count = 0
        for x in range(n):
            for y in range(n):
                if 0 <= x-a < n and 0 <= y-b < n:
                    continue
                length, xx, yy = 0, x, y
                while 0 <= xx < n and 0 <= yy < n:
                    length += 1
                    xx += a
                    yy += b
                if length >= 4:
                    count += comb(length, 4)
        result[a, b] = count
    return result


def brute_collinear(n):
    points = [(x, y) for y in range(n) for x in range(n)]
    count = 0
    for p, q, r, s in combinations(points, 4):
        dx, dy = q[0]-p[0], q[1]-p[1]
        if dx*(r[1]-p[1]) != dy*(r[0]-p[0]):
            continue
        if dx*(s[1]-p[1]) == dy*(s[0]-p[0]):
            count += 1
    return count


def rat(x):
    return {"numerator": x.numerator, "denominator": x.denominator}


def decimal_floor(x, digits=12):
    sign = "-" if x < 0 else ""
    scaled = abs(x.numerator) * 10**digits // x.denominator
    return f"{sign}{scaled // 10**digits}.{scaled % 10**digits:0{digits}d}"


def main():
    limit = 100000
    phi = phi_sieve(limit)
    result = {"integer_only": True, "small_checks": [], "large_exact_counts": [],
              "direction_coefficients": [], "claims_proved_in_markdown":
              ["B141", "B145", "B150", "B471", "B472", "B473"]}
    known = {2: 0, 3: 0, 4: 10, 5: 64, 6: 234, 7: 660, 8: 1524,
             9: 3156, 10: 5928, 11: 10428}
    for n in range(1, 21):
        by_line = maximal_line_counts(n)
        endpoint = {v: direction_count(n, *v) for v in by_line}
        assert endpoint == by_line
        total = total_via_power_sums(n, phi)
        assert total == sum(by_line.values())
        if n in known:
            assert total == known[n]
        brute = brute_collinear(n) if n <= 7 else None
        if brute is not None:
            assert brute == total
        heights = Counter()
        for (a, b), value in by_line.items():
            heights[max(abs(a), abs(b))] += value
        for h in range(1, n+1):
            tail = sum(v for height, v in heights.items() if height > h)
            assert h * tail <= 2 * n**5
        result["small_checks"].append({"n": n, "D": total,
            "directions_checked": len(by_line), "brute_quadruples_checked":
            comb(n*n, 4) if n <= 7 and n*n >= 4 else 0,
            "direct_count": brute, "all_equal": True})
    quantum = 10**18
    floor_sum3 = 0
    floor_sum2 = 0
    requested = {4, 8, 16, 32, 40, 64, 128, 256, 512, 1024, 4096, 16384, 65536, 100000}
    for n in range(1, limit+1):
        floor_sum3 += quantum * phi[n] // n**3
        floor_sum2 += quantum * phi[n] // n**2
        if n not in requested:
            continue
        total = total_via_power_sums(n, phi)
        ratio = Fraction(total, n**5)
        # R = D/n^4 - (7/60)n*sum(phi/h^3) + (3/4)sum(phi/h^2).
        # Rounding intervals rigorously account for every truncated summand.
        residual_lo = Fraction(total, n**4) - Fraction(7*n*(floor_sum3+n), 60*quantum) + Fraction(3*floor_sum2, 4*quantum)
        residual_hi = Fraction(total, n**4) - Fraction(7*n*floor_sum3, 60*quantum) + Fraction(3*(floor_sum2+n), 4*quantum)
        result["large_exact_counts"].append({"n": n, "D": total,
            "D_over_n5": rat(ratio), "D_over_n5_decimal_truncated": decimal_floor(ratio),
            "finite_sum_residual_over_n4_interval": [rat(residual_lo), rat(residual_hi)]})
    constant_lo = Fraction(7*floor_sum3, 60*quantum)
    constant_hi = constant_lo + Fraction(7*limit, 60*quantum) + Fraction(7, 60*limit)
    result["leading_constant_rigorous_interval"] = {
        "truncation_height": limit, "lower": rat(constant_lo), "upper": rat(constant_hi),
        "lower_decimal_truncated": decimal_floor(constant_lo),
        "upper_decimal_truncated": decimal_floor(constant_hi)}
    for a, b in [(1,0), (1,1), (2,1), (5,1), (5,4), (7,3)]:
        height = max(a,b)
        coefficient = Fraction(5*height-3*min(a,b), 120*height**4)
        result["direction_coefficients"].append({"direction": [a,b],
            "exact_limit_D_over_n5": rat(coefficient),
            "n1024_D": direction_count(1024,a,b)})
    output = Path(__file__).resolve().parents[1] / "round4_collinear_asymptotic.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print("All 20 maximal-line / endpoint / totient comparisons passed; direct n<=7 passed.")
    print("Constant interval:", decimal_floor(constant_lo), decimal_floor(constant_hi))
    for row in result["large_exact_counts"]:
        print(row["n"], row["D"], row["D_over_n5_decimal_truncated"])
    print(output)


if __name__ == "__main__":
    main()
