#!/usr/bin/env python3
"""Quick targeted computations for NOT-CHECKED IDs. n=4 only (fast)."""
from __future__ import annotations
import json, struct, sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from math import gcd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, det4, square_points

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = Path(__file__).resolve().parent.parent / "round5_b101_quick.json"

def load_maximal(n):
    raw = (DATA / f"maximal_n{n}.bin").read_bytes()
    return list(struct.unpack(f"<{len(raw)//8}Q", raw))

def main():
    out = {}
    n = 4
    V = n * n
    board = Board(square_points(n))
    maximal = load_maximal(n)
    sizes = [bin(m).count("1") for m in maximal]
    smin, smax = min(sizes), max(sizes)
    mset = set(maximal)

    # --- B129: 1-swap mobility ---
    def swap_count(mask):
        c = 0
        occ = [i for i in range(V) if mask >> i & 1]
        emp = [i for i in range(V) if not (mask >> i & 1)]
        for p in occ:
            base = mask ^ (1 << p)
            for q in emp:
                if base | (1 << q) in mset:
                    c += 1
        return c

    min_sets = [m for m, s in zip(maximal, sizes) if s == smin]
    max_sets = [m for m, s in zip(maximal, sizes) if s == smax]
    min_swaps = [swap_count(m) for m in min_sets]  # 176 for n=4
    max_swaps = [swap_count(m) for m in max_sets]  # 64 for n=4
    out["b129_n4"] = {
        "n_maximal": len(maximal), "smin": smin, "smax": smax,
        "n_min_sets": len(min_sets), "n_max_sets": len(max_sets),
        "min_swap_mean": sum(min_swaps)/len(min_swaps),
        "min_swap_norm": (sum(min_swaps)/len(min_swaps))/smin,
        "max_swap_mean": sum(max_swaps)/len(max_swaps),
        "max_swap_norm": (sum(max_swaps)/len(max_swaps))/smax,
        "min_swap_hist": dict(Counter(min_swaps)),
        "max_swap_hist": dict(Counter(max_swaps)),
    }
    print("B129 n=4:", out["b129_n4"])

    # --- B130: P/N vs components at k=3,4 for n=4 ---
    from functools import lru_cache
    @lru_cache(maxsize=None)
    def grundy(mask):
        moves = []
        empty = board.full ^ mask
        v = 0
        while empty:
            if empty & 1:
                bit = 1 << v
                if board.is_safe(mask | bit):
                    moves.append(grundy(mask | bit))
            empty >>= 1
            v += 1
        if not moves:
            return 0
        s = set(moves)
        g = 0
        while g in s:
            g += 1
        return g

    for k in [3, 4]:
        safe_k = [m for m in range(1 << V) if bin(m).count("1") == k and board.is_safe(m)]
        index = {m: i for i, m in enumerate(safe_k)}
        parent = list(range(len(safe_k)))
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra
        for m in safe_k:
            occ = [i for i in range(V) if m >> i & 1]
            emp = [i for i in range(V) if not (m >> i & 1)]
            for p in occ:
                base = m ^ (1 << p)
                for q in emp:
                    nb = base | (1 << q)
                    if nb in index:
                        union(index[m], index[nb])
        comp_pn = defaultdict(set)
        comp_size = Counter()
        for m in safe_k:
            g = grundy(m)
            r = find(index[m])
            comp_pn[r].add(g == 0)
            comp_size[r] += 1
        mixed = sum(1 for s in comp_pn.values() if len(s) > 1)
        out[f"b130_n4k{k}"] = {
            "n_safe_k": len(safe_k), "n_components": len(comp_size),
            "n_mixed_components": mixed,
            "n_pure_components": sum(1 for s in comp_pn.values() if len(s) == 1),
            "largest_component": max(comp_size.values()) if comp_size else 0,
        }
        print(f"B130 n=4 k={k}:", out[f"b130_n4k{k}"])

    # --- B158/B160: degree vs L-size, same-degree different outcome ---
    deg = [0] * V
    for q in board.quads:
        for i in range(V):
            if q >> i & 1:
                deg[i] += 1
    L_sizes = []
    for i in range(V):
        mask = 1 << i
        legal = sum(1 for v in range(V) if v != i and board.is_safe(mask | (1 << v)))
        L_sizes.append(legal)

    # B158 claim: d(p)>d(q) but L(p)>L(q)
    claim = None
    for i in range(V):
        for j in range(V):
            if deg[i] > deg[j] and L_sizes[i] > L_sizes[j]:
                claim = {"p": (i%n, i//n), "deg_p": deg[i], "L_p": L_sizes[i],
                         "q": (j%n, j//n), "deg_q": deg[j], "L_q": L_sizes[j]}
                break
        if claim:
            break

    # B160: same-degree D4-inequivalent different g
    def d4_orbit(x, y):
        n1 = n - 1
        return {(x,y),(y,n1-x),(n1-x,n1-y),(n1-y,x),(n1-x,y),(n1-y,n1-x),(x,n1-y),(y,x)}

    b160 = None
    pt_g = {i: grundy(1 << i) for i in range(V)}
    by_deg = defaultdict(list)
    for i in range(V):
        by_deg[deg[i]].append(i)
    for d, pts in by_deg.items():
        orbit_gs = {}
        for i in pts:
            orb = frozenset(d4_orbit(i % n, i // n))
            orbit_gs.setdefault(orb, set()).add(pt_g[i])
        all_g = set()
        for gs in orbit_gs.values():
            all_g |= gs
        if len(all_g) > 1:
            orbits = list(orbit_gs.keys())
            for o1, o2 in combinations(orbits, 2):
                g1 = list(orbit_gs[o1])[0]
                g2 = list(orbit_gs[o2])[0]
                if g1 != g2:
                    p1 = next(i for i in pts if frozenset(d4_orbit(i%n, i//n)) == o1)
                    p2 = next(i for i in pts if frozenset(d4_orbit(i%n, i//n)) == o2)
                    b160 = {"deg": d, "p1": (p1%n, p1//n), "g1": g1,
                            "p2": (p2%n, p2//n), "g2": g2}
                    break
            if b160:
                break

    out["b158_b160_n4"] = {
        "deg_hist": dict(Counter(deg)),
        "L_hist": dict(Counter(L_sizes)),
        "b158_claim_witness": claim,
        "b160_witness": b160,
        "first_move_g": {str((i%n, i//n)): pt_g[i] for i in range(V)},
    }
    print("B158/160 n=4: claim=", claim, "b160=", b160)

    # --- B165/166/167: mod p on n=4 max sets ---
    primes = [2, 3, 5, 7, 11, 13, 17, 19]
    max_sets = [m for m, s in zip(maximal, sizes) if s == smax]
    b167_sizes = []
    prime_hits = {p: 0 for p in primes}
    for mask in max_sets:
        pts_idx = [i for i in range(V) if mask >> i & 1]
        pts = [(i % n, i // n) for i in pts_idx]
        dets = []
        for ids in combinations(range(len(pts)), 4):
            rows = [(pts[j][0]**2+pts[j][1]**2, pts[j][0], pts[j][1], 1) for j in ids]
            d = det4(*rows)
            dets.append(d)
        covering = set()
        for d in dets:
            for p in primes:
                if d % p != 0:
                    covering.add(p)
        b167_sizes.append(len(covering))
        for p in primes:
            if all(d % p != 0 for d in dets):
                prime_hits[p] += 1
                break

    # B165: parabola construction
    b165 = {}
    for p in [3, 5, 7]:
        pts = [(i, (i*i) % p) for i in range(p)]
        safe = all(det4(*[(pts[j][0]**2+pts[j][1]**2, pts[j][0], pts[j][1], 1) for j in ids]) != 0
                   for ids in combinations(range(p), 4))
        b165[f"parabola_p{p}"] = {"n_points": p, "safe": safe, "points": pts}

    out["b165_166_167_n4"] = {
        "n_max_sets": len(max_sets),
        "prime_hits": prime_hits,
        "b167_covering_sizes": {"min": min(b167_sizes), "max": max(b167_sizes),
                                "hist": dict(Counter(b167_sizes))},
        "b165_trials": b165,
    }
    print("B165/166/167 n=4:", out["b165_166_167_n4"])

    # --- B177: same f-vector different game value (n=4 remove-one) ---
    @lru_cache(maxsize=None)
    def sub_grundy(keep_mask):
        kept = [i for i in range(V) if keep_mask >> i & 1]
        sub_pts = [(i % n, i // n) for i in kept]
        sub = Board(sub_pts)
        @lru_cache(maxsize=None)
        def sg(mask):
            moves = []
            empty = ((1 << sub.V) - 1) ^ mask
            v = 0
            while empty:
                if empty & 1:
                    bit = 1 << v
                    if sub.is_safe(mask | bit):
                        moves.append(sg(mask | bit))
                empty >>= 1
                v += 1
            if not moves:
                return 0
            s = set(moves)
            g = 0
            while g in s:
                g += 1
            return g
        return sg(0)

    def fv(keep_mask):
        kept = [i for i in range(V) if keep_mask >> i & 1]
        sub_pts = [(i % n, i // n) for i in kept]
        sub = Board(sub_pts)
        c = Counter()
        for m in range(1 << sub.V):
            if sub.is_safe(m):
                c[bin(m).count("1")] += 1
        return tuple(sorted(c.items()))

    seen = {}
    witness = None
    for rm in range(V):
        keep = board.full ^ (1 << rm)
        f = fv(keep)
        g = sub_grundy(keep)
        if f in seen:
            if seen[f][1] != g:
                witness = {"sub1_rm": seen[f][0], "g1": seen[f][1],
                           "sub2_rm": (rm % n, rm // n), "g2": g, "fv": str(f)[:120]}
                break
        else:
            seen[f] = ((rm % n, rm // n), g)

    out["b177_n4"] = {"witness": witness, "n_distinct_fv": len(seen),
                       "n_examined": V}
    print("B177 n=4:", out["b177_n4"])

    # --- B133: circle hierarchy by q (n=4,5) ---
    for n2 in [4, 5]:
        pts = square_points(n2)
        seen_c = set()
        by_q = Counter()
        max_by_q = defaultdict(int)
        for tri in combinations(range(len(pts)), 3):
            p0, p1, p2 = pts[tri[0]], pts[tri[1]], pts[tri[2]]
            ax, ay = p0; bx, by = p1; cx, cy = p2
            d = 2 * (ax*(by-cy) + bx*(cy-ay) + cx*(ay-by))
            if d == 0:
                continue
            ux = ((ax*ax+ay*ay)*(by-cy) + (bx*bx+by*by)*(cy-ay) + (cx*cx+cy*cy)*(ay-by))
            uy = ((ax*ax+ay*ay)*(cx-bx) + (bx*bx+by*by)*(ax-cx) + (cx*cx+cy*cy)*(bx-ax))
            g_all = gcd(gcd(abs(ux), abs(uy)), abs(d))
            q = abs(d) // g_all if g_all else abs(d)
            key = (ux, uy, d)
            if key in seen_c:
                continue
            seen_c.add(key)
            r2 = (ax*d - ux)**2 + (ay*d - uy)**2
            cnt = sum(1 for (x, y) in pts if (x*d - ux)**2 + (y*d - uy)**2 == r2)
            if cnt >= 3:
                by_q[q] += 1
                max_by_q[q] = max(max_by_q[q], cnt)
        out[f"b133_n{n2}"] = {
            "n_circles_ge3": sum(by_q.values()),
            "by_q_count": dict(sorted(by_q.items())),
            "max_pts_by_q": dict(sorted(max_by_q.items())),
            "global_max": max(max_by_q.values()) if max_by_q else 0,
        }
        print(f"B133 n={n2}:", out[f"b133_n{n2}"])

    # --- B159: boundary effect (degree profile n=4,5) ---
    for n2 in [4, 5]:
        board2 = Board(square_points(n2))
        V2 = n2 * n2
        deg2 = [0] * V2
        for q in board2.quads:
            for i in range(V2):
                if q >> i & 1:
                    deg2[i] += 1
        rad = defaultdict(list)
        for i in range(V2):
            x, y = i % n2, i // n2
            cx, cy = (n2-1)/2, (n2-1)/2
            r2 = round((x-cx)**2 + (y-cy)**2, 4)
            rad[r2].append(deg2[i])
        out[f"b159_n{n2}"] = {
            "deg_min": min(deg2), "deg_max": max(deg2),
            "radial": {str(k): {"min": min(v), "max": max(v), "mean": sum(v)/len(v)} for k, v in sorted(rad.items())},
        }
        print(f"B159 n={n2}: deg[{min(deg2)},{max(deg2)}]")

    OUT.write_text(json.dumps(out, indent=1, default=str))
    print(f"\nWrote {OUT}")

if __name__ == "__main__":
    main()
