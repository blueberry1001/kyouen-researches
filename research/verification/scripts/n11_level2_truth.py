"""Decide the true n=11 level-2 count: 7007 (1-word) or 7260 (2-word).

Level 2 is small enough to enumerate exhaustively in Python from the forbidden
4-set rule alone, with no reference to either C++ run. 2 points choose 2, so
the count is the number of pairs {p,q} that are not collinear with any two
other board points -- that is, pairs whose union extends to no forbidden quad.
That is exactly C(121,2) minus the pairs that lie in some forbidden quad, and
each forbidden quad contains 6 pairs, so we can also cross-check by inclusion.
"""
from itertools import combinations

n = 11
pts = [(x, y) for y in range(n) for x in range(n)]
N = len(pts)
assert N == 121


def det4(p, q, r, s):
    m = [[p[0] * p[0] + p[1] * p[1], p[0], p[1], 1],
         [q[0] * q[0] + q[1] * q[1], q[0], q[1], 1],
         [r[0] * r[0] + r[1] * r[1], r[0], r[1], 1],
         [s[0] * s[0] + s[1] * s[1], s[0], s[1], 1]]
    tot = 0
    for i in range(4):
        sub = [[m[r][c] for c in range(1, 4)] for r in range(4) if r != i]
        d3 = (sub[0][0] * (sub[1][1] * sub[2][2] - sub[1][2] * sub[2][1])
              - sub[0][1] * (sub[1][0] * sub[2][2] - sub[1][2] * sub[2][0])
              + sub[0][2] * (sub[1][0] * sub[2][1] - sub[1][1] * sub[2][0]))
        tot += (1 if i % 2 == 0 else -1) * m[i][0] * d3
    return tot


# A 2-point set is safe iff no forbidden quad contains it. Enumerate all quads
# is C(121,4) = 8.5M determinants, which is slow in pure Python; instead index
# by pair: for each pair, we only need to know whether SOME other pair of points
# completes a forbidden quad with it. Use the per-point 3-point-completion table.
from collections import defaultdict

# triples containing each point -> the other two points
# Build by scanning all 4-subsets is too slow; use the "circle through 3 points"
# structure instead: p,q,r,s concyclic-or-collinear iff the circle through p,q,r
# also passes s. So: for each triple, compute the exact integer circle, then find
# all board points on it. That is C(121,3) = 287,980 circles, each tested against
# 121 points -> 35M determinant tests, still slow but tractable if we index by
# a canonical integer circle key.
from math import gcd


def circle_key(p, q, r):
    """Canonical integer key of the circle through p,q,r (or the line if collinear).

    For the conic  x^2+y^2 + D x + E y + F = 0, solve from p,q,r and reduce
    (D,E,F) by their gcd with a fixed sign convention. A line is F = 0 case and
    must be separated from circles, which the reduction does automatically
    because a line has no quadratic part -- we encode lines separately.
    """
    (x1, y1), (x2, y2), (x3, y3) = p, q, r
    a11 = 2 * (x2 - x1); b11 = 2 * (y2 - y1); c11 = x2 * x2 + y2 * y2 - x1 * x1 - y1 * y1
    a12 = 2 * (x3 - x1); b12 = 2 * (y3 - y1); c12 = x3 * x3 + y3 * y3 - x1 * x1 - y1 * y1
    det = a11 * b12 - a12 * b11
    if det == 0:
        return ("line", (a11, b11))          # collinear: normalise the direction
        g = gcd(gcd(abs(a11), abs(b11)), 1) or 1
        return ("line", (a11 // g, b11 // g))
    dD = c11 * b12 - c12 * b11
    dE = a11 * c12 - a12 * c11
    # D = -dD/det, E = -dE/det, F = ... ; scale so the coefficients are integral
    g = gcd(gcd(abs(dD), abs(dE)), abs(det))
    D, E, T = dD // g, dE // g, det // g
    f1 = -(D * x1 + E * y1) - (x1 * x1 + y1 * y1)
    # canonical sign: make T positive if possible, else flip D,E,f
    if T < 0:
        T, D, E, f1 = -T, -D, -E, -f1
    return ("circle", (T, D, E, f1))


# group points by circle key for every triple; a quad is forbidden iff all four
# points share a key.
circle_pts = defaultdict(set)
for p, q, r in combinations(pts, 3):
    circle_pts[circle_key(p, q, r)].update((p, q, r))

F = 0
pairs_in_quad = set()
for key, ps in circle_pts.items():
    if len(ps) >= 4:
        for quad in combinations(sorted(ps), 4):
            F += 1
        for pair in combinations(sorted(ps), 2):
            pairs_in_quad.add(pair)

print(f"forbidden 4-sets F_11 = {F}   (expected 95,670)")

safe_pairs = [pq for pq in combinations(pts, 2) if pq not in pairs_in_quad]
print(f"safe 2-point sets       = {len(safe_pairs)}")
print(f"  1-word run reported   = 7007")
print(f"  2-word run reported   = 7260")
print()
print("LEVEL 2 TRUTH:", len(safe_pairs))
