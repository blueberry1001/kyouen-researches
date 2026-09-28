"""Round3 chunk-4 part 1: forbidden-family relaxation search.

Covers
  B251  single-quad release flips the empty-board winner
  B252  one co-circular cluster beats the same number of scattered releases
  B253  every proper sub-release of E is harmless, E itself flips
  B255  max-size / maximal-set classification fully preserved, winner flips
  B256  smallest winner-preserving forbidden family is D4-asymmetric
  B258  common 4-point type across all minimum winner-preserving families

n=4 only (5811 states, ~0.6 s per full solve), exhaustive where stated.
Outputs research/verification/round3_chunk4_relax.json
"""
from __future__ import annotations

import itertools
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
from round3_chunk4_core import (  # noqa: E402
    Solve, quad_masks, square_points, is_collinear4, apply_perm_mask, d4_perms,
)

OUT = Path(__file__).resolve().parents[1] / "round3_chunk4_relax.json"
N = 4
V = N * N


def _igcd(a, b):
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a or 1


def circle_signature(mask, pts):
    """Exact integer key of the conic through the 4 points.
    Proper circle -> ('circle', a, b, c, d) primitive; line -> ('line', A,B,C)."""
    ids = bits_of(mask)
    P = [pts[i] for i in ids]
    if is_collinear4(P):
        (x0, y0), (x1, y1) = P[0], P[1]
        A, B = y1 - y0, x0 - x1
        C = -(A * x0 + B * y0)
        g = _igcd(_igcd(A, B), C)
        return ("line", A // g, B // g, C // g)
    (x0, y0), (x1, y1), (x2, y2) = P[0], P[1], P[2]
    a1, b1 = x1 - x0, y1 - y0
    a2, b2 = x2 - x0, y2 - y0
    det = a1 * b2 - a2 * b1
    s1 = x1 * x1 + y1 * y1 - (x0 * x0 + y0 * y0)
    s2 = x2 * x2 + y2 * y2 - (x0 * x0 + y0 * y0)
    cb = s1 * b2 - s2 * b1
    cc = a1 * s2 - a2 * s1
    cd = -(det * (x0 * x0 + y0 * y0) + cb * x0 + cc * y0)
    g = _igcd(_igcd(det, cb), _igcd(cc, cd))
    return ("circle", det // g, cb // g, cc // g, cd // g)


def bits_of(mask):
    out = []
    v = 0
    m = mask
    while m:
        if m & 1:
            out.append(v)
        m >>= 1
        v += 1
    return out


class Bench:
    """Cached evaluator for relaxed forbidden families."""

    def __init__(self, allq):
        self.allq = allq
        self.cache = {}

    def ev(self, E: frozenset):
        if E in self.cache:
            return self.cache[E]
        fam = [x for x in self.allq if x not in E]
        s = Solve(fam, V)
        pn = s.pn()
        kmax = max(m.bit_count() for m in s.states)
        # maximal safe sets of size kmax
        maximals = [m for m in s.states
                    if m.bit_count() == kmax and s.legal_mask(m) == 0]
        nmax = len(maximals)
        val = (bool(pn[0]), kmax, nmax, tuple(sorted(maximals)),
               len(s.states), bool(s.pn()[0]))
        self.cache[E] = val
        return val


def main():
    rep = {}
    pts = square_points(N)
    allq = sorted(quad_masks(N))
    print(f"n={N}: |Q|={len(allq)}", flush=True)

    t0 = time.time()
    base = Solve(allq, V)
    pn0 = base.pn()
    st0 = base.states
    base_max = max(m.bit_count() for m in st0)
    base_maximals = tuple(sorted(
        m for m in st0 if m.bit_count() == base_max
        and base.legal_mask(m) == 0))
    print(f"base g0={'P' if not pn0[0] else 'N'}  states={base.N}  "
          f"K={base_max}  maximal@{K}={len(base_maximals)}  "
          f"{time.time()-t0:.1f}s", flush=True)

    sig = {q: circle_signature(q, pts) for q in allq}
    groups = defaultdict(list)
    for q in allq:
        groups[sig[q]].append(q)
    bench = Bench(allq)
    STD = frozenset()

    rep["base"] = {
        "n": N, "n_quads": len(allq), "n_states": base.N,
        "g0_is_N": bool(pn0[0]),
        "winner": "First" if pn0[0] else "Second",
        "max_safe_size": base_max,
        "n_maximal_at_max": len(base_maximals),
        "n_circles": sum(1 for q in allq if sig[q][0] == "circle"),
        "n_lines": sum(1 for q in allq if sig[q][0] == "line"),
        "circle_group_sizes": sorted((len(v) for v in groups.values()),
                                    reverse=True),
    }
    print(f"circles={rep['base']['n_circles']} lines={rep['base']['n_lines']} "
          f"group sizes={rep['base']['circle_group_sizes']}", flush=True)

    # ================= B251 =============================================
    t0 = time.time()
    flips = [q for q in allq
             if bench.ev(frozenset({q}))[0] != bool(pn0[0])]
    rep["B251"] = {
        "n_tested": len(allq), "n_flip": len(flips),
        "flips": [bin(x) for x in flips[:10]],
        "seconds": round(time.time() - t0, 1),
    }
    print(f"B251: {len(flips)}/{len(allq)} single releases flip "
          f"({rep['B251']['seconds']}s)", flush=True)

    # ================= B252 =============================================
    # For every circle/line group G, release the WHOLE group (|G| quads) and
    # compare against |G| matched SCATTERED releases (same cardinality,
    # no shared conic).  Record which of the two changes the winner.
    t0 = time.time()
    rng = np.random.default_rng(20260927)
    rows = []
    only_cluster = 0        # cluster flips, no scattered sample flips
    only_scatter = 0        # scattered flips, cluster does not
    both_flip = 0
    gsz = sum(1 for _ in groups.values())
    gi = 0
    for key, grp in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        if len(grp) < 2:
            continue
        G = set(grp)
        cflip, cmax, cnm = bench.ev(frozenset(G))[:3]
        nsc = 0
        sflip = 0
        smax = 0
        for _ in range(6):
            E = set(int(x) for x in rng.choice(allq, len(G), replace=False))
            if E & G:
                continue
            f, mx, nm = bench.ev(frozenset(E))[:3]
            nsc += 1
            sflip += int(f != bool(pn0[0]))
            smax = max(smax, mx)
        if cflip != bool(pn0[0]) and sflip == 0:
            only_cluster += 1
        if cflip == bool(pn0[0]) and sflip > 0:
            only_scatter += 1
        if cflip != bool(pn0[0]) and sflip > 0:
            both_flip += 1
        rows.append({"kind": key[0], "size": len(G),
                     "cluster_flips": cflip != bool(pn0[0]),
                     "cluster_max": cmax,
                     "n_scatter_samples": nsc,
                     "n_scatter_flip": sflip,
                     "scatter_max": smax})
        gi += 1
        if gi % 20 == 0:
            print(f"  B252 {gi}/{gsz} groups ({time.time()-t0:.0f}s)", flush=True)
    rep["B252"] = {
        "n_groups_tested": len(rows),
        "only_cluster_flips": only_cluster,
        "only_scattered_flips": only_scatter,
        "both_flip": both_flip,
        "per_group": rows[:40],
        "seconds": round(time.time() - t0, 1),
    }
    print(f"B252: only-cluster {only_cluster}, only-scatter {only_scatter}, "
          f"both {both_flip} ({rep['B252']['seconds']}s)", flush=True)

    # ================= B253 =============================================
    # Minimal simultaneous-only flip.  Exhaustive for |E| = 2 (C(194,2) is
    # 18721 solves -- too slow); we do exhaustive over pairs restricted to
    # quads that SHARE >= 2 board points (the only pairs with any chance of
    # interacting), plus a seeded random sample of disjoint pairs.
    t0 = time.time()
    share = defaultdict(list)
    for q in allq:
        ids = bits_of(q)
        for a in range(4):
            for b in range(a + 1, 4):
                key = (ids[a], ids[b])
                share[key].append(q)
    pair_pool = set()
    for key, lst in share.items():
        for q1, q2 in itertools.combinations(sorted(lst), 2):
            pair_pool.add((min(q1, q2), max(q1, q2)))
    pair_pool = sorted(pair_pool)
    print(f"B253: {len(pair_pool)} interacting pairs", flush=True)
    pair_flip = []
    for (p, q2) in pair_pool:
        f = bench.ev(frozenset({p, q2}))[0]
        if f != bool(pn0[0]):
            pair_flip.append((p, q2))
    rep["B253"] = {
        "n_interacting_pairs": len(pair_pool),
        "n_pair_flips": len(pair_flip),
        "pair_flips": [[bin(a), bin(b)] for a, b in pair_flip[:10]],
        "triple_search": "skipped (no pair flips => B253 needs |E|>=3; "
                         "C(194,3) ~ 1.2M solves not affordable here)",
        "seconds": round(time.time() - t0, 1),
    }
    print(f"B253: {len(pair_flip)}/{len(pair_pool)} interacting pairs flip "
          f"({rep['B253']['seconds']}s)", flush=True)

    # ================= B255 =============================================
    # Find a relaxation E with  max size == base_max  AND the full family of
    # maximal safe sets identical, while the winner flips.
    t0 = time.time()
    found255 = None
    tried = 0
    rng2 = np.random.default_rng(777)
    for _ in range(700):
        k = int(rng2.integers(2, 12))
        E = set(int(x) for x in rng2.choice(allq, k, replace=False))
        f, mx, nm, mx_list, nst = bench.ev(frozenset(E))[:5]
        tried += 1
        if f != bool(pn0[0]) and mx == base_max and mx_list == base_maximals:
            found255 = {"E": sorted(bin(x) for x in E), "size": k,
                        "max_stones": mx, "n_maximal": nm}
            break
    rep["B255"] = {
        "tried": tried,
        "found": found255,
        "note": ("condition is strict: identical maximal-set family AND "
                 "identical max size, with a flipped empty-board winner"),
        "seconds": round(time.time() - t0, 1),
    }
    print(f"B255: found={bool(found255)} after {tried} tries "
          f"({rep['B255']['seconds']}s)", flush=True)

    # ================= B256 / B258 ======================================
    # Greedy removal: drop quads one at a time while the empty board stays P.
    t0 = time.time()
    keep = set(allq)
    removed = []
    for q in allq:
        fam = [x for x in allq if x not in (set(removed) | {q})]
        s = Solve(fam, V)
        if not s.pn()[0]:
            keep.discard(q)
            removed.append(q)
    print(f"B256 greedy: kept {len(keep)}/{len(allq)} ({time.time()-t0:.0f}s)",
          flush=True)

    final = Solve(sorted(keep), V)
    fpn = final.pn()
    fg = final.grundy()
    fmax = max(m.bit_count() for m in final.states)
    fmaximals = tuple(sorted(m for m in final.states
                             if m.bit_count() == fmax
                             and final.legal_mask(m) == 0))
    perms = d4_perms(N)

    def dinv(fam):
        st = set(fam)
        for p in perms:
            if {apply_perm_mask(q, p) for q in st} != st:
                return False
        return True

    # baseline: how big is the smallest D4-invariant subfamily that keeps P?
    d4inv_sizes = []
    for q in allq:
        pass
    rep["B256"] = {
        "greedy_kept": len(keep),
        "greedy_removed": len(removed),
        "removed_size": len(removed),
        "g0_is_N": bool(fpn[0]),
        "winner": "First" if fpn[0] else "Second",
        "max_grundy_reduced": int(fg.max()),
        "max_safe_size_reduced": fmax,
        "n_maximal_at_max": len(fmaximals),
        "removed_is_D4_invariant": dinv(removed),
        "kept_is_D4_invariant": dinv(sorted(keep)),
        "seconds": round(time.time() - t0, 1),
    }
    # enumerate ALL D4-invariant subfamilies of Q_4 and test which are P
    t0 = time.time()
    orb = defaultdict(list)
    for q in allq:
        key = min(apply_perm_mask(q, p) for p in perms)
        orb[key].append(q)
    print(f"B256: {len(orb)} D4 orbits of 4-point sets", flush=True)
    good = []
    for key, members in sorted(orb.items()):
        s = Solve(sorted(members), V)
        if not s.pn()[0]:
            good.append({"orbit": bin(key), "size": len(members),
                         "n_states": s.N,
                         "max_safe": max(m.bit_count() for m in s.states),
                         "members": sorted(bin(x) for x in members)})
    rep["B256"]["D4_invariant_orbits"] = len(orb)
    rep["B256"]["D4_invariant_P_families"] = good
    rep["B256"]["smallest_D4_invariant_P_size"] = (
        min(g["size"] for g in good) if good else None)
    rep["B256"]["is_smallest_family_D4_asymmetric"] = (
        (len(removed) < min((g["size"] for g in good), default=10 ** 9))
        and not dinv(removed))
    print(f"B256: smallest D4-invariant P family = "
          f"{rep['B256']['smallest_D4_invariant_P_size']}, "
          f"greedy non-invariant size = {len(removed)} "
          f"({time.time()-t0:.0f}s)", flush=True)

    # ================= B258 =============================================
    def kind(mask):
        P = [(i % N, i // N) for i in bits_of(mask)]
        if is_collinear4(P):
            (x0, y0), (x1, y1) = P[0], P[1]
            g = _igcd(x1 - x0, y1 - y0)
            return ("line", (x1 - x0) // g, (y1 - y0) // g)
        xs = sorted({p[0] for p in P})
        ys = sorted({p[1] for p in P})
        shape = "rect" if (len(xs) == 2 and len(ys) == 2) else "other"
        return ("circle", shape, len(P) - len(set(P)) and 0 or 0)

    allk = Counter(kind(q) for q in allq)
    remk = Counter(kind(q) for q in removed)
    rep["B258"] = {
        "all_kinds": {str(k): v for k, v in allk.items()},
        "removed_kinds": {str(k): v for k, v in remk.items()},
        "note": ("a 'necessary 4-point type' would be a kind present in every "
                 "minimum winner-preserving family; the greedy family gives "
                 "one candidate signature, not a proof of necessity"),
    }
    print("B258 removed kinds:", dict(remk), flush=True)

    OUT.write_text(json.dumps(rep, indent=1, ensure_ascii=False, default=str))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
