"""Independent check of the collinear-quad asymptotic claim in
round4-collinear-asymptotic.md.

We do NOT trust the existing script. We recompute D_n two independent ways
for n = 2..12:
  (a) brute force: all 4-subsets, exact integer collinearity test
  (b) the claimed closed form (4): sum over primitive directions H of
      2*phi(H) * sum_{t>=3} C(t-1,2) (n-H t)(2 n - H t)
and compare with the tabulated values in the proof note.
"""
from math import comb, gcd
from itertools import combinations
from fractions import Fraction

# totient sieve
LIMIT = 200
phi = list(range(LIMIT + 1))
for p in range(2, LIMIT + 1):
    if phi[p] == p:
        for k in range(p, LIMIT + 1, p):
            phi[k] -= phi[k] // p
phi[1] = 1


def D_brute(n):
    """All collinear 4-subsets of {0..n-1}^2, exact integer test."""
    pts = [(x, y) for y in range(n) for x in range(n)]
    total = 0
    for a, b, c, d in combinations(pts, 4):
        # (b-a) x (c-a) == 0  and  (b-a) x (d-a) == 0  =>  a,b,c,d collinear
        u = (b[0] - a[0], b[1] - a[1])
        v = (c[0] - a[0], c[1] - a[1])
        w = (d[0] - a[0], d[1] - a[1])
        if u[0] * v[1] - u[1] * v[0] == 0 and u[0] * w[1] - u[1] * w[0] == 0:
            total += 1
    return total


def D_formula(n):
    """The claimed finite sum (4) in round4-collinear-asymptotic.md."""
    total = 0
    for H in range(1, (n - 1) // 3 + 1):
        inner = 0
        for t in range(3, (n - 1) // H + 1):
            inner += comb(t - 1, 2) * (n - H * t) * (2 * n - H * t)
        total += 2 * phi[H] * inner
    return total


def D_runs(n):
    """Third way: max-length lines, sum C(len,4). Independent derivation."""
    total = 0
    # every maximal lattice line in the square, counted once via its
    # smallest point in a canonical direction
    dirs = []
    for dx in range(0, n):
        for dy in range(-n + 1, n):
            if dx == 0 and dy <= 0:
                continue
            if dx == 0 and dy > 0:
                pass
            if gcd(dx, abs(dy)) != 1:
                continue
            if dx < 0:
                continue
            dirs.append((dx, dy))
    seen = set()
    for (dx, dy) in dirs:
        for (sx, sy) in [(x, y) for y in range(n) for x in range(n)]:
            # start point: the predecessor p-(dx,dy) must be off-board
            if 0 <= sx - dx < n and 0 <= sy - dy < n:
                continue
            cnt, px, py = 0, sx, sy
            while 0 <= px < n and 0 <= py < n:
                cnt += 1
                px += dx
                py += dy
            if cnt >= 4:
                total += comb(cnt, 4)
    return total


print(f"{'n':>3} {'brute':>10} {'formula':>10} {'runs':>10}  agree")
bad = 0
for n in range(4, 12):
    b, f, r = D_brute(n), D_formula(n), D_runs(n)
    ok = (b == f == r)
    if not ok:
        bad += 1
    print(f"{n:>3} {b:>10} {f:>10} {r:>10}  {'OK' if ok else 'MISMATCH'}")
print(f"\nindependent agreement: {'PASS' if bad == 0 else f'FAIL ({bad})'}")

# asymptotic coefficient, exact rational via phi up to 200k
L = 200_000
phi2 = list(range(L + 1))
for p in range(2, L + 1):
    if phi2[p] == p:
        for k in range(p, L + 1, p):
            phi2[k] -= phi2[k] // p
phi2[1] = 1
s = sum(Fraction(phi2[H], H ** 3) for H in range(1, L + 1))
# tail bound: sum_{H>L} phi(H)/H^3 <= sum 1/H^2 <= 1/L
c = Fraction(7, 60) * s
print(f"\npartial sum S_L      = {float(s):.12f}")
print(f"leading const 7/60*S = {float(c):.12f}")
print(f"tail bound           <= 7/60 * 1/L = {float(Fraction(7,60)/L):.3e}")
print(f"7*zeta(2)/(60*zeta(3)) = "
      f"{7 * 1.6449340668482264 / (60 * 1.2020569031595943):.12f}")
lo, hi = float(c), float(c + Fraction(7, 60) / L)
print(f"claimed interval in note: 0.159649781475 < c < 0.159650948143")
print(f"our bracket            : {lo:.12f} < c < {hi:.12f}")
print("interval consistent:", lo > 0.159649781 and hi < 0.159650948)
