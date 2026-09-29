"""How much does D4 symmetry buy on the 11x11 board?

A generic position has a trivial stabiliser, so its D4 orbit has size 8 and a
symmetry-reduced solver does 1/8 of the work. Positions with a non-trivial
stabiliser exist but get rarer as k grows, so 1/8 is the right number to
budget with. This also reports the point-orbit decomposition, which is what a
solver would key on.
"""
n = 11
V = n * n
pts = [(x, y) for y in range(n) for x in range(n)]

# The 8 elements of D4, as coordinate transforms.
TRANSFORMS = [
    lambda x, y: (x, y),                 # identity
    lambda x, y: (y, n - 1 - x),         # rot 90
    lambda x, y: (n - 1 - x, n - 1 - y), # rot 180
    lambda x, y: (n - 1 - y, x),         # rot 270
    lambda x, y: (n - 1 - x, y),         # reflect horizontally
    lambda x, y: (x, n - 1 - y),         # reflect vertically
    lambda x, y: (y, x),                 # reflect main diagonal
    lambda x, y: (n - 1 - y, n - 1 - x), # reflect anti-diagonal
]


def image(gi, x, y):
    X, Y = TRANSFORMS[gi](x, y)
    return Y * n + X


# point orbits
seen = [False] * V
orbits = []
for i in range(V):
    if seen[i]:
        continue
    orb = sorted({image(g, *pts[i]) for g in range(8)})
    orbits.append(orb)
    for j in orb:
        seen[j] = True

print(f"n={n}: {V} points fall into {len(orbits)} D4 orbits")
print(f"  orbit sizes: {[len(o) for o in orbits]}")
print(f"  sum = {sum(len(o) for o in orbits)} (must be {V})")
print()

# A point is fixed by a reflection only if it lies on that reflection's axis.
# For an odd board the two diagonals and the centre line/column contain the
# fixed points; counting them tells us how much the stabiliser structure costs.
axes = {
    "vert centre line": lambda x, y: x == n // 2,
    "horz centre line": lambda x, y: y == n // 2,
    "main diagonal": lambda x, y: x == y,
    "anti diagonal": lambda x, y: x + y == n - 1,
}
for name, pred in axes.items():
    cnt = sum(1 for (x, y) in pts if pred(x, y))
    print(f"  points on {name:18s}: {cnt}")
print()

print("generic position stabiliser: trivial -> D4 orbit size 8")
print("=> a symmetry-reduced solver does 1/8 of the work in the best case")
print()

PEAK = 187_879_156            # measured, k=5
print(f"measured peak so far: k=5 with {PEAK:,} states")
print(f"  after 1/8 symmetry: {PEAK // 8:,} states "
      f"({(PEAK // 8) * 16 / 2**30:.2f} GiB at 16 B/state)")
print()

BUDGET = 19 * 2**30 // 16
print(f"19 GB of RAM holds {BUDGET:,} states at 16 B/state")
print(f"last observed growth ratio entering k=6: 22.37x")
print(f"with the 1/8 cut the effective ratio is {22.37 / 8:.2f}x")
print()

print("k(n) series for n=1..9 (known): 1, 3, 5, 7, 9, 11, 14, 15, 18")
print("n=10 and n=11 are expected around 20-22, so the peak layer sits near")
print("k=10-11. Whether that peak fits in 19 GB depends on how far the growth")
print("ratio decays before it turns over, and that is the open question.")
