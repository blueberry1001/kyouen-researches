#!/usr/bin/env python3
"""B131-B138: lattice-point counts on circles, centre-denominator hierarchy.

Exact integer arithmetic only. For small n enumerate every circle through
>=3 board points via circumcentres of triples, count board points on it,
record reduced centre denominator q and squared radius.

Also recompute F-K max over q=1,2 (integer / half-integer centres) and
compare against all-q maxima.
"""
from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "data"


def count_repr(N: int) -> int:
    """# integer (a,b) with a^2+b^2=N, signs and order included."""
    if N < 0:
        return 0
    if N == 0:
        return 1
    c = 0
    a = 0
    while a * a <= N:
        b2 = N - a * a
        b = math.isqrt(b2)
        if b * b == b2:
            if a == 0 and b == 0:
                c += 1
            elif a == 0 or b == 0:
                c += 2
            elif a == b:
                c += 4
            else:
                c += 8
        a += 1
    return c


def circumcircle(p, q, r):
    """Exact circle through 3 non-collinear integer points.

    Returns (qden, cx_num, cy_num, rho) meaning centre=(cx_num/qden, cy_num/qden)
    and (qden*x-cx_num)^2+(qden*y-cy_num)^2 = rho, reduced so gcd(cx,cy,qden)=1.
    Or None if collinear.
    """
    (x1, y1), (x2, y2), (x3, y3) = p, q, r
    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    if d == 0:
        return None
    # centre = (ux/d, uy/d) with integer ux,uy
    s1 = x1 * x1 + y1 * y1
    s2 = x2 * x2 + y2 * y2
    s3 = x3 * x3 + y3 * y3
    ux = s1 * (y2 - y3) + s2 * (y3 - y1) + s3 * (y1 - y2)
    uy = s1 * (x3 - x2) + s2 * (x1 - x3) + s3 * (x2 - x1)
    # centre = (ux/d, uy/d); write as (cx/q, cy/q) with q=|d|/g
    g = math.gcd(math.gcd(abs(ux), abs(uy)), abs(d))
    ux, uy, d = ux // g, uy // g, d // g
    if d < 0:
        ux, uy, d = -ux, -uy, -d
    # now centre=(ux/d, uy/d), gcd(|ux|,|uy|,d) may still share factor with d only
    # reduced denominator q = d / gcd(d, ux, uy) already handled by g above
    # squared radius = ((x1*d-ux)^2+(y1*d-uy)^2) / d^2  => rho / q^2 with q=d
    rho = (x1 * d - ux) ** 2 + (y1 * d - uy) ** 2
    return (d, ux, uy, rho)


def circle_key(circ):
    q, cx, cy, rho = circ
    return (q, cx, cy, rho)


def count_on_circle(circ, n):
    q, cx, cy, rho = circ
    cnt = 0
    pts = []
    for y in range(n):
        for x in range(n):
            a = q * x - cx
            b = q * y - cy
            if a * a + b * b == rho:
                cnt += 1
                pts.append((x, y))
    return cnt, pts


def max_half_integer(n):
    """F-K style: centre (i/2,j/2), count max lattice points on a circle."""
    best = 0
    witness = None
    pts = [(x, y) for y in range(n) for x in range(n)]
    for i2 in range(-1, 2 * n + 1):
        for j2 in range(-1, 2 * n + 1):
            dist = Counter()
            for x, y in pts:
                d4 = (2 * x - i2) ** 2 + (2 * y - j2) ** 2
                dist[d4] += 1
            for d4, cnt in dist.items():
                if d4 > 0 and cnt > best:
                    best = cnt
                    witness = (i2, j2, d4)
    return best, witness


def analyse_n(n: int, max_triples_n: int = 8):
    pts = [(x, y) for y in range(n) for x in range(n)]
    V = n * n
    # enumerate circles via triples (only n <= max_triples_n for full coverage)
    circles = {}
    if n <= max_triples_n:
        for i in range(V):
            for j in range(i + 1, V):
                for k in range(j + 1, V):
                    circ = circumcircle(pts[i], pts[j], pts[k])
                    if circ is None:
                        continue
                    key = circle_key(circ)
                    if key not in circles:
                        circles[key] = circ
    # count points on each distinct circle
    by_q_max = defaultdict(int)  # q -> max points seen
    by_q_max_rho = {}
    max_all = 0
    max_witness = None
    max_key_q = None
    hist = Counter()
    top = []
    for key, circ in circles.items():
        cnt, _ = count_on_circle(circ, n)
        if cnt < 3:
            continue
        hist[cnt] += 1
        q = circ[0]
        if cnt > by_q_max[q]:
            by_q_max[q] = cnt
            by_q_max_rho[q] = circ
        if cnt > max_all:
            max_all = cnt
            max_witness = circ
            max_key_q = q
        top.append((cnt, circ))
    top.sort(reverse=True)
    best_hi, wit_hi = max_half_integer(n)
    return {
        "n": n,
        "n_circles_ge3": sum(hist.values()),
        "hist_points": dict(sorted(hist.items())),
        "max_all_q": max_all,
        "max_all_q_witness": max_witness,
        "max_all_denom": max_key_q,
        "max_half_integer_q12": best_hi,
        "max_half_integer_witness": wit_hi,
        "by_q_max": dict(by_q_max),
        "by_q_max_rho": {str(k): v for k, v in by_q_max_rho.items()},
        "top5": [(c, cxy) for c, cxy in top[:5]],
    }


def radius_type(N: int) -> str:
    """prime signature of N (the 4*r^2 numerator for half-integer centres)."""
    n = N
    fac = []
    d = 2
    while d * d <= n:
        e = 0
        while n % d == 0:
            n //= d
            e += 1
        if e:
            fac.append((d, e))
        d += 1 if d == 2 else 2
    if n > 1:
        fac.append((n, 1))
    return "*".join(f"{p}^{e}" for p, e in fac)


def mz_table(max_n=31):
    """F-K measured M(n) and witness N, check B137 (new type before each jump)."""
    measured = {
        2: 4, 3: 4, 4: 8, 5: 8, 6: 8, 7: 8, 8: 12, 9: 12, 10: 12, 11: 12,
        12: 16, 13: 16, 14: 16, 15: 16, 16: 16, 17: 16, 18: 16, 19: 16,
        20: 16, 21: 16, 22: 16, 23: 16, 24: 16, 25: 20, 26: 24, 27: 24,
        28: 24, 29: 24, 30: 24, 31: 24,
    }
    witness_N = {2: 2, 4: 10, 8: 50, 12: 130, 25: 650, 26: 650}
    jumps = []
    prev = None
    for n in range(2, 32):
        m = measured[n]
        if prev is not None and m > prev:
            N = witness_N.get(n)
            jumps.append({
                "n_jump": n,
                "from": prev,
                "to": m,
                "witness_N": N,
                "witness_type": radius_type(N) if N else None,
                "new_type_at_n": n in witness_N and (n - 1 not in witness_N or witness_N.get(n) != witness_N.get(n - 1)),
            })
        prev = m
    return {"measured": measured, "jumps": jumps, "witness_N": witness_N}


def b135_same_radius_diff_centres():
    """Same r^2, different centre denominators, different lattice-point counts
    on the full infinite lattice (before board truncation)."""
    examples = []
    # For r^2 = 5/4 : centre (0,0) denom1 -> a^2+b^2=5/4 no lattice pts
    #                 centre (1/2,1/2) denom2 -> (2x-1)^2+(2y-1)^2=5, odd, 0 sols
    # Better: use r^2 = 25/4
    # centre (0,0): a^2+b^2=25/4 no
    # centre (1/2,1/2): (2x-1)^2+(2y-1)^2=25. odd pairs: (±3,±4)no, (±5,0)no, (±1,±√24)no
    #   25=25+0, 16+9. (±5,0) even, (±4,±3) one even. odd-odd: 25=9+16 no both odd.
    # centre (1/3,1/3): (3x-1)^2+(3y-1)^2=25*9/4 not integer -- use r^2=225/9=25
    # centre (1/3,0): (3x-1)^2+(3y)^2=225. a≡2 (mod 3), b≡0 (mod 3).
    #   a^2+b^2=225: (0,±15),(±15,0),(±9,±12),(±12,±9)
    #   a≡2: 15≡0, 0≡0, 9≡0, 12≡0 -- none ≡2. 0 pts.
    # Try r^2=50/4=25/2
    # centre (0,0): a^2+b^2=25/2 no
    # centre (1/2,1/2): (2x-1)^2+(2y-1)^2=50. odd-odd a^2+b^2=50: 1+49=50, 25+25=50.
    #   (±1,±7),(±7,±1),(±5,±5): 8+4=12 points? (±1,±7): 4*2=8 (order), (±5,±5): 4. Total 12.
    # centre (1/3, 1/3): (3x-1)^2+(3y-1)^2=50*9=450. a,b≡2 (mod 3).
    #   a^2+b^2=450: (±15,±15),(±3,±21),(±21,±3),(±9,±? ) 225+225, 9+441, 81+369 no, 117+333 no
    #   450=225+225, 9+441, 81+369? 450-81=369 not square. 450-49=401 no. 450-121=329 no.
    #   450-169=281 no. 450-289=161 no. 450-361=89 no.
    #   so (±15,±15),(±3,±21),(±21,±3).
    #   15≡0, 3≡0, 21≡0 -- none ≡2. 0 pts.
    # Concrete working example via code below.
    return examples


def find_b135_examples(max_abs=6):
    """Search small same-r^2 different-centre examples by brute force."""
    found = []
    # enumerate circles from triples on a slightly larger ambient box
    seen = {}  # (q,cx,cy,rho) -> count on infinite lattice (residue-restricted)
    # instead: for each rational centre with q<=4 and |cx|,|cy| small, and rho small
    from fractions import Fraction as F

    def infinite_count(q, cx, cy, rho):
        # count (x,y) in Z^2 with (qx-cx)^2+(qy-cy)^2=rho, via residue classes
        # a=qx-cx => a ≡ -cx (mod q), similarly b
        c = 0
        lim = math.isqrt(rho) + 1
        for a in range(-lim, lim + 1):
            if (a + cx) % q != 0:
                continue
            b2 = rho - a * a
            if b2 < 0:
                continue
            b = math.isqrt(b2)
            if b * b != b2:
                continue
            for sb in ({b, -b} if b else {0}):
                if (sb + cy) % q == 0:
                    c += 1
        return c

    # group by r^2 as Fraction
    by_r2 = defaultdict(list)
    for q in range(1, 5):
        for cx in range(-4, 5):
            for cy in range(-4, 5):
                g = math.gcd(math.gcd(abs(cx), abs(cy)), q)
                if g != 1:
                    continue  # not reduced
                for rho in range(1, 80):
                    r2 = F(rho, q * q)
                    cnt = infinite_count(q, cx, cy, rho)
                    if cnt > 0:
                        by_r2[r2].append((q, cx, cy, rho, cnt))
    for r2, lst in by_r2.items():
        qs = {}
        for q, cx, cy, rho, cnt in lst:
            qs.setdefault(q, []).append(cnt)
        if len(qs) >= 2:
            # same radius, different denominators present
            max_per_q = {q: max(cs) for q, cs in qs.items()}
            if len(set(max_per_q.values())) >= 1 and len(max_per_q) >= 2:
                found.append({
                    "r2": str(r2),
                    "max_count_by_q": max_per_q,
                    "examples": lst[:8],
                })
    return found[:12]


def main():
    report = {}
    print("=== per-n circle census (n=2..8) ===", flush=True)
    per_n = {}
    for n in range(2, 9):
        r = analyse_n(n)
        per_n[n] = r
        print(
            f"  n={n}: max_all_q={r['max_all_q']} (q={r['max_all_denom']}) "
            f"max_q12={r['max_half_integer_q12']} hist={r['hist_points']}",
            flush=True,
        )
    report["per_n"] = per_n

    print("=== F-K M(n) jumps / B137 ===", flush=True)
    mz = mz_table()
    report["mz_jumps"] = mz
    for j in mz["jumps"]:
        print(f"  {j}", flush=True)

    print("=== B135 same radius different centres ===", flush=True)
    b135 = find_b135_examples()
    report["b135"] = b135
    for e in b135[:6]:
        print(f"  r2={e['r2']} by_q={e['max_count_by_q']}", flush=True)

    # B134: for fixed r2 bound, max points by q
    print("=== B134 max points by denom q (r2<=25) ===", flush=True)
    by_q = defaultdict(int)
    for q in range(1, 6):
        best = 0
        for cx in range(-6, 7):
            for cy in range(-6, 7):
                if math.gcd(math.gcd(abs(cx), abs(cy)), q) != 1 and not (cx == 0 and cy == 0 and q == 1):
                    if q > 1:
                        continue
                for rho in range(1, int(25 * q * q) + 1):
                    # count
                    c = 0
                    lim = math.isqrt(rho) + 1
                    for a in range(-lim, lim + 1):
                        if (a + cx) % q != 0:
                            continue
                        b2 = rho - a * a
                        if b2 < 0:
                            continue
                        b = math.isqrt(b2)
                        if b * b != b2:
                            continue
                        for sb in ({b, -b} if b else {0}):
                            if (sb + cy) % q == 0:
                                c += 1
                    if c > best:
                        best = c
        by_q[q] = best
        print(f"  q={q}: max infinite points (r^2<=25) = {best}", flush=True)
    report["b134_by_q"] = dict(by_q)

    out = OUT / "circle_b131_b138.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
