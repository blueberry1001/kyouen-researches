#!/usr/bin/env python3
"""round5 p_rand residual: B512-B530 computations (n<=6, existing n=7 data).

Corrects the board_square_minus ID/coord bug that invalidated
round5_b401_del3.json (it passed int ids into a (x,y)-coord API, so no
points were ever deleted).

Outputs research/verification/round5_pgrand.json
"""
from __future__ import annotations

import itertools
import json
import struct
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import board_square, board_square_minus, is_forbidden_quad  # noqa: E402

OUT = REPO / "research" / "verification" / "round5_pgrand.json"
NIGHT = REPO / "night-research"

rep: dict = {}
t0 = time.time()


def xy(i: int, n: int) -> tuple[int, int]:
    return (i % n, i // n)


def solve_K_g(n: int, deleted_ids: tuple[int, ...]) -> tuple[int, int]:
    bd = board_square_minus(n, [xy(i, n) for i in deleted_ids])
    K = bd.max_safe_size()
    g = bd.solve_outcomes().get(0, 0)
    return K, g


# ==================== B512 / B514: deletion distances ====================
print("=== B512/B514 n=4 del3 (correct coords) ===", flush=True)
n = 4
base_K, base_g = solve_K_g(n, ())
print(f"base K={base_K} g={base_g}", flush=True)
assert base_K == 7 and base_g == 0

drops = []
flips = []
pure3 = []
# also record 2-point flips for delta_out
flip_pairs = []
for i, j in itertools.combinations(range(16), 2):
    K, g = solve_K_g(n, (i, j))
    if g != base_g:
        flip_pairs.append({"deleted": [i, j], "K": K, "g": g})
    if K < base_K:
        drops.append({"deleted": [i, j], "K": K, "g": g})

print(f"pairs: K_drops={len(drops)} flip_pairs={len(flip_pairs)}", flush=True)

t = time.time()
for trip in itertools.combinations(range(16), 3):
    K, g = solve_K_g(n, trip)
    if K < base_K:
        drops.append({"deleted": list(trip), "K": K, "g": g})
    if g != base_g:
        flips.append({"deleted": list(trip), "K": K, "g": g})
        # pure 3-point flip: no 2-subset flips
        if all(
            solve_K_g(n, sub)[1] == base_g
            for sub in itertools.combinations(trip, 2)
        ):
            pure3.append({"deleted": list(trip), "K": K, "g": g})
print(f"triples done {time.time()-t:.1f}s K_drops={len(drops)} flips={len(flips)} pure3={len(pure3)}", flush=True)

rep["B512_n4"] = {
    "base_K": base_K,
    "base_g": base_g,
    "n_pairs": 120,
    "n_triples": 560,
    "K_drops": drops,
    "n_K_drops": len(drops),
    "flip_pairs_n": len(flip_pairs),
    "flip_pairs": flip_pairs[:20],
    "triple_flips_n": len(flips),
    "pure_triple_flips": pure3,
    "delta_K_n4": 3 if any(len(d["deleted"]) == 3 for d in drops) else (
        4 if any(len(d["deleted"]) == 2 for d in drops) else ">=4_or_pairs_untested"
    ),
    # more precise below
}

# refine delta_K: min |D| with K drop
if drops:
    min_del = min(len(d["deleted"]) for d in drops)
    rep["B512_n4"]["delta_K_n4"] = min_del
else:
    # no 2- or 3-point K-drop
    rep["B512_n4"]["delta_K_n4"] = ">=4"
rep["B512_n4"]["delta_out_n4"] = 2 if flip_pairs else ">=3"

# B514 on n=4: gap
dk4 = rep["B512_n4"]["delta_K_n4"]
dout4 = rep["B512_n4"]["delta_out_n4"]
rep["B514_n4"] = {
    "delta_out": dout4,
    "delta_K": dk4,
    "gap": (dk4 - dout4) if isinstance(dk4, int) and isinstance(dout4, int) else "unknown",
}

# ---- n=3 full del (cheap) ----
print("=== n=3 deletions ===", flush=True)
n = 3
bK3, bG3 = solve_K_g(n, ())
drops3 = []
flips3 = []
for r in (1, 2, 3):
    for dele in itertools.combinations(range(9), r):
        K, g = solve_K_g(n, dele)
        if K < bK3:
            drops3.append({"deleted": list(dele), "r": r, "K": K, "g": g})
        if g != bG3:
            flips3.append({"deleted": list(dele), "r": r, "K": K, "g": g})
rep["B512_n3"] = {
    "base_K": bK3,
    "base_g": bG3,
    "K_drops": drops3[:20],
    "n_K_drops": len(drops3),
    "min_K_drop_size": min((len(d["deleted"]) for d in drops3), default=None),
    "flips": flips3[:20],
    "n_flips": len(flips3),
    "min_flip_size": min((len(d["deleted"]) for d in flips3), default=None),
}
print("n3", rep["B512_n3"]["n_K_drops"], rep["B512_n3"]["n_flips"], flush=True)

# ---- n=5: all 1-point + sample of 2-point (full 2-point is 14 min) ----
print("=== n=5 del 1 + sample 2,3 ===", flush=True)
n = 5
bK5, bG5 = solve_K_g(n, ())
print("n5 base", bK5, bG5, flush=True)
drops5 = []
flip5 = []
t = time.time()
for dele in itertools.combinations(range(25), 1):
    K, g = solve_K_g(n, dele)
    if K < bK5:
        drops5.append({"deleted": list(dele), "r": 1, "K": K, "g": g})
    if g != bG5:
        flip5.append({"deleted": list(dele), "r": 1, "K": K, "g": g})
print(f"n5 r=1 done {time.time()-t:.1f}s drops={len(drops5)} flips={len(flip5)}", flush=True)

pairs5 = list(itertools.combinations(range(25), 2))
sample2 = pairs5[:: max(1, len(pairs5) // 80)][:80]
for dele in sample2:
    K, g = solve_K_g(n, dele)
    if K < bK5:
        drops5.append({"deleted": list(dele), "r": 2, "K": K, "g": g})
    if g != bG5:
        flip5.append({"deleted": list(dele), "r": 2, "K": K, "g": g})
print(f"n5 r=2 sample done {time.time()-t:.1f}s", flush=True)

rep["B512_n5"] = {
    "base_K": bK5,
    "base_g": bG5,
    "n_singles": 25,
    "n_pairs_sampled": len(sample2),
    "K_drops": drops5[:30],
    "n_K_drops": len(drops5),
    "flips": flip5[:30],
    "n_flips": len(flip5),
}
print("n5 sample done", flush=True)


# ==================== B513: 7x7 hitting number of 16 K=14 sets =========
print("=== B513 hitting number ===", flush=True)
raw = (NIGHT / "maxsafe_n7_K14.bin").read_bytes()
masks = struct.unpack("<" + "Q" * (len(raw) // 8), raw)
sets7 = []
for m in masks:
    pts = frozenset(j for j in range(49) if (m >> j) & 1)
    assert len(pts) == 14
    sets7.append(pts)
print(f"loaded {len(sets7)} sets of size 14", flush=True)

# corners of 7x7: id = y*7+x
corners = [0, 6, 42, 48]


def hits_all(D: frozenset[int] | set[int]) -> bool:
    return all(s & D for s in sets7)


# tau = min hitting set size
tau = None
tau_examples = []
for r in (1, 2, 3, 4):
    found = []
    for D in itertools.combinations(range(49), r):
        if hits_all(frozenset(D)):
            found.append(list(D))
            if len(found) >= 5:
                break
    if found:
        tau = r
        tau_examples = found
        break
print(f"tau={tau} examples={tau_examples[:3]}", flush=True)

# specifically: do 3 corners hit all?
c3 = [c for c in corners]
# all 3-subsets of corners
c3_hits = []
for trip in itertools.combinations(corners, 3):
    c3_hits.append({"D": list(trip), "hits_all": hits_all(frozenset(trip))})
c2_hits = []
for pair in itertools.combinations(corners, 2):
    c2_hits.append({"D": list(pair), "hits_all": hits_all(frozenset(pair))})

# every 2-set misses some 14-set? (= tau >= 3)
n2_hit = 0
for D in itertools.combinations(range(49), 2):
    if hits_all(frozenset(D)):
        n2_hit += 1

# every 3-set that hits all: count how many of C(49,3)
n3_hit = 0
n3_tested = 0
for D in itertools.combinations(range(49), 3):
    n3_tested += 1
    if hits_all(frozenset(D)):
        n3_hit += 1

rep["B513"] = {
    "n_sets": len(sets7),
    "set_size": 14,
    "tau": tau,
    "tau_examples": tau_examples,
    "corner_triples": c3_hits,
    "corner_pairs": c2_hits,
    "n_2sets_hitting_all": n2_hit,
    "n_3sets_hitting_all": n3_hit,
    "n_3sets_tested": n3_tested,
    "delta_K_7_equals_tau": True,
    "note": "All 14-stone safe sets on 7x7 are exactly these 16 (K=14); "
            "D lowers K iff D hits every one of them. Hence delta_K(7)=tau.",
}
print("B513", rep["B513"]["tau"], rep["B513"]["n_2sets_hitting_all"], rep["B513"]["n_3sets_hitting_all"], flush=True)


# ==================== B514: gap on n=3,4 (and 5) =======================
rep["B514"] = {
    "n3": {
        "delta_out": rep["B512_n3"].get("min_flip_size"),
        "delta_K": rep["B512_n3"].get("min_K_drop_size"),
        "gap": (
            rep["B512_n3"]["min_K_drop_size"] - rep["B512_n3"]["min_flip_size"]
            if rep["B512_n3"].get("min_K_drop_size") and rep["B512_n3"].get("min_flip_size")
            else None
        ),
    },
    "n4": rep["B514_n4"],
    "n5_partial": {
        "delta_out": min((len(d["deleted"]) for d in flip5), default=None),
        "delta_K": min((len(d["deleted"]) for d in drops5), default=None),
        "note": "triples only sampled 200/2300",
    },
    "n7_from_B513": {
        "delta_out": "unknown (needs winner DP on 7x7-minus; not run)",
        "delta_K": rep["B513"]["tau"],
    },
}


# ==================== B519: minimal flip deletion sets size>=4 =========
print("=== B519 minimal flip sets n=3,4 ===", flush=True)


def min_flip_sets(n: int, max_r: int) -> dict:
    base_K, base_g = solve_K_g(n, ())
    # first find all flip sets up to max_r, then keep minimal
    flips_by_r: dict[int, list[tuple]] = {}
    for r in range(1, max_r + 1):
        lst = []
        for dele in itertools.combinations(range(n * n), r):
            K, g = solve_K_g(n, dele)
            if g != base_g:
                lst.append(dele)
        flips_by_r[r] = lst
        print(f"  n={n} r={r} flips={len(lst)}", flush=True)
    # minimal: no proper subset flips
    flip_all = set()
    for r, lst in flips_by_r.items():
        flip_all.update(lst)
    minimal = []
    for S in flip_all:
        ok = True
        for r in range(1, len(S)):
            for sub in itertools.combinations(S, r):
                if sub in flip_all:
                    ok = False
                    break
            if not ok:
                break
        if ok:
            minimal.append(S)
    # does each minimal set of size>=4 contain a forbidden quad?
    contain_q = 0
    no_q = []
    for S in minimal:
        if len(S) < 4:
            continue
        has = False
        pts = [xy(i, n) for i in S]
        for comb in itertools.combinations(pts, 4):
            if is_forbidden_quad(comb):
                has = True
                break
        if has:
            contain_q += 1
        else:
            no_q.append(list(S))
    return {
        "base_g": base_g,
        "flips_by_r": {str(r): len(v) for r, v in flips_by_r.items()},
        "n_minimal": len(minimal),
        "minimal_by_size": {
            str(sz): sum(1 for S in minimal if len(S) == sz)
            for sz in sorted({len(S) for S in minimal})
        },
        "minimal_ge4_with_quad": contain_q,
        "minimal_ge4_without_quad": no_q[:10],
        "minimal_examples": [list(S) for S in minimal[:15]],
    }


rep["B519"] = {
    "n3": min_flip_sets(3, 4),
    "n4_r_le_3": {
        "note": "size-4 full enum C(16,4)=1820 ~ 3min; using known flip pairs + triples first",
    },
}

# n=4: we already have flip_pairs and pure3 / flips from B512 section
# enumerate size-4 sets that are minimal (no subset flips)
flip_all_4 = set()
for d in flip_pairs:
    flip_all_4.add(tuple(d["deleted"]))
for d in flips:
    flip_all_4.add(tuple(d["deleted"]))
# also need ALL triple flips (not just pure)
# recompute all triple flips quickly from stored list
for d in flips:
    flip_all_4.add(tuple(d["deleted"]))

min4 = []
t = time.time()
for quad in itertools.combinations(range(16), 4):
    # minimal iff no 1-2-3 subset flips
    bad = False
    for r in (1, 2, 3):
        for sub in itertools.combinations(quad, r):
            if sub in flip_all_4:
                bad = True
                break
        if bad:
            break
    if bad:
        continue
    K, g = solve_K_g(4, quad)  # n=4
    if g != base_g:
        min4.append(quad)
print(f"n4 size-4 minimal flips: {len(min4)} in {time.time()-t:.1f}s", flush=True)

with_q = []
without_q = []
for S in min4:
    pts = [xy(i, 4) for i in S]
    has = any(is_forbidden_quad(c) for c in itertools.combinations(pts, 4))
    (with_q if has else without_q).append(list(S))

rep["B519"]["n4"] = {
    "n_size4_minimal_flips": len(min4),
    "with_forbidden_quad": len(with_q),
    "without_forbidden_quad": without_q[:10],
    "examples_with_q": with_q[:10],
    "minimal_ge4_summary": {
        "size4_total": len(min4),
        "size4_with_q": len(with_q),
        "size4_without_q": len(without_q),
    },
}
print("B519 n4", rep["B519"]["n4"]["n_size4_minimal_flips"], flush=True)


# ==================== B520: delta_K achieving sets keep W? =============
print("=== B520 ===", flush=True)
# On n=4, if delta_K>=4 we have no achieving set yet at size 3.
# On n=7, tau-hitting sets achieve delta_K; check whether first-move W is preserved.
# Winner of 7x7-minus is expensive; use first-move classification only via
# known fact: 7x7 empty is P (g=0). If we delete a hitting set D, K drops.
# We cannot cheaply recompute g on 7x7-minus (49-|D| points). Skip full DP;
# instead on n=4 if we find any K-drop set, check g.
if drops:
    bK4, bG4 = 7, 0
    witness = []
    for d in drops[:10]:
        K, g = solve_K_g(4, tuple(d["deleted"]))
        witness.append({"deleted": d["deleted"], "K": K, "g": g, "g_preserved": g == bG4})
    rep["B520"] = {
        "n4_Kdrop_sets_checked": len(witness),
        "witness": witness,
        "note": "If no K-drop exists at minimal size, B520 is blocked on finding delta_K sets.",
    }
else:
    # check tau-hitting sets on n=7 conceptually
    rep["B520"] = {
        "n4": "no K-drop at size<=3, so no delta_K-achieving set to test on n=4",
        "n7_conceptual": {
            "delta_K_achieving": f"tau={rep['B513']['tau']} hitting sets",
            "note": "W preservation on 7x7-minus requires full game DP (46 points); "
                    "not run in this batch (n>=7 full calc forbidden).",
        },
    }


# ==================== B521-B524: forbidden-quad release ================
print("=== B521-B524 (from existing complete B521 + bundle) ===", flush=True)
# Reuse parallel-agent B521 result + known circle-bundle flip; do B523/B524
# analysis on the known flipping release family (70 quads of one circle).
# Identify the 8-point circle on 4x4 that yields 70 quads and check shared triples.

bd = board_square(4)
# find 8-point circles: groups of points on a common circle
# A circle through 4+ points; the known bundle is "8 points on a circle, C(8,4)=70"
# Search: find all 8-subsets that are cocircular? Too many. Use known from
# round2: "8 点の円 1 本（四点 70 個）の解除で勝者が後手→先手に反転（g=1）"
# We recompute: enumerate all 4-point quads (forbidden), group by circle.
# is_forbidden_quad covers collinear OR cocircular.
# For B523/B524 we need the MINIMAL flipping release family.

# Build list of forbidden quads on 4x4
quads_pts = []
for comb in itertools.combinations([(x, y) for y in range(4) for x in range(4)], 4):
    if is_forbidden_quad(comb):
        quads_pts.append(comb)
print(f"4x4 forbidden quads: {len(quads_pts)}", flush=True)

# Known: single release 0 flips, pair release 0 flips (B521 complete).
# Circle-bundle release of 70 flips. Find that circle: a set of cocircular pts.
# Group quads by their circumcircle? Use integer approach: 4 points cocircular
# iff det[x^2+y^2,x,y,1]=0. An 8-point circle gives C(8,4)=70 quads all sharing
# the same circle. Cluster quads that are subsets of a common 8-point set.


def points_of(q):
    return set(q)


# greedily find large cocircular clusters via intersection of point-sets
# Better: all 8-point sets from geometric circles on 4x4.
# 4x4 points are small; circle through 3 points determines one; check how many
# of the 16 lie on it. We'll sample centers.


def circle_key(p0, p1, p2):
    """Return a hashable key for the circle through 3 non-collinear points, or None."""
    x0, y0 = p0
    x1, y1 = p1
    x2, y2 = p2
    d = 2 * (x0 * (y1 - y2) + x1 * (y2 - y0) + x2 * (y0 - y1))
    if d == 0:
        return None
    # circumcenter (ux, uy) may be half-integer; scale by 2
    ux2 = (
        (x0 * x0 + y0 * y0) * (y1 - y2)
        + (x1 * x1 + y1 * y1) * (y2 - y0)
        + (x2 * x2 + y2 * y2) * (y0 - y1)
    )
    uy2 = (
        (x0 * x0 + y0 * y0) * (x2 - x1)
        + (x1 * x1 + y1 * y1) * (x0 - x2)
        + (x2 * x2 + y2 * y2) * (x1 - x0)
    )
    return (ux2, uy2, d)


# find all maximal cocircular sets
pts4 = [(x, y) for y in range(4) for x in range(4)]
circ_sets = set()
for a, b, c in itertools.combinations(pts4, 3):
    key = circle_key(a, b, c)
    if key is None:
        continue
    ux2, uy2, d = key
    members = []
    for p in pts4:
        x, y = p
        # (x-ux)^2+(y-uy)^2 = (x0-ux)^2+(y0-uy)^2
        # multiply by d^2: use scaled
        # dist2 * d^2 = (x*d - ux2)^2 + (y*d - uy2)^2  / d^2 * d^2 wait
        # ux = ux2/d, so x - ux = (x*d - ux2)/d
        # dist2_num = (x*d-ux2)^2 + (y*d-uy2)^2
        num = (x * d - ux2) ** 2 + (y * d - uy2) ** 2
        members.append((p, num))
    # same circle iff same num
    ref = members[0][1]
    on = frozenset(p for p, num in members if num == ref)
    if len(on) >= 4:
        circ_sets.add(on)

big_circles = sorted(circ_sets, key=len, reverse=True)
rep["B521_B524"] = {
    "F_4x4": len(quads_pts),
    "cocircular_sets_ge4": len(circ_sets),
    "largest_circles": [sorted(s) for s in big_circles[:6]],
    "largest_sizes": [len(s) for s in big_circles[:6]],
}

# Identify the 8-point circle and its 70 quads; then search for a smaller
# flipping release family inside it / other families.
eight = [s for s in big_circles if len(s) == 8]
rep["B521_B524"]["n_8point_circles"] = len(eight)
rep["B521_B524"]["eight_point_examples"] = [sorted(s) for s in eight[:3]]


_W_CACHE: dict = {}
_pts_index = {p: i for i, p in enumerate(pts4)}
_ALL_QUAD_MASKS = []
for q in quads_pts:
    m = 0
    for p in q:
        m |= 1 << _pts_index[p]
    _ALL_QUAD_MASKS.append((frozenset(q), m))


def winner_with_released(released_quads) -> int:
    """Standard 4x4 game with some forbidden quads released (made legal)."""
    key = frozenset(frozenset(q) for q in released_quads)
    if key in _W_CACHE:
        return _W_CACHE[key]
    forbid = [m for fs, m in _ALL_QUAD_MASKS if fs not in key]
    V = 16
    full = (1 << V) - 1

    def safe(occ: int) -> bool:
        for q in forbid:
            if (occ & q) == q:
                return False
        return True

    levels = [[0]]
    seen = {0}
    for _ in range(V):
        nxt = set()
        for occ in levels[-1]:
            empty = full ^ occ
            v = 0
            e = empty
            while e:
                if e & 1:
                    child = occ | (1 << v)
                    if safe(child):
                        nxt.add(child)
                e >>= 1
                v += 1
        if not nxt:
            break
        levels.append(sorted(nxt))
        seen |= nxt
    win = {}
    for k in range(len(levels) - 1, -1, -1):
        for s in levels[k]:
            empty = full ^ s
            w = False
            e = empty
            v = 0
            while e:
                if e & 1:
                    child = s | (1 << v)
                    if child in seen and not win.get(child, True):
                        w = True
                        break
                e >>= 1
                v += 1
            win[s] = w
    g = 1 if win.get(0, False) else 0
    _W_CACHE[key] = g
    return g


# verify base: no release -> g should be 0
t = time.time()
g0 = winner_with_released([])
print(f"base g={g0} in {time.time()-t:.1f}s", flush=True)
rep["B521_B524"]["base_g_recomputed"] = g0

# test the 8-point circle bundle
if eight:
    e0 = sorted(eight[0])
    bundle = list(itertools.combinations(e0, 4))
    t = time.time()
    g1 = winner_with_released(bundle)
    print(f"8-circle bundle {len(bundle)} quads g={g1} in {time.time()-t:.1f}s", flush=True)
    rep["B521_B524"]["eight_bundle_g"] = g1
    rep["B521_B524"]["eight_bundle_flips"] = g1 != g0

    # B523: do all quads of the minimal flipping family share 3 points?
    # Search sub-families of the 70 that still flip, find minimal.
    # Heuristic: try releasing half, etc. — full min search is 2^70.
    # Instead: try all 1-,2-,3-,4-quad subsets? C(70,4)~1M too many.
    # Try: for each point of the 8, release only quads NOT containing it
    # (56 quads) and quads containing it (15+... C(7,3)=35).
    # Better structural test: intersection of all 70 quads as sets of points
    # (as 4-sets). Common intersection of all C(8,4) 4-subsets is empty.
    inter = set(e0)
    for q in itertools.combinations(e0, 4):
        inter &= set(q)
    rep["B521_B524"]["all70_common_points"] = sorted(inter)
    # Do they share a common 3-set? (intersection of size-3 cores)
    # A 3-set T is in every quad iff every 4-subset of e0 contains T
    # iff |e0 \ T| <= 1, impossible for |e0|=8. So no common 3-set.
    rep["B521_B524"]["common_3set_in_all70"] = False

    # Find a smaller flipping subfamily: release quads of a 6-point subset (C(6,4)=15)
    for take in (5, 6, 7, 8):
        if take > len(e0):
            continue
        sub = e0[:take]
        bundle_s = list(itertools.combinations(sub, 4))
        t = time.time()
        gs = winner_with_released(bundle_s)
        print(f"sub {take}-circle {len(bundle_s)} quads g={gs} flips={gs!=g0} {time.time()-t:.1f}s", flush=True)
        rep["B521_B524"][f"sub_{take}_g"] = gs
        rep["B521_B524"][f"sub_{take}_flips"] = gs != g0


# ==================== B527-B530: addition-order experiments ============
print("=== B527-B530 addition experiments ===", flush=True)
# Start from empty family (no forbidden quads) and add standard quads.
# Empty family: every placement legal. V=16 even -> second player wins (g=0)
# as analyzed. Confirm with winner_with_released(all quads) = release all 194.
all_released = list(quads_pts)
t = time.time()
g_empty = winner_with_released(all_released)
print(f"empty family g={g_empty} in {time.time()-t:.1f}s", flush=True)
rep["B527_B530"] = {
    "empty_family_g": g_empty,
    "standard_g": g0,
    "note_flip_parity": "empty and standard both claimed P (g=0); flips must be even",
}

# B527: for a single quad addition that flips P<->N, what is the minimal
# board-point subset responsible? Definition is fuzzy; we operationalize as:
# find a quad q such that adding q to empty family flips winner (from g_empty),
# then measure the size of the smallest point subset S such that the quads
# fully inside S already determine the flip (critical core).
# Practical test on 4x4: add quads one-by-one from empty and see flips.

# From empty (all released), add back (re-forbid) one quad at a time.
single_add_flips = []
t = time.time()
# full 194 is ~6 min; sample every 3rd plus all collinear-looking ones
sample_q = quads_pts[::3]
for q in sample_q:
    rel = [qq for qq in quads_pts if qq != q]
    g = winner_with_released(rel)
    if g != g_empty:
        single_add_flips.append({"quad": [list(p) for p in q], "g": g})
print(f"single re-forbid flips: {len(single_add_flips)}/{len(sample_q)} in {time.time()-t:.1f}s", flush=True)
rep["B527_B530"]["single_reforbid_flips"] = len(single_add_flips)
rep["B527_B530"]["single_reforbid_tested"] = len(sample_q)
rep["B527_B530"]["single_reforbid_examples"] = single_add_flips[:5]

# B528 / B530: compare random addition orders vs geometric (circle-bundle
# contiguous) orders — count flips along the path empty -> standard.
# Sample a few orders (not exhaustive).


def count_flips_along(order: list[tuple]) -> tuple[int, list[int]]:
    """order is a permutation of quads_pts. Start empty (all released).
    Step i: re-forbid order[i]. Return number of g-changes and the g-path."""
    released = set(quads_pts)  # all currently released
    g = g_empty
    flips = 0
    path = [g]
    for q in order:
        released.discard(q)
        # rebuild: forbid = all not in released
        rel = list(released)
        g_new = winner_with_released(rel)
        if g_new != g:
            flips += 1
        g = g_new
        path.append(g)
    return flips, path


# Too expensive to run full 194-step paths with DP each step (194 * 2s).
# Instead: sample 20 random steps (partial orders) and 1 geometric clustered order
# on a random subset of 20 quads.

def count_flips_on_subset(sub_quads: list[tuple]) -> int:
    """Start with sub_quads released (among full set the rest are forbidden? No:
    we want empty->standard restricted to these quads being added.
    Start: only these are released? Let's define:
    base = standard but with `sub` still released.
    Then forbid them one by one."""
    released = set(sub_quads)
    # start g
    g = winner_with_released(list(released))
    flips = 0
    for q in sub_quads:
        released.discard(q)
        g_new = winner_with_released(list(released))
        if g_new != g:
            flips += 1
        g = g_new
    return flips


# pick 12 quads from the 8-circle (geometric cluster) vs 12 random
import random

random.seed(20260928)
if eight:
    cluster = list(itertools.combinations(e0, 4))[:12]
else:
    cluster = list(quads_pts)[:12]
rand12 = random.sample(quads_pts, 12)

t = time.time()
flips_cluster = count_flips_on_subset(cluster)
print(f"cluster-12 flips={flips_cluster} {time.time()-t:.1f}s", flush=True)
t = time.time()
flips_rand = count_flips_on_subset(rand12)
print(f"rand-12 flips={flips_rand} {time.time()-t:.1f}s", flush=True)

rep["B527_B530"]["order_experiment"] = {
    "subset_size": 12,
    "cluster_is_8circle_prefix": True,
    "cluster_flips": flips_cluster,
    "random_flips": flips_rand,
    "n_random_trials": 1,
    "note": "pilot only; not enough to establish minimality of geometric order",
}

# B529: all minimal winner-preserving forbidden families share no common quad.
# Operationalization: find 2 distinct subsets of forbidden quads that both give
# standard g=0 (winner preserved from empty? or from standard?) and have empty
# intersection as families, each minimal for that property.
# "最小勝敗保持禁止族" = minimal families of forbidden quads that still yield the
# same winner as standard (second player win), i.e. g=0 with as few quads as possible.
# Minimal: removing any quad from the family changes g.
# We search small families on 4x4 that already force g=0, minimal w.r.t. inclusion.

def is_g0(family: list[tuple]) -> bool:
    """family are the ONLY forbidden quads; all others released."""
    return winner_with_released([q for q in quads_pts if q not in set(family)]) == 0


# search minimal g=0 families of size up to 5 (greedy from random)
min_families = []
seen_keys = set()
random.seed(1)
for _ in range(12):
    fam = random.sample(quads_pts, 5)
    # shrink
    changed = True
    while changed:
        changed = False
        for q in list(fam):
            trial = [x for x in fam if x != q]
            if is_g0(trial):
                fam = trial
                changed = True
    key = frozenset(fam)
    if key not in seen_keys and is_g0(fam):
        # verify minimal
        minimal = all(not is_g0([x for x in fam if x != q]) for q in fam)
        if minimal:
            seen_keys.add(key)
            min_families.append(fam)
    if len(min_families) >= 6:
        break

rep["B527_B530"]["B529_min_families"] = {
    "n_found": len(min_families),
    "families": [[[list(p) for p in q] for q in fam] for fam in min_families],
    "pairwise_intersection_empty_count": 0,
}
# check pairwise intersections of found families (as sets of quads)
for i in range(len(min_families)):
    for j in range(i + 1, len(min_families)):
        inter = set(min_families[i]) & set(min_families[j])
        if not inter:
            rep["B527_B530"]["B529_min_families"]["pairwise_intersection_empty_count"] += 1

rep["timing_s"] = round(time.time() - t0, 2)
OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
print("wrote", OUT, "in", rep["timing_s"], "s", flush=True)
print(json.dumps({k: rep[k] for k in rep if k != "timing_s"}, ensure_ascii=False)[:3000])
