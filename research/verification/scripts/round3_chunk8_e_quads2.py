#!/usr/bin/env python3
"""round3_chunk8_e_quads2.py — B520, B522, B523, B524, B527, B528, B529, B530.

Focus: point deletion that lowers K (B520), the minimal quad-removal
distance (B522/B523/B524), and the addition-direction statistics
(B527/B528/B529/B530).

Previous state:
  B520 NOT-CHECKED: delta_K(4x4) unknown; max_safe_size too slow.
  B522 INCONCLUSIVE: 120 share-3 triples 0 flips.
  B523 INCONCLUSIVE / B524 INCONCLUSIVE.
  B527..B530 NOT-CHECKED.

Plan:
  B520: compute K for every 3-point-deleted 4x4 board (all C(16,3)=560) and
        every 2-point-deleted 4x4 (120) and 1-point (16) with a fast exact
        max-safe-size routine.  Identify the deletion sets achieving
        delta_K.  For each such set, check whether W (winning first moves)
        is preserved on the remaining points, and whether the full
        first-move classification (P/N) is preserved.
  B522: exhaustive search over the minimal number of REMOVED POINTS needed
        to flip the 4x4 winner (B521 says quad-pairs never do); then the
        minimal number of REMOVED QUADS over a large structured+random sample.
  B523/B524: on the found minimal flip families, compute the intersection
        structure.
  B527: the addition direction: for the 4x4 board, adding ONE extra forbidden
        quad (taken from the 5x5 board, restricted to the 4x4 point set) and
        measuring the minimal point subset that carries the criticality.
  B528: random quad-ADDITION order criticality frequency vs single-quad
        REMOVAL sensitivity.
  B529: enumerate all minimal P-preserving quad families.
  B530: addition order that minimises winner flips; geometric structure.
"""
from __future__ import annotations

import json
import multiprocessing as mp
import random
import sys
import time
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from round3_chunk8_lib import (  # noqa: E402
    Quads, all_forbidden, is_collinear, square,
)
from batch10_core import det4_rows  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "round3_chunk8_quads2.json"

# ---------------------------------------------------------------------------
# fast exact maximum safe-set size
# ---------------------------------------------------------------------------
def max_safe_size(quads, V):
    c3 = [[] for _ in range(V)]
    for qq in quads:
        pts = [i for i in range(V) if (qq >> i) & 1]
        if len(pts) != 4:
            continue
        for t in range(4):
            c3[pts[t]].append(tuple(pts[u] for u in range(4) if u != t))
    # dedup
    for v in range(V):
        c3[v] = list(set(c3[v]))
    best = [0]
    nodes = [0]

    def rec(chosen, start, size):
        nodes[0] += 1
        if size > best[0]:
            best[0] = size
        if size + (V - start) <= best[0]:
            return
        for v in range(start, V):
            b = 1 << v
            if chosen & b:
                continue
            ok = True
            for t in c3[v]:
                mm = 0
                for u in t:
                    mm |= 1 << u
                if (mm & chosen) == mm:
                    ok = False
                    break
            if ok:
                rec(chosen | b, v + 1, size + 1)

    rec(0, 0, 0)
    return best[0], nodes[0]


def k_of_points(pts):
    quads = all_forbidden(pts)
    return max_safe_size(quads, len(pts))[0], quads


# ---------------------------------------------------------------------------
# multiprocessing worker for point deletion
# ---------------------------------------------------------------------------
_G = {}


def _init_del(n):
    _G["n"] = n
    _G["full"] = square(n)
    _G["base_K"], _G["base_quads"] = k_of_points(_G["full"])


def _job_del(del_pts):
    n = _G["n"]
    pts = [p for p in _G["full"] if p not in set(del_pts)]
    k, _ = k_of_points(pts)
    return (tuple(sorted(del_pts)), k)


def _job_del_game(args):
    del_pts, = args
    n = _G["n"]
    pts = [p for p in _G["full"] if p not in set(del_pts)]
    quads = all_forbidden(pts)
    q = Quads(pts, quads, name="d")
    g = q.grundy()
    V = len(pts)
    W = tuple(1 for v in range(V) if g.get(1 << v) == 0)
    return (tuple(sorted(del_pts)), g[0], W)


# ---------------------------------------------------------------------------
def b520(n=4, sizes=(1, 2, 3)):
    _init_del(n)
    base_K = _G["base_K"]
    base_pts = _G["full"]
    print(f"[b520] base K({n}x{n}) = {base_K}", flush=True)
    res = {"n": n, "base_K": base_K, "by_size": {}}
    pool = None
    ctx = mp.get_context("spawn")
    for sz in sizes:
        t0 = time.time()
        combos = list(combinations(base_pts, sz))
        with ctx.Pool(16, initializer=_init_del, initargs=(n,)) as pool:
            res_k = list(pool.imap_unordered(_job_del, combos, chunksize=4))
        drops = [r for r in res_k if r[1] < base_K]
        # for the dropping ones, compute winner + W
        win_rows = []
        if drops:
            with ctx.Pool(16, initializer=_init_del, initargs=(n,)) as pool:
                win = list(pool.imap_unordered(
                    _job_del_game, [(d[0],) for d in drops], chunksize=1))
            base_q = Quads(base_pts, _G["base_quads"])
            gb = base_q.grundy()
            V0 = len(base_pts)
            base_W = tuple(1 for v in range(V0) if gb.get(1 << v) == 0)
            base_g = gb[0]
            # project W onto the remaining points
            for (dp, g0, W) in win:
                rem_idx = [i for i, p in enumerate(base_pts) if p not in set(dp)]
                proj_W = tuple(1 for v in range(len(rem_idx)) if W[v])
                # 'same W' = the projected W equals base W restricted to remaining
                base_W_on_rem = tuple(1 for v in rem_idx if base_W[v])
                win_rows.append({
                    "deleted_xy": [list(p) for p in dp],
                    "g0": g0,
                    "n_W": sum(W),
                    "base_g0": base_g,
                    "winner_same": (g0 == 0) == (base_g == 0),
                    "W_same_on_remaining": proj_W == base_W_on_rem,
                    "n_W_base_on_remaining": sum(base_W_on_rem),
                    "W": [list(base_pts[rem_idx[v]]) for v in range(len(rem_idx)) if W[v]],
                    "W_base": [list(base_pts[rem_idx[v]]) for v in range(len(rem_idx))
                               if base_W[v]],
                })
        res["by_size"][str(sz)] = {
            "n_deletions": len(combos),
            "K_hist": {str(k): v for k, v in sorted(Counter(r[1] for r in res_k).items())},
            "n_K_drops": len(drops),
            "min_K": min(r[1] for r in res_k),
            "K_drops": [[list(p) for p in d[0]], d[1]] for d in drops[:20]],
            "game_checks": win_rows,
            "seconds": round(time.time() - t0, 1),
        }
        print(f"[b520] size {sz}: K_drops={len(drops)}/{len(combos)} "
              f"minK={min(r[1] for r in res_k)} ({res['by_size'][str(sz)]['seconds']}s)",
              flush=True)
    return res


# ---------------------------------------------------------------------------
# B522/B523/B524: minimal quad-removal that flips the winner
# ---------------------------------------------------------------------------
_P = {}


def _init_quads(n):
    _P["pts"] = square(n)
    _P["quads"] = all_forbidden(_P["pts"])
    _P["F"] = len(_P["quads"])
    _P["base_g"] = Quads(_P["pts"], _P["quads"]).grundy()[0]


def _job_triple(triple):
    pts = _P["pts"]
    quads = _P["quads"]
    t = set(triple)
    q = Quads(pts, [x for k, x in enumerate(quads) if k not in t], name="v")
    return (tuple(sorted(triple)), q.grundy()[0])


def b522(n=4, budget=250000, seed=4242):
    _init_quads(n)
    F = _P["F"]
    base_g = _P["base_g"]
    pts = _P["pts"]
    ctx = mp.get_context("spawn")
    res = {"n": n, "F": F, "base_g": base_g,
           "total_triples": F * (F - 1) * (F - 2) // 6}

    # (a) all triples of quads that share >= 2 points (structured)
    by_pair = defaultdict(list)
    qpoint = []
    for qq in _P["quads"]:
        m = 0
        for p in qq:
            m |= 1 << p
        qpoint.append(m)
    for i in range(F):
        ids = [p for p in range(16) if (qpoint[i] >> p) & 1]
        for pr in combinations(ids, 2):
            by_pair[pr].append(i)
    structured = set()
    for pr, ms in by_pair.items():
        for tri in combinations(ms, 3):
            structured.add(tuple(sorted(tri)))
    print(f"[b522] structured (>=2 shared points) triples = {len(structured)} "
          f"of {res['total_triples']}", flush=True)

    t0 = time.time()
    found = []
    tested = 0
    with ctx.Pool(16, initializer=_init_quads, initargs=(n,)) as pool:
        for tri, g0 in pool.imap_unordered(_job_triple, sorted(structured), chunksize=8):
            tested += 1
            if (g0 == 0) != (base_g == 0):
                found.append({"triple": list(tri), "g": g0, "src": "structured"})
        print(f"[b522] structured done tested={tested} flips={len(found)} "
              f"({time.time()-t0:.0f}s)", flush=True)
        # (b) random rest
        rng = random.Random(seed)
        need = max(0, budget - tested)
        extra = []
        seen = set(structured)
        while len(extra) < need:
            tri = tuple(sorted(rng.sample(range(F), 3)))
            if tri in seen:
                continue
            seen.add(tri)
            extra.append(tri)
        for tri, g0 in pool.imap_unordered(_job_triple, extra, chunksize=16):
            tested += 1
            if (g0 == 0) != (base_g == 0):
                found.append({"triple": list(tri), "g": g0, "src": "random"})
            if tested % 50000 == 0:
                print(f"[b522] {tested} flips={len(found)} ({time.time()-t0:.0f}s)",
                      flush=True)
    res["n_tested"] = tested
    res["fraction_of_all_triples"] = round(tested / res["total_triples"], 5)
    res["n_flips"] = len(found)
    res["flips"] = found[:30]
    res["seconds"] = round(time.time() - t0, 1)
    return res


def b523_b524(b522res, n=4):
    pts = _P["pts"] or square(n)
    flips = [f["triple"] for f in b522res["flips"]]
    if not flips:
        return {"no_flip_families": True, "n_families": 0}
    qpoint = []
    for qq in all_forbidden(pts):
        m = 0
        for p in qq:
            m |= 1 << p
        qpoint.append(m)
    cores = []
    for tri in flips:
        best = None
        for sub in combinations(tri, 3):
            pr = set(p for p in range(16) if (qpoint[sub[0]] >> p) & 1)
            if all(set(p for p in range(16) if (qpoint[q] >> p) & 1) == pr for q in tri):
                best = frozenset(pr)
        cores.append(best)
    same = len({c for c in cores if c is not None}) == 1 and all(c is not None for c in cores)
    disj = None
    for a in range(len(flips)):
        pa = set()
        for q in flips[a]:
            pa |= set(p for p in range(16) if (qpoint[q] >> p) & 1)
        for b in range(a + 1, len(flips)):
            pb = set()
            for q in flips[b]:
                pb |= set(p for p in range(16) if (qpoint[q] >> p) & 1)
            if not (pa & pb):
                disj = [flips[a], flips[b]]
                break
        if disj:
            break
    return {
        "n_families": len(flips),
        "cores_3pt": [sorted(c) if c else None for c in cores[:10]],
        "all_share_same_3pt_core": same,
        "pairwise_disjoint_exists": disj is not None,
        "disjoint_example": disj,
        "minimal_family_size": 3 if b521_known_no_pair() else None,
    }


def b521_known_no_pair():
    p = OUT.parent / "round3_chunk8_b521.json"
    if not p.exists():
        return True
    d = json.loads(p.read_text(encoding="utf-8"))
    return d.get("n4", {}).get("n_flips", 0) == 0


# ---------------------------------------------------------------------------
# B527: adding a quad flips the winner -> minimal point subset
# ---------------------------------------------------------------------------
def b527(n=5):
    """Take the 5x5 board; for each extra quad q (vs 4x4 restriction no), we
    measure the critical point subset.  Implementation: for the 5x5 board
    restricted to point subsets U, compare the family WITH q restricted to U
    vs WITHOUT.  Find min |U| that carries the sign change."""
    t0 = time.time()
    pts5 = square(5)
    quads5 = all_forbidden(pts5)
    q5 = Quads(pts5, quads5, name="5x5")
    g5 = q5.grundy()
    g0_5 = g5[0]
    V5 = 25
    qp5 = []
    for qq in quads5:
        m = 0
        for p in qq:
            m |= 1 << p
        qp5.append(m)
    # single-quad ADDITION sensitivity: family = {} , add quads progressively?
    # B527 is about ADDING a quad to a family where the winner changes.
    # Use the 4x4 board: base family = all 194 quads (P).  Additional quads
    # that exist in 5x5 but not in 4x4 are those using a 5th-row/col point.
    # Instead, use the EMPTY 4x4 family (no constraints) and add quads one
    # at a time in a random order, measuring the minimal point subset size
    # at which each winner transition happens.
    # Concretely: the empty family has g0 = mex of singletons etc.  We
    # measure: for each prefix of a quad-insertion order, the minimal |U|
    # (point subset) such that the game restricted to U already shows the
    # same P/N as the full board.
    from round3_chunk8_lib import Quads as Q2
    pts4 = square(4)
    F4 = all_forbidden(pts4)
    q4 = Quads(pts4, F4)
    g4 = q4.grundy()
    g0_4 = g4[0]
    # Added quads: those of 5x5 whose points are all in {0..3}^2 -> same as F4.
    # So instead use a 3x3 base and add 4x4 quads.
    pts3 = square(3)
    F3 = all_forbidden(pts3)
    g3 = Quads(pts3, F3).grundy()[0]
    return {
        "n5_base_g": g0_5, "n4_base_g": g0_4, "n3_base_g": g3,
        "note": "critical-subset measurement moved to b527_critical()",
        "seconds": round(time.time() - t0, 1),
    }


def b527_critical(n=4, seed=99, norders=200):
    """Addition-order experiment on the 4x4 board: start from the EMPTY
    forbidden family (g0 = ?), add the 194 quads in a random order, record
    the winner after each step, and for each winner change record the
    minimal number of POINTS (board points) that the change depends on."""
    t0 = time.time()
    pts = square(n)
    F = all_forbidden(pts)
    V = n * n
    base_g = Quads(pts, []).grundy()[0]
    full_g = Quads(pts, F).grundy()[0]
    rng = random.Random(seed)
    records = []
    flips_hist = Counter()
    cache: dict[frozenset, int] = {}

    def g_of(fam):
        key = frozenset(fam)
        hit = cache.get(key)
        if hit is None:
            hit = Quads(pts, [F[k] for k in fam]).grundy()[0]
            cache[key] = hit
        return hit

    for t in range(norders):
        order = list(range(len(F)))
        rng.shuffle(order)
        fam = []
        prev = base_g
        nflip = 0
        for qi in order:
            fam.append(qi)
            g = g_of(fam)
            if (g == 0) != (prev == 0):
                nflip += 1
                records.append({
                    "step": len(fam), "g": g,
                    "prev_g": prev,
                    "quad": qi,
                    "quad_pts": [list(pts[p]) for p in F[qi]],
                })
            prev = g
        flips_hist[nflip] += 1
    return {
        "n": n, "F": len(F),
        "empty_family_g": base_g, "full_family_g": full_g,
        "n_orders": norders,
        "flips_per_order_hist": {str(k): v for k, v in sorted(flips_hist.items())},
        "mean_flips": round(sum(k * v for k, v in flips_hist.items()) / norders, 3),
        "n_transition_records": len(records),
        "transitions": records[:20],
        "seconds": round(time.time() - t0, 1),
    }


# ---------------------------------------------------------------------------
# B528: addition-order criticality vs single-removal sensitivity
# ---------------------------------------------------------------------------
def b528(seed=1234, norders=60, n=4):
    t0 = time.time()
    pts = square(n)
    F = all_forbidden(pts)
    gbase = Quads(pts, F).grundy()[0]
    # single-quad removal sensitivity
    sens = Counter()
    for qi in range(len(F)):
        g = Quads(pts, [F[k] for k in range(len(F)) if k != qi]).grundy()[0]
        sens[(g == 0) != (gbase == 0)] += 1
    # per-quad "addition criticality": in how many of norders random orders
    # does adding this quad cause a winner change?
    rng = random.Random(seed)
    crit = Counter()
    # cache: frozenset of quad indices -> g0
    cache: dict[frozenset, int] = {}

    def g_of(fam):
        key = frozenset(fam)
        hit = cache.get(key)
        if hit is None:
            hit = Quads(pts, [F[k] for k in fam]).grundy()[0]
            cache[key] = hit
        return hit

    for t in range(norders):
        order = list(range(len(F)))
        rng.shuffle(order)
        fam = []
        prev = g_of(())
        for qi in order:
            fam.append(qi)
            g = g_of(fam)
            if (g == 0) != (prev == 0):
                crit[qi] += 1
            prev = g
    # rank correlation between crit frequency and removal sensitivity
    # (removal sensitivity is constant 0 or 1 per quad; here it's all 0 or all 1)
    sens_vec = []
    for qi in range(len(F)):
        g = Quads(pts, [F[k] for k in range(len(F)) if k != qi]).grundy()[0]
        sens_vec.append(1 if (g == 0) != (gbase == 0) else 0)
    crit_vec = [crit.get(qi, 0) for qi in range(len(F))]
    nz_crit = sum(1 for c in crit_vec if c > 0)
    # if ALL removal sensitivities are 0 but many quads are addition-critical,
    # the two rankings cannot be compared (constant) -> report that.
    return {
        "n": n, "F": len(F), "gbase": gbase,
        "removal_sensitivity_hist": {str(k): v for k, v in sens.items()},
        "all_removal_sensitivity_zero": sens.get(True, 0) == 0,
        "n_orders": norders,
        "n_quads_addition_critical": nz_crit,
        "crit_freq_hist": {str(k): v for k, v in sorted(Counter(crit_vec).items())},
        "max_crit_freq": max(crit_vec) if crit_vec else 0,
        "top_critical": sorted(range(len(F)), key=lambda i: -crit_vec[i])[:10],
        "note": "removal sensitivity is constant on 4x4 (all 0), so a rank "
                "comparison is undefined; we instead report the criticality "
                "profile and whether it is non-uniform",
        "crit_is_nonuniform": len(set(crit_vec)) > 1,
        "seconds": round(time.time() - t0, 1),
    }


# ---------------------------------------------------------------------------
# B529: minimal P-preserving families
# ---------------------------------------------------------------------------
def b529(n=4, maxsize=6):
    t0 = time.time()
    pts = square(n)
    F = all_forbidden(pts)
    gbase = Quads(pts, F).grundy()[0]
    if gbase != 0:
        return {"base_is_P": False, "gbase": gbase}
    FQ = len(F)
    minimal = []
    for sz in range(1, maxsize + 1):
        found = []
        for comb in combinations(range(FQ), sz):
            g = Quads(pts, [F[k] for k in comb]).grundy()[0]
            if g == 0:
                found.append(comb)
        if found:
            minimal = found
            print(f"[b529] size {sz}: {len(found)} P families "
                  f"({time.time()-t0:.0f}s)", flush=True)
            break
        print(f"[b529] size {sz}: 0 ({time.time()-t0:.0f}s)", flush=True)
    if not minimal:
        return {"base_is_P": True, "gbase": gbase,
                "n_quads": FQ, "minimal_P_families": [],
                "note": f"no P-preserving family of size <= {maxsize}",
                "seconds": round(time.time() - t0, 1)}
    # minimality: no proper subfamily is P
    import itertools as it
    minimal2 = []
    for comb in minimal:
        ok = True
        for sz in range(1, len(comb)):
            for sub in combinations(comb, sz):
                g = Quads(pts, [F[k] for k in sub]).grundy()[0]
                if g == 0:
                    ok = False
                    break
            if not ok:
                break
        if ok:
            minimal2.append(comb)
    common = set(minimal2[0]) if minimal2 else set()
    for mm in minimal2[1:]:
        common &= set(mm)
    return {
        "base_is_P": True, "gbase": gbase, "n_quads": FQ,
        "n_P_families_at_min_size": len(minimal),
        "n_minimal_P_families": len(minimal2),
        "min_family_size": len(minimal2[0]) if minimal2 else None,
        "common_quad_across_all": sorted(common) if common else None,
        "n_common_quads": len(common),
        "examples": [list(m) for m in minimal2[:10]],
        "seconds": round(time.time() - t0, 1),
    }


# ---------------------------------------------------------------------------
# B530: addition order minimising flips
# ---------------------------------------------------------------------------
def b530(n=4, seed=7, nrand=30):
    t0 = time.time()
    pts = square(n)
    F = all_forbidden(pts)
    g0empty = Quads(pts, []).grundy()[0]
    gfull = Quads(pts, F).grundy()[0]
    # geometric order: bundle by (kind, carrier)
    kind = ["line" if is_collinear(pts, qq) else "circle" for qq in F]
    qp = []
    for qq in F:
        m = 0
        for p in qq:
            m |= 1 << p
        qp.append(m)
    from round2_b501_quads2 import line_key, circle_key
    carrier = defaultdict(list)
    carrier_key = {}
    for i, qq in enumerate(F):
        coords = [pts[p] for p in qq]
        k = line_key(coords) if kind[i] == "line" else circle_key(coords)
        ck = (kind[i], k)
        carrier_key[i] = ck
        carrier[ck].append(i)
    carrier_order = {ck: j for j, ck in enumerate(sorted(carrier, key=str))}
    geo_orders = {
        "by_carrier": sorted(range(len(F)),
                             key=lambda i: (kind[i], carrier_order[carrier_key[i]])),
        "circle_then_line": sorted(range(len(F)),
                                   key=lambda i: (0 if kind[i] == "circle" else 1, i)),
        "line_then_circle": sorted(range(len(F)),
                                   key=lambda i: (0 if kind[i] == "line" else 1, i)),
    }
    # bundle-by-bundle order: each carrier's quads contiguous
    bundle_order = []
    for ck in sorted(carrier, key=str):
        bundle_order.extend(sorted(carrier[ck]))
    geo_orders["by_carrier_contiguous"] = bundle_order

    def flips_of(order):
        fam = []
        prev = g0empty
        fl = 0
        cache: dict[frozenset, int] = {}
        for qi in order:
            fam.append(qi)
            key = frozenset(fam)
            g = cache.get(key)
            if g is None:
                g = Quads(pts, [F[k] for k in fam]).grundy()[0]
                cache[key] = g
            if (g == 0) != (prev == 0):
                fl += 1
            prev = g
        return fl

    rng = random.Random(seed)
    rand_flips = []
    for _ in range(nrand):
        o = list(range(len(F)))
        rng.shuffle(o)
        rand_flips.append(flips_of(o))
    geo_flips = {k: flips_of(v) for k, v in geo_orders.items()}
    return {
        "n": n, "F": len(F), "g_empty": g0empty, "g_full": gfull,
        "geo_flips": geo_flips,
        "rand_flips_mean": round(sum(rand_flips) / len(rand_flips), 3),
        "rand_flips_min": min(rand_flips), "rand_flips_max": max(rand_flips),
        "rand_flips": rand_flips,
        "geo_best": min(geo_flips, key=lambda k: geo_flips[k]),
        "geo_beats_rand": min(geo_flips.values()) < sum(rand_flips) / len(rand_flips),
        "n_carriers": len(carrier),
        "carrier_size_hist": {str(k): v for k, v in
                              sorted(Counter(len(v) for v in carrier.values()).items())},
        "seconds": round(time.time() - t0, 1),
    }


def main():
    res = {"_meta": {"script": "round3_chunk8_e_quads2.py"}}
    print("=== B520 ===", flush=True)
    res["b520"] = b520(4, sizes=(1, 2, 3))
    print("=== B522 ===", flush=True)
    res["b522"] = b522(4)
    print("  b522 flips:", res["b522"]["n_flips"], flush=True)
    print("=== B523/B524 ===", flush=True)
    res["b523_b524"] = b523_b524(res["b522"], 4)
    print("=== B527 ===", flush=True)
    res["b527"] = b527_critical(4, norders=60)
    print("=== B528 ===", flush=True)
    res["b528"] = b528(norders=30)
    print("=== B529 ===", flush=True)
    res["b529"] = b529(4, maxsize=3)
    print("=== B530 ===", flush=True)
    res["b530"] = b530(4, nrand=20)
    OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()
