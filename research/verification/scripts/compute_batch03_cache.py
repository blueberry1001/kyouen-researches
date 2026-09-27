#!/usr/bin/env python3
"""Batch-03 residual cache builder.

Enumerates all reachable safe sets for n<=5, computes for each:
  g(S), L(S), R(S) features, P(S) size, component counts, D4 stabilizer,
  raw (pre-minimization) residual counts, R-isomorphism canonical hash.
Saves a pickle consumed by the batch-03 hypothesis tests.

Also enumerates maximal safe sets and Aut(Q_n) witnesses.
"""
from __future__ import annotations

import pickle
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from residual_core import (
    BoardN,
    bits_of,
    d4_perms,
    apply_perm_mask,
    hyper_canonical,
    to_abs_edges,
)

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "batch03_cache.pkl"


def fast_legal_and_candidates(quads: list[int], empty: int, occ: int):
    """One pass over quads: return (L_mask, raw_residual_candidates)."""
    Lbad = 0
    cands = []
    for q in quads:
        rest = q & empty
        if not rest:
            continue
        if rest & (rest - 1) == 0:
            # exactly one missing point -> that point is illegal
            Lbad |= rest
        else:
            cands.append(rest)
    L = empty & ~Lbad
    # keep candidates whose unoccupied part is fully legal
    res = []
    for r in cands:
        if r & ~L == 0:
            res.append(r)
    return L, res


def minimize(cands: list[int]) -> list[int]:
    cs = set(cands)
    out = []
    for r in cands:
        ok = True
        x = r
        while True:
            x = (x - 1) & r
            if x == 0:
                break
            if x in cs:
                ok = False
                break
        if ok:
            out.append(r)
    return out


def raw_counts(cands: list[int]) -> tuple[int, int, int]:
    c2 = c3 = c4 = 0
    for r in cands:
        k = r.bit_count()
        if k == 2:
            c2 += 1
        elif k == 3:
            c3 += 1
        else:
            c4 += 1
    return c2, c3, c4


def min_counts(R: list[int]) -> tuple[int, int, int]:
    return raw_counts(R)


def hyper_comp_count(L: int, R: list[int]) -> int:
    if L == 0:
        return 0
    parent = list(range(L.bit_length()))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for r in R:
        pts = bits_of(r)
        for i in range(1, len(pts)):
            union(pts[0], pts[i])
    roots = set()
    for v in bits_of(L):
        roots.add(find(v))
    return len(roots)


def grid_comp_count(n: int, L: int) -> int:
    if L == 0:
        return 0
    seen = 0
    comps = 0
    for s in bits_of(L):
        if (seen >> s) & 1:
            continue
        comps += 1
        stack = [s]
        seen |= 1 << s
        while stack:
            u = stack.pop()
            x, y = u % n, u // n
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                xx, yy = x + dx, y + dy
                if 0 <= xx < n and 0 <= yy < n:
                    v = yy * n + xx
                    if ((L >> v) & 1) and not ((seen >> v) & 1):
                        seen |= 1 << v
                        stack.append(v)
    return comps


def analyze_board(n: int) -> dict:
    t0 = time.time()
    board = BoardN(n)
    quads = board.quads
    full = board.full
    perms = d4_perms(n)

    # --- reachable sets via DFS + grundy retrograde ---
    memo_g: dict[int, int] = {}
    features: dict[int, dict] = {}

    sys.setrecursionlimit(100000)

    def ev(occ: int) -> int:
        hit = memo_g.get(occ)
        if hit is not None:
            return hit
        empty = full ^ occ
        L, cands = fast_legal_and_candidates(quads, empty, occ)
        if L == 0:
            memo_g[occ] = 0
            return 0
        seen = set()
        moves = bits_of(L)
        for u in moves:
            seen.add(ev(occ | (1 << u)))
        g = 0
        while g in seen:
            g += 1
        memo_g[occ] = g
        return g

    ev(0)
    print(f"[n={n}] grundy done: {len(memo_g)} positions ({time.time()-t0:.1f}s)", flush=True)

    # --- features for every reachable position ---
    stab_cache: dict[int, int] = {}
    recs = []
    maximal = []
    for idx, (occ, g) in enumerate(memo_g.items()):
        empty = full ^ occ
        L, cands = fast_legal_and_candidates(quads, empty, occ)
        R = minimize(cands)
        c2r, c3r, c4r = raw_counts(cands)
        c2, c3, c4 = min_counts(R)
        nh = hyper_comp_count(L, R)
        ng = grid_comp_count(n, L)
        stab = stab_cache.get(occ)
        if stab is None:
            stab = sum(1 for p in perms if apply_perm_mask(occ, p) == occ)
            stab_cache[occ] = stab
        # cheap iso signature; full canonical only if needed later
        rec = {
            "occ": occ,
            "k": occ.bit_count(),
            "g": g,
            "L": L,
            "R": tuple(R),
            "Rhash": hash(tuple(R)),
            "raw": (c2r, c3r, c4r),
            "cnt": (c2, c3, c4),
            "nh": nh,
            "ng": ng,
            "stab": stab,
            "nL": L.bit_count(),
        }
        recs.append(rec)
        if L == 0:
            maximal.append(rec)
        if (idx + 1) % 30000 == 0:
            print(f"  ... {idx+1}/{len(memo_g)} ({time.time()-t0:.1f}s)", flush=True)

    print(f"[n={n}] features done: {len(recs)} recs, {len(maximal)} maximal ({time.time()-t0:.1f}s)", flush=True)

    # maximal size histogram + stabilizer
    hist = defaultdict(int)
    stab_hist = defaultdict(lambda: defaultdict(int))
    for mrec in maximal:
        hist[mrec["k"]] += 1
        stab_hist[mrec["k"]][mrec["stab"]] += 1

    return {
        "n": n,
        "n_quads": len(quads),
        "n_reachable": len(recs),
        "empty_g": memo_g[0],
        "max_g": max(memo_g.values()),
        "recs": recs,
        "maximal_size_hist": dict(hist),
        "maximal_stab_hist": {k: dict(v) for k, v in stab_hist.items()},
        "elapsed": time.time() - t0,
    }


def aut_qn(n: int) -> dict:
    board = BoardN(n)
    edges = [frozenset(bits_of(q)) for q in board.quads]
    eset = set(edges)
    from residual_core import hyper_automorphisms

    auts = hyper_automorphisms(board.V, edges, limit=50000)
    d4 = set(tuple(p) for p in d4_perms(n))
    autset = set(auts)
    return {
        "n": n,
        "V": board.V,
        "n_edges": len(edges),
        "aut_size": len(auts),
        "d4_subset": d4 <= autset,
        "n_extras": len(autset - d4),
    }


def main() -> None:
    t0 = time.time()
    data = {"aut_qn": {}}
    for n in range(2, 6):
        print(f"=== Aut(Q_{n}) ===", flush=True)
        data["aut_qn"][n] = aut_qn(n)
        print(data["aut_qn"][n], flush=True)
    for n in range(2, 6):
        print(f"=== board n={n} ===", flush=True)
        data[n] = analyze_board(n)
        print(
            f"  reachable={data[n]['n_reachable']} empty_g={data[n]['empty_g']} "
            f"max_g={data[n]['max_g']} maximal_hist={data[n]['maximal_size_hist']}",
            flush=True,
        )
    OUT.write_bytes(pickle.dumps(data, protocol=4))
    print(f"saved {OUT} ({OUT.stat().st_size} bytes) total {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
