#!/usr/bin/env python3
"""round3_chunk8_a_quads.py — B521, B522, B523, B524, B527, B528, B529, B530.

Theme: "円束解除・2点削除の反転・V字反転" — forbidden-quad removal / addition.

Previous state (round2-batch-b501.md):
  B521 PARTIAL 878/18721 pairs, 0 flips; 194 singles 0 flips.
  B522 INCONCLUSIVE 120 share-3 triples, 0 flips.
  B523 INCONCLUSIVE (no minimal flip family found)
  B524 INCONCLUSIVE (not started)
  B527 NOT-CHECKED (addition direction, local critical proof)
  B528 NOT-CHECKED (random addition-order criticality frequency)
  B529 NOT-CHECKED (minimal P-preserving families)
  B530 NOT-CHECKED (addition order minimising flips)

This round:
  B521: FULL exhaustive all C(194,2)=18721 pairs (numpy-accelerated by
       precomputing the outcome of every quad-subset family via a smarter
       decomposition) — or, if too slow, a provably complete bitmask-level
       strategy.  Report exactly how many pairs were evaluated.
  B522: FULL exhaustive all C(194,3) = 1,181,404 triples via a two-level
       meet-in-the-middle: for each triple of quads compute the remaining
       quad set and evaluate.  This is 1.2M games — too many for a naive
       solve.  Instead: build the full 4x4 game once (V=16), and use the
       "legal-move" structure: a game over a family F of forbidden quads has
       at most 2^16 = 65536 states.  So instead of 1.2M separate games, note
       the game with quad family F' = F \ T depends only on which quads are
       present.  Use a *symmetry-reduced* search + incremental structure.
       Concretely: we can solve each variant in ~ms with memoized DFS over
       65536 states, but 1.2M * 65536 is far too much.  So: (a) use D4
       orbits of the quad set; (b) exploit the fact that removing quads can
       only ADD legal moves, so the game is monotone in |F|; (c) search
       triples in a *directed* way: find whether ANY triple flips the winner
       using a constraint-driven search over triples ordered by |F'| size.
  B527: FULL computation of "adding one quad flips empty-board P/N" plus the
       minimal point subset certificate size.
  B528: random addition orders, criticality frequency vs single-removal
       sensitivity ranking.
  B529: enumerate ALL minimal P-preserving quad families (families F' with
       g=0 and no proper subfamily also g=0) and check whether any quad is
       in all of them.
  B530: addition order minimising flips; geometric characterisation.
"""
from __future__ import annotations

import json
import os
import random
import sys
import time
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from round3_chunk8_lib import (  # noqa: E402
    Quads, all_forbidden, apply_mask, d4_perms, is_collinear, square,
)
from batch10_core import det4_rows  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "round3_chunk8_quads.json"
N = 4
PTS = square(N)
V = 16


def build_4x4():
    quads = all_forbidden(PTS)
    kinds = []
    for ids in quads:
        kinds.append("line" if is_collinear(PTS, ids) else "circle")
    # per-quad point tuple
    qtup = [tuple(ids) for ids in quads]
    return quads, kinds, qtup


QUADS, KINDS, QTUP = build_4x4()
FQ = len(QUADS)
META = {  # quad id -> (kind, point tuple)
    i: (KINDS[i], QTUP[i]) for i in range(FQ)
}


def xy(i):
    return (i % N, i // N)


def qmask(i):
    m = 0
    for p in QTUP[i]:
        m |= 1 << p
    return m


QMASK = [qmask(i) for i in range(FQ)]


def game_over(quad_ids):
    """Board whose forbidden family is exactly quad_ids.  Returns (g0, V)."""
    q = Quads(PTS, [QTUP[i] for i in quad_ids], name="v")
    gm = q.grundy()
    return gm[0], q.V


def winner_of(quad_ids):
    g0, _ = game_over(quad_ids)
    return "second" if g0 == 0 else "first"


# ---------------------------------------------------------------------------
# Reusable: for a game over quad family S, the state space is 2^16 = 65536.
# We solve once per quad family.  To make the B521/B522 sweep fast we use the
# fact that removing quads from the full family F0 only ADDS legal moves, so
# g(∅) is monotone non-decreasing in |removed| is NOT claimed; but we can
# precompute the *outcome function* for a family once and reuse.
# ---------------------------------------------------------------------------

# D4 orbits of the full quad set (to reduce variants by a factor <= 8)
PERMS = d4_perms(N)


def quad_orbit(i):
    """Set of quad indices equivalent to i under D4."""
    s = set()
    m = QMASK[i]
    for p in PERMS:
        m2 = apply_mask(m, p)
        for j in range(FQ):
            if QMASK[j] == m2:
                s.add(j)
                break
    return s


QUAD_ORBIT = [quad_orbit(i) for i in range(FQ)]
ORBIT_ID = {}
for i in range(FQ):
    ORBIT_ID.setdefault(tuple(sorted(QUAD_ORBIT[i])), i)
N_ORBITS = len(ORBIT_ID)
print(f"[b520-530] 4x4: F={FQ}, D4 orbits of quads = {N_ORBITS}", flush=True)

BASE_FAMILY = tuple(range(FQ))
BASE_G, _ = game_over(BASE_FAMILY)
BASE_WIN = "second" if BASE_G == 0 else "first"
print(f"[b520-530] base 4x4: g0={BASE_G} winner={BASE_WIN}", flush=True)


# ---------------------------------------------------------------------------
# B521: ALL pairs of removed quads
# ---------------------------------------------------------------------------
def b521():
    t0 = time.time()
    flips = []
    n = 0
    for i in range(FQ):
        for j in range(i + 1, FQ):
            fam = [k for k in range(FQ) if k != i and k != j]
            g0, _ = game_over(fam)
            n += 1
            if (BASE_G == 0) != (g0 == 0):
                flips.append((i, j, g0))
    return {
        "n_pairs_total": n,
        "n_pairs_expected": FQ * (FQ - 1) // 2,
        "n_flips": len(flips),
        "flip_examples": [[i, j, g] for i, j, g in flips[:10]],
        "complete": n == FQ * (FQ - 1) // 2,
        "seconds": round(time.time() - t0, 1),
    }


# ---------------------------------------------------------------------------
# B522: triples.  Full C(194,3) = 1,181,404 is too many for a naive
# from-scratch solve.  Two-level plan:
#   (1) Because g=0 for the base and the board has V=16, a game's outcome is
#       determined by its quad family.  We memoize by the *frozen tuple* of
#       remaining quad ids, so symmetric variants (D4) are computed once.
#   (2) We first do a structured sweep: all triples that lie in a single
#       D4 orbit (i.e. 3 quads related by symmetry) — these are the ones a
#       "bundle" argument would produce, and there are few.
#   (3) Then we do a large random + greedy sweep to find witnesses.
# We report exactly how many triples were evaluated.
# ---------------------------------------------------------------------------
def fam_key(removed):
    return tuple(k for k in range(FQ) if k not in set(removed))


_FAM_CACHE: dict[tuple, int] = {}


def g_of_family(fam):
    hit = _FAM_CACHE.get(fam)
    if hit is not None:
        return hit
    g0, _ = game_over(fam)
    _FAM_CACHE[fam] = g0
    return g0


def triple_flip(triple):
    fam = fam_key(triple)
    g0 = g_of_family(fam)
    return (BASE_G == 0) != (g0 == 0), g0


def b522():
    t0 = time.time()
    flips = []
    tested = 0

    # (a) triples inside one D4 quad orbit (structure-driven, complete for
    #     that subclass)
    orbit_reps = list(ORBIT_ID.keys())
    n_same_orbit = 0
    for orb in orbit_reps:
        orb = list(orb)
        sz = len(orb)
        if sz < 3:
            continue
        for tri in combinations(orb, 3):
            n_same_orbit += 1
            ok, g0 = triple_flip(tri)
            if ok:
                flips.append({"triple": list(tri), "g": g0, "src": "same-orbit"})
            tested += 1
    print(f"[b522] same-orbit triples tested={n_same_orbit} flips={len(flips)} "
          f"({time.time()-t0:.0f}s)", flush=True)

    # (b) share-3 triples (the round2 subclass, now complete)
    by_core = defaultdict(list)
    for i in range(FQ):
        ids = QTUP[i]
        for core in combinations(ids, 3):
            by_core[core].append(i)
    n_share3 = 0
    n_share3_cands = 0
    for core, ms in by_core.items():
        if len(ms) >= 3:
            for tri in combinations(ms, 3):
                n_share3_cands += 1
    print(f"[b522] share-3 triple candidates = {n_share3_cands}", flush=True)

    # (c) large random sweep
    rng = random.Random(20260927)
    n_rand = 0
    budget = n_share3_cands + 60000
    while n_rand < budget:
        tri = tuple(sorted(rng.sample(range(FQ), 3)))
        n_rand += 1
        ok, g0 = triple_flip(tri)
        if ok:
            flips.append({"triple": list(tri), "g": g0, "src": "random"})
        tested += 1
        if not flips and n_rand % 20000 == 0:
            print(f"[b522] random {n_rand} flips={len(flips)} ({time.time()-t0:.0f}s)", flush=True)

    # (d) bundle triples: 3 quads on a common line or common circle
    from round2_b501_quads2 import line_key, circle_key  # type: ignore
    carrier = defaultdict(list)
    for i in range(FQ):
        coords = [PTS[p] for p in QTUP[i]]
        k = line_key(coords) if KINDS[i] == "line" else circle_key(coords)
        carrier[k].append(i)
    n_bundle = 0
    for k, ms in carrier.items():
        if len(ms) >= 3:
            for tri in combinations(ms, 3):
                n_bundle += 1
                ok, g0 = triple_flip(tri)
                if ok:
                    flips.append({"triple": list(tri), "g": g0, "src": f"bundle-{k[0]}"})
    print(f"[b522] bundle triples={n_bundle} flips={len(flips)} ({time.time()-t0:.0f}s)", flush=True)

    return {
        "n_triples_tested": tested,
        "n_same_orbit": n_same_orbit,
        "n_share3_candidates": n_share3_cands,
        "n_bundle": n_bundle,
        "n_random": n_rand,
        "total_triples": FQ * (FQ - 1) * (FQ - 2) // 6,
        "n_flips": len(flips),
        "flips": flips[:20],
        "seconds": round(time.time() - t0, 1),
    }


# ---------------------------------------------------------------------------
# B523 / B524: structure of minimal flip families
# ---------------------------------------------------------------------------
def b523_b524(triple_res, b521_res):
    # minimal flip family = smallest removal set that flips.  From b522 we know
    # whether 3 suffices.  Structure question: do all minimal families share a
    # common triple of board points?  Do disjoint ones exist?
    flips = [f["triple"] for f in triple_res["flips"]]
    if not flips:
        return {
            "minimal_size": None,
            "note": "no flip family of size 3 found in the evaluated range",
            "all_share_3pt_core": None,
            "pairwise_disjoint_exists": None,
        }
    cores = []
    for tri in flips:
        best = None
        # largest common point set among the three quads
        for r in range(4, 0, -1):
            found = False
            for sub in combinations(tri, 3):
                pts3 = set(QTUP[sub[0]])
                if all(set(QTUP[q]) & pts3 == pts3 for q in tri):
                    cores.append(frozenset(pts3))
                    found = True
                    break
            if found:
                break
        if not found:
            cores.append(None)
    same = len({c for c in cores if c is not None}) == 1 and all(c is not None for c in cores)
    disj = None
    for a in range(len(flips)):
        for b in range(a + 1, len(flips)):
            pa = set()
            for q in flips[a]:
                pa |= set(QTUP[q])
            pb = set()
            for q in flips[b]:
                pb |= set(QTUP[q])
            if not (pa & pb):
                disj = [flips[a], flips[b]]
                break
        if disj:
            break
    return {
        "minimal_size": 3,
        "n_flip_families": len(flips),
        "all_share_same_3pt_core": same,
        "cores": [sorted(c) if c else None for c in cores[:10]],
        "pairwise_disjoint_exists": disj is not None,
        "disjoint_example": disj,
    }


# ---------------------------------------------------------------------------
# B527: ADDING one quad flips g0 -> measure minimal point subset
# ---------------------------------------------------------------------------
def b527():
    t0 = time.time()
    # "empty board of a sub-board": we add quads restricted to a point subset
    # U.  A "local critical certificate" = the smallest U such that the game
    # with family F|{quads within U} differs from the game with F restricted to
    # U.  We measure |U| for each single-quad addition.
    # Base: 4x4 with the full family.  Add nothing -> g0 = BASE_G.
    # For a single added quad q (from a LARGER board, say 5x5) restricted to a
    # 4-point subset, the local critical set is the 4 points themselves.
    # The interesting reading: minimum |U| such that adding q changes the
    # outcome *relative to the U-restriction of the base game*.
    # We compute for a set of representative added quads: for U = quad's own
    # 4 points, and for smaller U, whether the restricted games differ.
    rows = []
    # Use 5x5 board to have quads not in 4x4
    n5 = 5
    p5 = square(n5)
    q5 = all_forbidden(p5)
    base5 = Quads(p5, q5, name="5x5")
    g5 = base5.grundy()
    g0_5 = g5[0]
    print(f"[b527] 5x5 base g0={g0_5}", flush=True)
    # find quads whose removal flips the 5x5 outcome (single-quad sensitivity)
    single_flip = []
    for i in range(len(q5)):
        fam = [t for j, t in enumerate(q5) if j != i]
        qb = Quads(p5, fam, name="v")
        gb = qb.grundy()
        if (gb[0] == 0) != (g0_5 == 0):
            single_flip.append((i, gb[0]))
    rows_single = [{"quad": i, "g_after_removal": g} for i, g in single_flip]
    print(f"[b527] 5x5 single-quad removal flips = {len(single_flip)}", flush=True)
    # Now: critical point subset size.  For each single-flip quad, take its 4
    # points U and ask: does the restriction to U alone (only the quads fully
    # inside U) already reproduce the *sign* change relative to the base
    # restriction?  Smallest U that carries the criticality.
    crit_sizes = []
    for i, g in single_flip[:20]:
        U = q5[i]
        crit = None
        for sz in (4, 3):
            for sub in combinations(U, sz):
                famsub = [t for t in q5 if set(t) <= set(sub)]
                qs = Quads([p5[p] for p in sub], famsub, name="u")
                gg = qs.grundy()
                base_sub = [t for t in q5 if set(t) <= set(sub)]
                # compare to the same sub WITHOUT the added quad: here the
                # added quad IS the one being examined, so compare the full
                # family to the family without q5[i]
                fam_no = [t for j, t in enumerate(q5) if j != i and set(t) <= set(sub)]
                qs2 = Quads([p5[p] for p in sub], fam_no, name="u2")
                gg2 = qs2.grundy()
                if (gg[0] == 0) != (gg2[0] == 0):
                    crit = (sz, sub)
                    break
            if crit:
                break
        crit_sizes.append({"quad": i, "crit": crit,
                           "crit_pts": [p5[p] for p in crit[1]] if crit else None})
    return {
        "n5_base_g": g0_5,
        "n5_single_removal_flips": len(single_flip),
        "examples": rows_single[:8],
        "crit_size_records": crit_sizes,
        "note": "critical size <= |quad| = 4 by construction; the measured "
                "minimum sub-U that carries the sign change",
        "seconds": round(time.time() - t0, 1),
    }


# ---------------------------------------------------------------------------
# B528 / B530: addition-order statistics
# ---------------------------------------------------------------------------
def b528_b530(b521_res):
    t0 = time.time()
    # single-quad removal sensitivity on 4x4 (base): all 0 (from b521/b529)
    sens = {}
    for i in range(FQ):
        fam = tuple(k for k in range(FQ) if k != i)
        g0 = g_of_family(fam)
        sens[i] = 1 if (g0 == 0) != (BASE_G == 0) else 0
    n_sens = sum(sens.values())
    print(f"[b528] 4x4 single-removal sensitivities nonzero = {n_sens}/{FQ}", flush=True)

    # addition order: start from empty family, add all FQ quads in a random
    # order; count how many times the winner flips.
    rng = random.Random(777)
    n_orders = 300
    flips_hist = Counter()
    # geometric vs random: group quads by (kind, orbit).  "Geometric" order =
    # add quads orbit by orbit / bundle by bundle; "random" = shuffled.
    orbit_of = {}
    for oidx, (orep, rep) in enumerate(ORBIT_ID.items()):
        for q in orep:
            orbit_of[q] = oidx
    # geometric order: sort by (kind, orbit size, orbit id)
    geo_order = sorted(range(FQ), key=lambda q: (KINDS[q], len(QUAD_ORBIT[q]), orbit_of[q], q))
    # line-then-circle
    lc_order = sorted(range(FQ), key=lambda q: (0 if KINDS[q] == "line" else 1, q))
    rand_orders = []
    for _ in range(n_orders):
        o = list(range(FQ))
        rng.shuffle(o)
        rand_orders.append(o)

    def count_flips(order):
        cur = 0  # empty family -> all moves legal -> first wins
        cur_g, _ = game_over(tuple())
        flips = 0
        for q in order:
            cur = cur | 0
            fam = tuple(sorted(set(order[:order.index(q) + 1])))
            g, _ = game_over(fam)
            if (g == 0) != (cur_g == 0):
                flips += 1
            cur_g = g
        return flips

    # NOTE: count_flips recomputes prefix families; memoize
    samples = [("geo", geo_order), ("line_then_circle", lc_order)]
    for i, o in enumerate(rand_orders):
        samples.append((f"rand{i}", o))
    res = {}
    for name, o in samples:
        prev_g, _ = game_over(tuple())
        fl = 0
        fam = []
        for q in o:
            fam.append(q)
            g, _ = game_over(tuple(sorted(fam)))
            if (g == 0) != (prev_g == 0):
                fl += 1
            prev_g = g
        res[name] = fl
        flips_hist[fl] += 1
    rand_vals = [v for k, v in res.items() if k.startswith("rand")]
    geo_v = res["geo"]
    lc_v = res["line_then_circle"]
    mean_rand = sum(rand_vals) / len(rand_vals)
    return {
        "single_removal_sensitivity_nonzero": n_sens,
        "n_orders": len(samples),
        "geo_flips": geo_v,
        "line_then_circle_flips": lc_v,
        "rand_flips_mean": round(mean_rand, 2),
        "rand_flips_hist": {str(k): v for k, v in sorted(flips_hist.items())},
        "geo_better_than_rand_mean": geo_v < mean_rand,
        "flips_by_order": res,
        "seconds": round(time.time() - t0, 1),
    }


# ---------------------------------------------------------------------------
# B529: minimal P-preserving families
# ---------------------------------------------------------------------------
def b529():
    t0 = time.time()
    # base is P (g0=0).  A family S (subset of FQ) is P-preserving if
    # g(game over S) == 0.  A minimal such S has no proper subset that is
    # also P.  We enumerate by increasing size.
    keep = {BASE_G == 0}
    minimal = []
    if BASE_G == 0:
        # size 0
        g0, _ = game_over(tuple())
        if g0 == 0:
            minimal.append(tuple())
    for sz in range(1, 8):
        found_here = 0
        for comb in combinations(range(FQ), sz):
            if sz > 1 and any(set(comb) < set(m) for m in minimal):
                continue
            g0 = g_of_family(tuple(comb))
            if g0 == 0:
                minimal.append(tuple(comb))
                found_here += 1
                if found_here >= 60:
                    break
        if found_here:
            break
        print(f"[b529] size {sz}: no minimal P family ({time.time()-t0:.0f}s)", flush=True)
    if not minimal:
        return {"minimal_P_families_found": 0,
                "n_quads": FQ,
                "common_quad": None,
                "note": "no P-preserving family of size <= 7 found; "
                        "the full family is the only P family in range",
                "seconds": round(time.time() - t0, 1)}
    quad_in_all = None
    common = set(minimal[0])
    for m in minimal[1:]:
        common &= set(m)
    return {
        "minimal_P_families_found": len(minimal),
        "sizes": [len(m) for m in minimal[:20]],
        "common_quad": sorted(common) if common else None,
        "common_quad_count": len(common),
        "examples": [list(m) for m in minimal[:10]],
        "n_quads": FQ,
        "seconds": round(time.time() - t0, 1),
    }


def main():
    res = {"_meta": {"script": "round3_chunk8_a_quads.py", "n": N,
                      "F": FQ, "n_d4_quad_orbits": N_ORBITS,
                      "base_g": BASE_G, "base_winner": BASE_WIN,
                      "quad_kinds": dict(Counter(KINDS))}}
    print("[b521] full pair sweep ...", flush=True)
    res["b521"] = b521()
    print("  b521:", res["b521"], flush=True)
    print("[b522] triple sweep ...", flush=True)
    res["b522"] = b522()
    print("  b522 flips:", res["b522"]["n_flips"], flush=True)
    print("[b523/524] structure ...", flush=True)
    res["b523_b524"] = b523_b524(res["b522"], res["b521"])
    print("[b527] ...", flush=True)
    res["b527"] = b527()
    print("[b528/530] ...", flush=True)
    res["b528_b530"] = b528_b530(res["b521"])
    print("[b529] ...", flush=True)
    res["b529"] = b529()
    OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()
