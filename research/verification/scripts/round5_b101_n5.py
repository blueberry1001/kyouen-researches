#!/usr/bin/env python3
"""Quick n=5 targeted computations."""
from __future__ import annotations
import json, struct, sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from math import gcd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, det4, square_points

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = Path(__file__).resolve().parent.parent / "round5_b101_n5.json"

def load_maximal(n):
    raw = (DATA / f"maximal_n{n}.bin").read_bytes()
    return list(struct.unpack(f"<{len(raw)//8}Q", raw))

def main():
    out = {}
    n = 5
    V = n * n
    board = Board(square_points(n))
    maximal = load_maximal(n)
    sizes = [bin(m).count("1") for m in maximal]
    smin, smax = min(sizes), max(sizes)
    mset = set(maximal)

    # --- B129 n=5: only min (4 sets) and max (100 sets) ---
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
    min_swaps = [swap_count(m) for m in min_sets]
    max_swaps = [swap_count(m) for m in max_sets]
    out["b129_n5"] = {
        "n_maximal": len(maximal), "smin": smin, "smax": smax,
        "n_min_sets": len(min_sets), "n_max_sets": len(max_sets),
        "min_swap_mean": sum(min_swaps)/max(1,len(min_swaps)),
        "min_swap_norm": (sum(min_swaps)/max(1,len(min_swaps)))/smin,
        "max_swap_mean": sum(max_swaps)/max(1,len(max_swaps)),
        "max_swap_norm": (sum(max_swaps)/max(1,len(max_swaps)))/smax,
    }
    print("B129 n=5:", out["b129_n5"])

    # --- B166/B167 n=5: max sets ---
    primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]
    b167_sizes = []
    prime_hits = {p: 0 for p in primes}
    for mask in max_sets:
        pts_idx = [i for i in range(V) if mask >> i & 1]
        pts = [(i % n, i // n) for i in pts_idx]
        dets = []
        for ids in combinations(range(len(pts)), 4):
            rows = [(pts[j][0]**2+pts[j][1]**2, pts[j][0], pts[j][1], 1) for j in ids]
            dets.append(det4(*rows))
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
    out["b166_167_n5"] = {
        "n_max_sets": len(max_sets),
        "prime_hits": prime_hits,
        "b167_sizes": {"min": min(b167_sizes), "max": max(b167_sizes), "mean": sum(b167_sizes)/len(b167_sizes)},
    }
    print("B166/167 n=5:", out["b166_167_n5"])

    # --- B157: 2-stone P/N and degree matrix features (n=5) ---
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

    deg = [0] * V
    for q in board.quads:
        for i in range(V):
            if q >> i & 1:
                deg[i] += 1

    # 2-stone positions: sum of degrees vs P/N
    # Also d(p,q) = number of forbidden quads containing both p and q
    pair_data = []
    for i, j in combinations(range(V), 2):
        mask = (1 << i) | (1 << j)
        if not board.is_safe(mask):
            continue
        g = grundy(mask)
        # d(p,q) = shared forbidden quads
        shared = sum(1 for q in board.quads if (q >> i & 1) and (q >> j & 1))
        pair_data.append({
            "deg_sum": deg[i] + deg[j],
            "shared": shared,
            "g": g,
            "pn": "P" if g == 0 else "N",
        })

    # B157: does shared/dispersion explain P/N beyond deg_sum?
    by_degsum = defaultdict(lambda: {"P": 0, "N": 0, "shared_vals": []})
    for p in pair_data:
        by_degsum[p["deg_sum"]][p["pn"]] += 1
        by_degsum[p["deg_sum"]]["shared_vals"].append(p["shared"])

    out["b157_n5"] = {
        "n_pairs": len(pair_data),
        "deg_sum_pn": {str(k): {"P": v["P"], "N": v["N"],
                                "shared_min": min(v["shared_vals"]) if v["shared_vals"] else None,
                                "shared_max": max(v["shared_vals"]) if v["shared_vals"] else None}
                       for k, v in sorted(by_degsum.items())},
    }
    print("B157 n=5: pairs=", len(pair_data))
    for k, v in list(out["b157_n5"]["deg_sum_pn"].items())[:8]:
        print(f"  deg_sum={k}: P={v['P']} N={v['N']} shared=[{v['shared_min']},{v['shared_max']}]")

    # --- B158 n=5: reversal search ---
    L_sizes = []
    for i in range(V):
        mask = 1 << i
        legal = sum(1 for v in range(V) if v != i and board.is_safe(mask | (1 << v)))
        L_sizes.append(legal)
    claim = None
    for i in range(V):
        for j in range(V):
            if deg[i] > deg[j] and L_sizes[i] > L_sizes[j]:
                claim = {"p": (i%n, i//n), "deg_p": deg[i], "L_p": L_sizes[i],
                         "q": (j%n, j//n), "deg_q": deg[j], "L_q": L_sizes[j]}
                break
        if claim:
            break
    out["b158_n5"] = {
        "deg_min": min(deg), "deg_max": max(deg),
        "L_min": min(L_sizes), "L_max": max(L_sizes),
        "claim_witness": claim,
    }
    print("B158 n=5:", out["b158_n5"])

    OUT.write_text(json.dumps(out, indent=1, default=str))
    print(f"\nWrote {OUT}")

if __name__ == "__main__":
    main()
