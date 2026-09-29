#!/usr/bin/env python3
"""Round5 followup B072: max b_S(p) for safe k-sets at k=5 (and k=6 for n<=5).
Also B045: D4 stabilizer sizes for n=5 maximal sets (already enumerated).
B054: residual splitting rate for n=5 at remaining-depth >= 4."""
import sys, json, time
from collections import Counter
sys.path.insert(0, r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\scripts")
from kyouen_core import Board, square_points

def b072_k5(n, k=5):
    """Max over safe k-sets S and empty points p of b_S(p) = #quads containing p whose other 3 pts are in S."""
    t0 = time.time()
    b = Board(square_points(n), f"n{n}")
    V = b.V
    quads_by_pt = b.quads_by_pt
    full = b.full
    print(f"B072 n={n} k={k}: V={V}, quads={len(b.quads)}", flush=True)

    max_b = 0
    witness = None
    n_safe = 0
    hist = Counter()

    # enumerate C(V,k) subsets via recursion
    pts = list(range(V))
    def rec(chosen, start):
        nonlocal max_b, witness, n_safe
        if len(chosen) == k:
            s = 0
            for v in chosen:
                s |= (1 << v)
            # safety check
            for q in b.quads:
                if (s & q) == q:
                    return
            n_safe += 1
            # b_S(p) for each empty p
            empty = full ^ s
            for p in range(V):
                if not (empty & (1 << p)):
                    continue
                bc = 0
                for q in quads_by_pt[p]:
                    t = q & ~(1 << p)
                    if (s & t) == t:
                        bc += 1
                hist[bc] += 1
                if bc > max_b:
                    max_b = bc
                    witness = {"S": [(i%n, i//n) for i in chosen], "p": (p%n, p//n), "b": bc}
            return
        for i in range(start, V):
            chosen.append(pts[i])
            rec(chosen, i + 1)
            chosen.pop()

    rec([], 0)
    dt = time.time() - t0
    print(f"  safe {k}-sets: {n_safe}, max_b={max_b}, time={dt:.1f}s", flush=True)
    print(f"  b_hist: {dict(sorted(hist.items()))}", flush=True)
    if witness:
        print(f"  witness: {witness}", flush=True)
    bound_formula = k * (k - 1) // 6  # floor(k(k-1)/6)
    print(f"  floor(k(k-1)/6)={bound_formula}, max_b<=bound? {max_b <= bound_formula}", flush=True)
    return {
        "n": n, "k": k, "V": V, "safe_k_sets": n_safe,
        "max_b": max_b, "b_hist": dict(sorted(hist.items())),
        "bound_formula": bound_formula, "bound_holds": max_b <= bound_formula,
        "witness": witness, "seconds": round(dt, 1),
    }

def b045_n5():
    """D4 stabilizer sizes for n=5 maximal safe sets."""
    t0 = time.time()
    n = 5
    b = Board(square_points(n), f"n{n}")
    V = b.V
    # D4 transforms on point ids
    def tid(x, y, op):
        if op == 0: return (x, y)          # id
        if op == 1: return (y, x)          # reflect diag
        if op == 2: return (x, n-1-y)      # reflect horiz
        if op == 3: return (n-1-x, y)      # reflect vert
        if op == 4: return (y, n-1-x)      # rot 90
        if op == 5: return (n-1-x, n-1-y)  # rot 180
        if op == 6: return (n-1-y, x)      # rot 270
        if op == 7: return (n-1-y, n-1-x)  # reflect anti-diag
        raise ValueError(op)

    def apply_d4(s):
        """Return set of 8 D4 images of bitmask s."""
        images = set()
        for op in range(8):
            t = 0
            for i in range(V):
                if s & (1 << i):
                    x, y = i % n, i // n
                    nx, ny = tid(x, y, op)
                    t |= 1 << (ny * n + nx)
            images.add(t)
        return images

    # enumerate maximal (reuse B077 approach)
    maximal = []
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

    def dfs2(occ, start):
        all_moves = [v for v in legal_moves(occ)]
        if not all_moves:
            maximal.append(occ)
            return
        for v in all_moves:
            if v >= start:
                dfs2(occ | (1 << v), v + 1)
    dfs2(0, 0)

    # stabilizer size = number of D4 ops that fix s
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

    size_stab = {}  # size -> Counter of stab sizes
    for s in maximal:
        k = bin(s).count('1')
        st = stab_size(s)
        size_stab.setdefault(k, Counter())[st] += 1

    print(f"B045 n={n}: {len(maximal)} maximal sets, {time.time()-t0:.1f}s", flush=True)
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
    results = {}
    # B072 k=5 on n=5 (fast) and n=6 (moderate)
    results["b072_n5_k5"] = b072_k5(5, 5)
    results["b072_n6_k5"] = b072_k5(6, 5)
    # B045 n=5 symmetry
    results["b045_n5"] = b045_n5()
    with open(r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round5_b001_followup.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Done.", flush=True)
