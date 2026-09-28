import json
D = r'research\verification\batch09_pairs_n4.json'
d = json.load(open(D, encoding='utf-8'))
rows = d['rows']
N = 4
def xy(i): return (i % N, i // N)          # x=col, y=row

# ---- D4 group on a 4x4 square -------------------------------------------
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
GS = list(range(8))

def canon_pair(p, q):
    a, b = xy(p), xy(q)
    best = None
    for g in GS:
        u, v = d4(a, g), d4(b, g)
        if u > v: u, v = v, u
        t = (u, v)
        if best is None or t < best: best = t
    return best

def point_type(p):
    x, y = xy(p)
    d = min(x, y, N-1-x, N-1-y)   # distance to nearest border
    if d == 0: return 'border'
    if d == 1: return 'inner2'
    return 'core'

flips = [r for r in rows if r['flip_pair']]
print('=== B209: D4 orbit decomposition of the 12 flipping pairs ===')
orbits = {}
for r in flips:
    c = canon_pair(r['p'], r['q'])
    orbits.setdefault(c, []).append((r['p'], r['q']))
print('n flipping pairs =', len(flips), ' distinct D4 orbits =', len(orbits))
for c, mem in sorted(orbits.items()):
    pt = point_type(idx(c[0])), point_type(idx(c[1]))
    print('  orbit rep %s  size=%d  types=%s  members=%s' % (c, len(mem), pt, mem))

print()
print('=== orbit table: orbit -> (size, #flipping pairs in orbit) ===')
allorbits = {}
for r in rows:
    c = canon_pair(r['p'], r['q'])
    allorbits.setdefault(c, []).append(r)
sym_orbits = []; asym_orbits = []
for c, mem in sorted(allorbits.items()):
    nf = sum(1 for r in mem if r['flip_pair'])
    tag = 'SYMMETRIC' if c[0] == (N-1-c[0][0], N-1-c[0][1]) and c[1] == (N-1-c[1][0], N-1-c[1][1]) else 'asymmetric'
    line = 'rep=%s size=%d flips=%d %s' % (c, len(mem), nf, tag)
    (sym_orbits if tag == 'SYMMETRIC' else asym_orbits).append((c, len(mem), nf))
    print(' ', line)
print()
print('symmetric orbits: %d (total pairs %d, flips %d)' % (len(sym_orbits), sum(x[1] for x in sym_orbits), sum(x[2] for x in sym_orbits)))
print('asymmetric orbits: %d (total pairs %d, flips %d)' % (len(asym_orbits), sum(x[1] for x in asym_orbits), sum(x[2] for x in asym_orbits)))

print()
print('=== B210: point-type signature of the 12 flipping pairs ===')
sig = {}
for r in flips:
    t = tuple(sorted([point_type(r['p']), point_type(r['q'])]))
    sig[t] = sig.get(t, 0) + 1
for k, v in sorted(sig.items()):
    print('  %s : %d pairs' % (k, v))
print()
print('flipping pairs (p,q, type pair, d(p),d(q) unavail here):')
for r in flips:
    print('   p=%2d q=%2d  (%s,%s) -> (%s,%s)' % (r['p'], r['q'], xy(r['p']), xy(r['q']),
                                                  point_type(r['p']), point_type(r['q'])))
print()
print('=== B206: which single deletions already flip? ===')
fp = [r for r in rows if r['flip_p'] or r['flip_q']]
print('pairs where a single deletion already flips:', len(fp))
print('pairs with K drop:', sum(1 for r in rows if r['K_pair'] < r['K_full']))
print('K_pair values seen:', sorted(set(r['K_pair'] for r in rows)))
print('g_pair values seen:', sorted(set(r['g_pair'] for r in rows)))
