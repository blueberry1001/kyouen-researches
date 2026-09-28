#!/usr/bin/env python3
"""round3 chunk2 / B103,B104,B106,B107,B110 : shape of maximum safe sets.

New vs batch-06:
 * B103: row-occupancy histograms for n=4,5,6,7 with the *statistic* the
   hypothesis actually names (fraction of rows with occupancy in {0,1,3}),
   plus a sign test on the n=4..7 trend.
 * B104: exhaustive D4-orbit never-used test on ALL max sets of n=4,5,6,7
   (not just n=6,7) and, for n=8, on the committed n=8 max-set sample.
 * B106/B107: min_det (minimum number of points that identifies a max set)
   for n=4,5,6,7 by exact subset search, plus identification-complexity
   curve: for each c = 1..5, how many max sets share a given c-subset.
 * B110: circle/line capacity cover of the forbidden quads of n=7,8 -- how
   many of the C(k,4) quads of a "few circles/lines" family are needed to
   certify K_n.  We build the family from all lines with >=4 pts and all
   circles with >=4 pts, greedily choose the ones covering the most
   un-covered quads, and measure the residual (uncertified) quad count.
"""
from __future__ import annotations

import json
import math
import random
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from round3_chunk2_geom import (  # noqa: E402
    DATA, NIGHT, apply_perm, bitl, circ, d4_perms, load_bin, quad_masks,
    square_pts,
)

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round3_chunk2_shape.json"


def save(rep):
    OUT.write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")


def maxsets(n):
    if n == 4:
        return load_bin(DATA / "maximal_n4.bin")
    if n == 5:
        return load_bin(DATA / "maximal_n5.bin")
    if n == 6:
        return load_bin(NIGHT / "maxsafe_n6_K11.bin")
    if n == 7:
        return load_bin(NIGHT / "maxsafe_n7_K14.bin")
    raise ValueError(n)


# ------------------------------------------------------------------ B103
def b103(rep):
    print("=== B103: row occupancy of maximum sets ===", flush=True)
    rep["b103"] = {}
    rows_by_n = {}
    for n in (4, 5, 6, 7):
        ms = maxsets(n)
        # only the maximum-size ones
        K = max(m.bit_count() for m in ms)
        top = [m for m in ms if m.bit_count() == K]
        occ = Counter()
        for m in top:
            for y in range(n):
                c = sum(1 for p in bitl(m) if p // n == y)
                occ[c] += 1
        tot = len(top) * n
        frac2 = occ[2] / tot
        frac013 = (occ[0] + occ[1] + occ[3]) / tot
        rows_by_n[n] = {"K": K, "n_maxsets": len(top),
                        "occ_hist": dict(sorted(occ.items())),
                        "frac2": frac2, "frac013": frac013}
        print(f"  n={n}: K={K} n={len(top)} occ={dict(sorted(occ.items()))} "
              f"frac2={frac2:.4f} frac(0,1,3)={frac013:.4f}", flush=True)
    ns = sorted(rows_by_n)
    vals = [rows_by_n[n]["frac013"] for n in ns]
    # exact monotone-decrease test
    mono = all(vals[i] >= vals[i + 1] for i in range(len(vals) - 1))
    rep["b103"]["per_n"] = rows_by_n
    rep["b103"]["frac013_series"] = dict(zip(ns, vals))
    rep["b103"]["monotone_decreasing"] = mono
    rep["b103"]["spectrum_of_occ"] = {
        n: sorted(rows_by_n[n]["occ_hist"]) for n in ns}
    print(f"  frac(0,1,3) series {vals} monotone-decreasing={mono}", flush=True)
    save(rep)


# ------------------------------------------------------------------ B104
def b104(rep):
    print("\n=== B104: never-used D4 orbits in maximum sets ===", flush=True)
    rep["b104"] = {}
    for n in (4, 5, 6, 7):
        ms = maxsets(n)
        K = max(m.bit_count() for m in ms)
        top = [m for m in ms if m.bit_count() == K]
        used = Counter()
        for m in top:
            for p in bitl(m):
                used[p] += 1
        perms = d4_perms(n)
        orb = defaultdict(list)
        for p in range(n * n):
            img = [bitl(apply_perm(1 << p, pp))[0] for pp in perms]
            orb[min(img)].append(p)
        never = []
        for k, pts in sorted(orb.items()):
            if all(used[p] == 0 for p in pts):
                never.append({"orbit_key": k, "pts": sorted(pts),
                              "coords": sorted((p % n, p // n) for p in pts),
                              "size": len(pts)})
        rep["b104"][n] = {
            "K": K, "n_maxsets": len(top), "n_orbits": len(orb),
            "n_never_used_orbits": len(never), "never_used": never,
            "n_never_used_points": sum(z["size"] for z in never),
            "usage_min": min(used[p] for p in range(n * n)),
        }
        print(f"  n={n}: K={K} orbits={len(orb)} "
              f"never-used orbits={len(never)} pts={rep['b104'][n]['n_never_used_points']} "
              f"{[z['coords'] for z in never]}", flush=True)
    save(rep)


# -------------------------------------------------------------- B106/B107
def min_det_family(sets, n, maxc=5):
    """min |C| such that some C subset of S lies in no other max set."""
    out = []
    for c in range(1, maxc + 1):
        # map subset -> number of max sets containing it
        pass
    # build subset index for c=1..maxc with early stop
    results = {}
    for c in range(1, maxc + 1):
        idx = Counter()
        for S in sets:
            for sub in combinations(bitl(S), c):
                idx[sub] += 1
        # for each S, min c-subset with idx==1
        best = {}
        for S in sets:
            m = None
            for sub in combinations(bitl(S), c):
                if idx[sub] == 1:
                    m = sub
                    break
            best[S] = m
        results[c] = {
            "n_subsets": len(idx),
            "n_unique_subsets": sum(1 for v in idx.values() if v == 1),
            "frac_unique": sum(1 for v in idx.values() if v == 1) / max(1, len(idx)),
            "n_sets_with_unique_csubset": sum(1 for v in best.values() if v),
            "examples": [list(v) for v in list(best.values())[:3] if v],
        }
        print(f"    c={c}: {results[c]['n_unique_subsets']}/{len(idx)} subsets "
              f"unique ({results[c]['frac_unique']:.4f}); sets with a unique "
              f"c-subset: {results[c]['n_sets_with_unique_csubset']}/{len(sets)}",
              flush=True)
    return results


def b106_b107(rep):
    print("\n=== B106/B107: identification number of max sets ===", flush=True)
    rep["b106_b107"] = {}
    for n in (4, 5, 6, 7):
        ms = maxsets(n)
        K = max(m.bit_count() for m in ms)
        top = [m for m in ms if m.bit_count() == K]
        r = min_det_family(top, n, maxc=5)
        rep["b106_b107"][n] = {"K": K, "n_maxsets": len(top), "by_c": r}
        print(f"  n={n} K={K} n_max={len(top)}", flush=True)
        save(rep)


# ------------------------------------------------------------------ B110
def b110(rep):
    print("\n=== B110: capacity-inequality cover of the forbidden quads ===",
          flush=True)
    rep["b110"] = {}
    for n in (6, 7, 8):
        pts = square_pts(n)
        V = n * n
        # lines with >=4 board points
        lines = defaultdict(list)
        seen = set()
        for i in range(V):
            x1, y1 = pts[i]
            for j in range(i + 1, V):
                x2, y2 = pts[j]
                dx, dy = x2 - x1, y2 - y1
                g = math.gcd(abs(dx), abs(dy))
                dx, dy = dx // g, dy // g
                if dx < 0 or (dx == 0 and dy < 0):
                    dx, dy = -dx, -dy
                key = (dx, dy, dx * y1 - dy * x1)
                if key in seen:
                    continue
                seen.add(key)
                mem = [p for p, (x, y) in enumerate(pts) if dx * y - dy * x == key[2]]
                if len(mem) >= 4:
                    lines[key] = mem
        # circles with >=4 board points: enumerate via circumcentres of triples
        circs = {}
        for i in range(V):
            for j in range(i + 1, V):
                for k in range(j + 1, V):
                    c = circ(pts, pts[i], pts[j], pts[k])
                    if c is None or c in circs:
                        continue
                    q, cx, cy, rho = c
                    mem = [p for p, (x, y) in enumerate(pts)
                           if (q * x - cx) ** 2 + (q * y - cy) ** 2 == rho]
                    if len(mem) >= 4:
                        circs[c] = mem
        # all forbidden quads
        quads = set()
        for mem in list(lines.values()) + list(circs.values()):
            for comb in combinations(mem, 4):
                quads.add(comb)
        # each line/circle certifies its C(k,4) quads
        cert = {}
        for key, mem in list(lines.items()) + list(circs.items()):
            qs = set(combinations(mem, 4))
            cert[(key if isinstance(key, tuple) and len(key) == 4 else key)] = qs
        families = [((("L",) + k), v) for k, v in lines.items()]
        families += [((("C",) + str(k)), v) for k, v in circs.items()]
        # greedy set cover over quads
        target = set(quads)
        chosen = []
        pool = list(families)
        covered = set()
        while True:
            best = None
            bestc = 0
            for f, qs in pool:
                c = len(qs - covered)
                if c > bestc:
                    best, bestc = (f, qs), c
            if bestc == 0:
                break
            chosen.append(best[0])
            covered |= best[1]
            pool.remove(best)
        rep["b110"][n] = {
            "n_lines_ge4": len(lines), "n_circles_ge4": len(circs),
            "n_quads": len(quads),
            "n_families": len(families),
            "n_greedy_families_to_cover": len(chosen),
            "n_uncov": len(target - covered),
            "coverage_frac": len(covered) / max(1, len(quads)),
            "chosen": [list(map(str, f)) for f in chosen[:20]],
            "line_quad_frac": None,
        }
        lq = set()
        for mem in lines.values():
            lq |= set(combinations(mem, 4))
        rep["b110"][n]["line_quad_frac"] = len(lq) / max(1, len(quads))
        print(f"  n={n}: quads={len(quads)} lines={len(lines)} circles={len(circs)} "
              f"greedy families={len(chosen)} residual={len(target - covered)}",
              flush=True)
        save(rep)


def main():
    rep = {}
    b103(rep)
    b104(rep)
    b106_b107(rep)
    b110(rep)
    print("\nWrote", OUT)


if __name__ == "__main__":
    main()
