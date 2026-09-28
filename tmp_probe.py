import sys, time, itertools
from pathlib import Path
HERE = Path('research/verification/scripts').resolve()
sys.path.insert(0, str(HERE))
from round3_chunk8_lib import Quads, all_forbidden, square

def max_safe(q):
    """Exact maximum safe-set size, branch and bound, ordered by degree."""
    V = q.V
    nbr = [0]*V
    for qq in q.quads:
        b = qq
        pts = [i for i in range(V) if (qq>>i)&1]
        for i in range(4):
            for j in range(4):
                if i!=j:
                    nbr[pts[i]] |= 1<<pts[j]
    # constraint: for each quad, can't take all 4
    # use DFS over vertices in fixed order with pruning
    best = [0]
    order = sorted(range(V), key=lambda v: -bin(nbr[v]).count('1'))
    pos = {v:i for i,v in enumerate(order)}
    cquads = []
    for qq in q.quads:
        cquads.append([pos[i] for i in range(V) if (qq>>i)&1])
    cquads = [sorted(c) for c in cquads]
    # index: for each vertex in order-space, list of (other 3) in order-space
    c3 = [[] for _ in range(V)]
    for c in cquads:
        for t in range(4):
            c3[c[t]].append(tuple(c[u] for u in range(4) if u!=t))
    # suffix masks
    suffix = [0]*(V+1)
    for i in range(V-1,-1,-1):
        suffix[i] = suffix[i+1] | (1<<i)
    def dfs(occ_mask, start, size):
        if size > best[0]:
            best[0] = size
        avail = suffix[start]
        n_avail = bin(avail).count('1')
        if size + n_avail <= best[0]:
            return
        for v in range(start, V):
            bit = 1<<v
            if not (occ_mask & bit):
                continue
            ok = True
            for t in c3[v]:
                m = 0
                for u in t: m |= 1<<u
                if (m & occ_mask) == m:
                    ok = False; break
            if ok:
                dfs(occ_mask | bit, v+1, size+1)
    # simple: choose greedily with pruning
    def rec(chosen_mask, start, size):
        if size > best[0]:
            best[0] = size
        if size + (V-start) <= best[0]:
            return
        for v in range(start, V):
            if chosen_mask & (1<<v): continue
            ok = True
            for t in c3[v]:
                mm = 0
                for u in t: mm |= 1<<u
                if (mm & chosen_mask) == mm:
                    ok = False; break
            if ok:
                rec(chosen_mask | (1<<v), v+1, size+1)
    rec(0,0,0)
    return best[0]

for n in (3,4):
    q = Quads(square(n), all_forbidden(square(n)))
    t0=time.time()
    K = max_safe(q)
    print('n',n,'K',K, round(time.time()-t0,2),'s')

for n in (5,):
    q = Quads(square(n), all_forbidden(square(n)))
    t0=time.time()
    K = max_safe(q)
    print('n',n,'K',K, round(time.time()-t0,2),'s')
