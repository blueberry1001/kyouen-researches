import json
D = r'research\verification\batch09_pairs_n4.json'
d = json.load(open(D, encoding='utf-8'))
rows = d['rows']
N = 4
def xy(i): return (i % N, i // N)
def d4(p, g):
    x, y = p
    if g == 0: return (x, y)
    if g == 1: return (y, x)
    if g == 2: return (N-1-x, y)
    if g == 3: return (x, N-1-y)
    if g == 4: return (N-1-y, N-1-x)
    if g == 5: return (N-1-x, N-1-y)
    if g == 6: return (y, N-1-x)
    return (N-1-y, x)
def idx(q): return q[1]*N + q[0]
def stab(p):
    return [g for g in range(8) if d4(xy(p), g) == xy(p)]
def pair_stab(p, q):
    return [g for g in range(8) if d4(xy(p), g) == xy(p) and d4(xy(q), g) == xy(q)]
def canon_pair(p, q):
    a, b = xy(p), xy(q); best = None
    for g in range(8):
        u, v = d4(a, g), d4(b, g)
        if u > v: u, v = v, u
        if best is None or (u, v) < best: best = (u, v)
    return best
def orbit_size(p, q): return 8 // len(pair_stab(p, q))

orbits = {}
for r in rows:
    orbits.setdefault(canon_pair(r['p'], r['q']), []).append(r)

print('%-26s %5s %6s %6s' % ('orbit rep', 'size', 'flips', 'stab'))
tot4 = totfl4 = 0
for c, mem in sorted(orbits.items()):
    osz = orbit_size(idx(c[0]), idx(c[1]))
    nf = sum(1 for r in mem if r['flip_pair'])
    print('%-26s %5d %6d %6d' % (str(c), osz, nf, 8//osz))
    if osz == 4:
        tot4 += osz; totfl4 += nf
print()
print('orbit size 4 : %d pairs total, %d flip' % (tot4, totfl4))
for sz in (2, 4, 8):
    tot = sum(orbit_size(idx(c[0]), idx(c[1])) for c in orbits)
    fl = 0; tt = 0
    for c, mem in orbits.items():
        if orbit_size(idx(c[0]), idx(c[1])) == sz:
            tt += len(mem); fl += sum(1 for r in mem if r['flip_pair'])
    print('orbit size %d : %3d pairs, %2d flip  (flip rate %.3f)' % (sz, tt, fl, fl/tt if tt else 0))
