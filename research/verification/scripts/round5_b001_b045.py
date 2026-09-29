#!/usr/bin/env python3
"""B045: D4 stabilizer sizes for n=5 maximal safe sets (quick)."""
import sys, json, time
from collections import Counter
sys.path.insert(0, r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\scripts")
from kyouen_core import Board, square_points

def b045_n5():
    t0 = time.time()
    n = 5
    b = Board(square_points(n), f"n{n}")
    V = b.V
    quads_by_pt = b.quads_by_pt
    full = b.full

    def legal_moves(occ):
        out = []
        empty = full ^ occ
        for v in range(V):
            if empty & (1 << v):
                bit = 1 << v
                ok = True
                for q in quads_by_pt[v]:
                    if (occ & q) == (q & ~bit):
                        ok = False
                        break
                if ok:
                    out.append(v)
        return out

    maximal = []
    def dfs2(occ, start):
        all_moves = legal_moves(occ)
        if not all_moves:
            maximal.append(occ)
            return
        for v in all_moves:
            if v >= start:
                dfs2(occ | (1 << v), v + 1)
    dfs2(0, 0)
    print(f"maximal: {len(maximal)}, {time.time()-t0:.1f}s", flush=True)

    def tid(x, y, op):
        if op == 0: return (x, y)
        if op == 1: return (y, x)
        if op == 2: return (x, n-1-y)
        if op == 3: return (n-1-x, y)
        if op == 4: return (y, n-1-x)
        if op == 5: return (n-1-x, n-1-y)
        if op == 6: return (n-1-y, x)
        if op == 7: return (n-1-y, n-1-x)

    def stab_size(s):
        c = 0
        for op in range(8):
            t = 0
            for i in range(V):
                if s & (1 << i):
                    x, y = i % n, i // n
                    nx, ny = tid(x, y, op)
                    t |= 1 << (ny * n + nx)
            if t == s:
                c += 1
        return c

    size_stab = {}
    for s in maximal:
        k = bin(s).count('1')
        st = stab_size(s)
        size_stab.setdefault(k, Counter())[st] += 1

    out = {}
    for k in sorted(size_stab):
        c = size_stab[k]
        total = sum(c.values())
        ge2 = sum(v for st, v in c.items() if st >= 2)
        ge4 = sum(v for st, v in c.items() if st >= 4)
        print(f"  k={k}: n={total}, stab_hist={dict(sorted(c.items()))}, stab>=2: {ge2} ({100*ge2/total:.1f}%), stab>=4: {ge4}", flush=True)
        out[k] = {"n": total, "stab_hist": dict(sorted(c.items())),
                  "stab_ge2": ge2, "stab_ge2_frac": round(ge2/total, 4),
                  "stab_ge4": ge4}
    return out

if __name__ == "__main__":
    r = b045_n5()
    with open(r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round5_b001_b045.json", "w") as f:
        json.dump({"n5": r}, f, indent=2)
    print("Done.", flush=True)
