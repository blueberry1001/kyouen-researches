#!/usr/bin/env python3
"""round5 pgrand residual — fast pass for B512-B530.

Known from the timed-out run (recomputed here only what is cheap):
  n=4 pairs: K_drops=0, flip_pairs=12
  n=4 triples: K_drops=0, triple_flips=140, pure3=12
  n=3: K_drops=8, flips=8
This script redoes n=4 flip sets (needed for B519 minimality), then
B513 hitting number, B519 size-4, B521-B530 pilots. n=5 is K-only sample.
"""
from __future__ import annotations

import itertools
import json
import random
import struct
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import board_square_minus, is_forbidden_quad  # noqa: E402

OUT = REPO / "research" / "verification" / "round5_pgrand.json"
NIGHT = REPO / "night-research"
rep: dict = {}
t0 = time.time()


def xy(i: int, n: int) -> tuple[int, int]:
    return (i % n, i // n)


def solve_K(n: int, deleted_ids) -> int:
    bd = board_square_minus(n, [xy(i, n) for i in deleted_ids])
    return bd.max_safe_size()


def solve_K_g(n: int, deleted_ids) -> tuple[int, int]:
    bd = board_square_minus(n, [xy(i, n) for i in deleted_ids])
    K = bd.max_safe_size()
    g = bd.solve_outcomes().get(0, 0)
    return K, g


# ==================== n=4 flip/K sets (for B512/B514/B519) ==============
print("=== n=4 flips (pairs+triples) ===", flush=True)
n = 4
base_K, base_g = 7, 0
flip_pairs = []
flip_triples = []
for i, j in itertools.combinations(range(16), 2):
    K, g = solve_K_g(n, (i, j))
    if g != base_g:
        flip_pairs.append((i, j))
    if K < base_K:
        rep.setdefault("B512_n4_Kdrops", []).append({"deleted": [i, j], "K": K})
print(f"pairs flips={len(flip_pairs)}", flush=True)

t = time.time()
for trip in itertools.combinations(range(16), 3):
    K, g = solve_K_g(n, trip)
    if g != base_g:
        flip_triples.append(trip)
    if K < base_K:
        rep.setdefault("B512_n4_Kdrops", []).append({"deleted": list(trip), "K": K})
print(f"triples flips={len(flip_triples)} K_drops={len(rep.get('B512_n4_Kdrops', []))} {time.time()-t:.1f}s", flush=True)

# pure3
pure3 = []
flip_set = set(flip_pairs) | set(flip_triples)
for trip in flip_triples:
    if all(tuple(sub) not in flip_set for sub in itertools.combinations(trip, 2)):
        pure3.append(trip)
print(f"pure3={len(pure3)}", flush=True)

rep["B512"] = {
    "n4": {
        "base_K": base_K,
        "base_g": base_g,
        "K_drops": rep.get("B512_n4_Kdrops", []),
        "n_K_drops": len(rep.get("B512_n4_Kdrops", [])),
        "n_flip_pairs": len(flip_pairs),
        "flip_pairs": [list(p) for p in flip_pairs],
        "n_flip_triples": len(flip_triples),
        "n_pure_triple_flips": len(pure3),
        "pure_triple_flips": [list(p) for p in pure3],
        "delta_K_n4": ">=4",
        "delta_out_n4": 2,
    }
}

# n=3 fast
print("=== n=3 ===", flush=True)
bK3, bG3 = solve_K_g(3, ())
drops3, flips3 = [], []
for r in (1, 2, 3):
    for dele in itertools.combinations(range(9), r):
        K, g = solve_K_g(3, dele)
        if K < bK3:
            drops3.append((dele, K))
        if g != bG3:
            flips3.append((dele, K, g))
rep["B512"]["n3"] = {
    "base_K": bK3,
    "base_g": bG3,
    "n_K_drops": len(drops3),
    "min_K_drop_size": min((len(d[0]) for d in drops3), default=None),
    "K_drops": [{"deleted": list(d[0]), "K": d[1]} for d in drops3],
    "n_flips": len(flips3),
    "min_flip_size": min((len(d[0]) for d in flips3), default=None),
    "flips": [{"deleted": list(d[0]), "K": d[1], "g": d[2]} for d in flips3],
}
print("n3", rep["B512"]["n3"]["n_K_drops"], rep["B512"]["n3"]["n_flips"], flush=True)

rep["B514"] = {
    "n3": {
        "delta_out": rep["B512"]["n3"]["min_flip_size"],
        "delta_K": rep["B512"]["n3"]["min_K_drop_size"],
        "gap": (
            rep["B512"]["n3"]["min_K_drop_size"] - rep["B512"]["n3"]["min_flip_size"]
            if rep["B512"]["n3"]["min_K_drop_size"] and rep["B512"]["n3"]["min_flip_size"]
            else None
        ),
    },
    "n4": {
        "delta_out": 2,
        "delta_K": ">=4",
        "gap": ">=2",
    },
}

# ==================== B513 ==============================================
print("=== B513 ===", flush=True)
raw = (NIGHT / "maxsafe_n7_K14.bin").read_bytes()
masks = struct.unpack("<" + "Q" * (len(raw) // 8), raw)
sets7 = [frozenset(j for j in range(49) if (m >> j) & 1) for m in masks]
assert all(len(s) == 14 for s in sets7)


def hits_all(D) -> bool:
    D = frozenset(D)
    return all(s & D for s in sets7)


tau = None
tau_examples = []
for r in (1, 2, 3, 4):
    found = []
    for D in itertools.combinations(range(49), r):
        if hits_all(D):
            found.append(list(D))
            if len(found) >= 8:
                break
    if found:
        tau = r
        tau_examples = found
        break

n2_hit = sum(1 for D in itertools.combinations(range(49), 2) if hits_all(D))
n3_hit = 0
for D in itertools.combinations(range(49), 3):
    if hits_all(D):
        n3_hit += 1

corners = [0, 6, 42, 48]
corner_triples = [{"D": list(t), "hits_all": hits_all(t)} for t in itertools.combinations(corners, 3)]
corner_pairs = [{"D": list(p), "hits_all": hits_all(p)} for p in itertools.combinations(corners, 2)]

rep["B513"] = {
    "n_sets": 16,
    "tau": tau,
    "tau_examples": tau_examples,
    "n_2sets_hitting_all": n2_hit,
    "n_3sets_hitting_all": n3_hit,
    "corner_triples": corner_triples,
    "corner_pairs": corner_pairs,
    "delta_K_7_equals_tau": True,
    "note": "All 14-stone safe sets on 7x7 are exactly these 16 (K=14). "
            "D lowers K iff D hits every one of them. Hence delta_K(7)=tau.",
}
print("tau", tau, "n2_hit", n2_hit, "n3_hit", n3_hit, flush=True)

# ==================== B519 ==============================================
print("=== B519 n=3 min flips size<=4, n=4 size-4 ===", flush=True)
# n=3
bK3, bG3 = solve_K_g(3, ())
flip_all3 = set()
for r in (1, 2, 3, 4):
    for dele in itertools.combinations(range(9), r):
        K, g = solve_K_g(3, dele)
        if g != bG3:
            flip_all3.add(dele)
minimal3 = []
for S in flip_all3:
    if all(tuple(sub) not in flip_all3 for r in range(1, len(S)) for sub in itertools.combinations(S, r)):
        minimal3.append(S)


def has_quad(n, S) -> bool:
    pts = [xy(i, n) for i in S]
    return any(is_forbidden_quad(c) for c in itertools.combinations(pts, 4))


ge4 = [S for S in minimal3 if len(S) >= 4]
with_q = [S for S in ge4 if has_quad(3, S)]
without_q = [S for S in ge4 if not has_quad(3, S)]
rep["B519"] = {
    "n3": {
        "n_minimal": len(minimal3),
        "minimal_by_size": {str(sz): sum(1 for S in minimal3 if len(S) == sz) for sz in sorted({len(S) for S in minimal3})},
        "ge4_with_quad": len(with_q),
        "ge4_without_quad": [list(S) for S in without_q],
        "minimal_examples": [list(S) for S in minimal3[:12]],
    }
}

# n=4 size-4 minimal flips (subsets of size<=3 that flip are known)
flip_le3 = set(flip_pairs) | set(flip_triples)
min4 = []
t = time.time()
for quad in itertools.combinations(range(16), 4):
    if any(tuple(sub) in flip_le3 for r in (1, 2, 3) for sub in itertools.combinations(quad, r)):
        continue
    K, g = solve_K_g(4, quad)
    if g != base_g:
        min4.append(quad)
print(f"n4 min size-4 flips: {len(min4)} {time.time()-t:.1f}s", flush=True)
with_q4 = [S for S in min4 if has_quad(4, S)]
without_q4 = [S for S in min4 if not has_quad(4, S)]
rep["B519"]["n4"] = {
    "n_size4_minimal_flips": len(min4),
    "with_forbidden_quad": len(with_q4),
    "without_forbidden_quad": [list(S) for S in without_q4[:12]],
    "examples_with_q": [list(S) for S in with_q4[:8]],
    "note": "size<=3 minimal flips are the 12 pure triples (plus smaller); "
            "B519 claims size>=4 minimal must contain a forbidden quad.",
}
print("n4 with_q", len(with_q4), "without", len(without_q4), flush=True)

# ==================== B520 ==============================================
rep["B520"] = {
    "n4": "no K-drop at |D|<=3, so no delta_K-achieving set on n=4 to test W-preservation",
    "n7": f"delta_K=tau={tau}; W-preservation on 7x7-minus needs full DP (46 pts) — not run (n>=7 full calc forbidden)",
}

# ==================== B521-B524 ========================================
print("=== B521-B524 ===", flush=True)
pts4 = [(x, y) for y in range(4) for x in range(4)]
quads_pts = [c for c in itertools.combinations(pts4, 4) if is_forbidden_quad(c)]
print("F", len(quads_pts), flush=True)


def circle_key(p0, p1, p2):
    x0, y0 = p0
    x1, y1 = p1
    x2, y2 = p2
    d = 2 * (x0 * (y1 - y2) + x1 * (y2 - y0) + x2 * (y0 - y1))
    if d == 0:
        return None
    ux2 = (x0 * x0 + y0 * y0) * (y1 - y2) + (x1 * x1 + y1 * y1) * (y2 - y0) + (x2 * x2 + y2 * y2) * (y0 - y1)
    uy2 = (x0 * x0 + y0 * y0) * (x2 - x1) + (x1 * x1 + y1 * y1) * (x0 - x2) + (x2 * x2 + y2 * y2) * (x1 - x0)
    return (ux2, uy2, d)


circ_sets = set()
for a, b, c in itertools.combinations(pts4, 3):
    key = circle_key(a, b, c)
    if key is None:
        continue
    ux2, uy2, d = key
    ref = (a[0] * d - ux2) ** 2 + (a[1] * d - uy2) ** 2
    on = frozenset(p for p in pts4 if (p[0] * d - ux2) ** 2 + (p[1] * d - uy2) ** 2 == ref)
    if len(on) >= 4:
        circ_sets.add(on)
big = sorted(circ_sets, key=len, reverse=True)
eight = [s for s in big if len(s) == 8]

_pts_index = {p: i for i, p in enumerate(pts4)}
_ALL_Q = []
for q in quads_pts:
    m = 0
    for p in q:
        m |= 1 << _pts_index[p]
    _ALL_Q.append((frozenset(q), m))
_W_CACHE = {}


def winner_with_released(released_quads) -> int:
    key = frozenset(frozenset(q) for q in released_quads)
    if key in _W_CACHE:
        return _W_CACHE[key]
    forbid = [m for fs, m in _ALL_Q if fs not in key]
    V = 16
    N = 1 << V
    legal = bytearray(N)
    for occ in range(N):
        ok = 1
        for q in forbid:
            if (occ & q) == q:
                ok = 0
                break
        legal[occ] = ok
    # win[occ] = current player can force a win
    win = bytearray(N)
    # process by descending popcount so children (occ|bit) have higher count already done
    # Actually children have MORE stones = higher popcount. Compute high -> low.
    order = sorted(range(N), key=lambda x: -bin(x).count("1"))
    for occ in order:
        if not legal[occ]:
            continue
        w = 0
        e = ((1 << V) - 1) ^ occ
        v = 0
        while e:
            if e & 1:
                child = occ | (1 << v)
                if legal[child] and win[child] == 0:
                    w = 1
                    break
            e >>= 1
            v += 1
        win[occ] = w
    g = win[0]
    _W_CACHE[key] = g
    return g


t = time.time()
g0 = winner_with_released([])
print("standard g", g0, time.time() - t, flush=True)

rep["B521_B524"] = {
    "F": len(quads_pts),
    "n_8point_circles": len(eight),
    "eight_examples": [sorted(s) for s in eight[:3]],
    "largest_circles": [sorted(s) for s in big[:4]],
    "standard_g": g0,
    "B521_existing": "SUPPORTED in round5-batch-b401-b600.md (18721 pairs, 0 flips)",
}

if eight:
    e0 = sorted(eight[0])
    bundle = list(itertools.combinations(e0, 4))
    t = time.time()
    g1 = winner_with_released(bundle)
    print("8-bundle g", g1, "flips", g1 != g0, time.time() - t, flush=True)
    rep["B521_B524"]["eight_bundle"] = {
        "n_quads": len(bundle),
        "g": g1,
        "flips": g1 != g0,
        "common_points_all70": sorted(set(e0)),
        "common_3set_in_all70": False,
    }
    # sub-families
    for take in (5, 6, 7):
        sub = e0[:take]
        b = list(itertools.combinations(sub, 4))
        t = time.time()
        gs = winner_with_released(b)
        print(f"sub{take} g", gs, "flips", gs != g0, time.time() - t, flush=True)
        rep["B521_B524"][f"sub_{take}"] = {"n_quads": len(b), "g": gs, "flips": gs != g0}

# B523/B524 structural: min flipping release family
# If 8-bundle flips but 7-sub doesn't, min family is in the 70.
# Check whether any proper subfamily of size C(8,4)-1 flips — too many.
# Instead: check shared-triple hypothesis on the 70 (already False).
rep["B523"] = {
    "status": "min flipping release family not yet isolated",
    "shared_3set_in_70": False,
    "note": "B523 claims min flip release families share 3 points. "
            "The known 70-quad circle bundle flips but has no common 3-set. "
            "If a smaller flipping family inside it shares 3 points, B523 survives; "
            "if the 70 itself is minimal, B523 is REFUTED for this witness.",
}
rep["B524"] = {
    "status": "depends on finding a min flip release family without common points",
    "note": "If the 70-bundle is minimal and has no common 3-set, it is a witness "
            "for B524 (no shared 3 points) — but B524 asks for no common POINT at all.",
}

# ==================== B527-B530 ========================================
print("=== B527-B530 ===", flush=True)
all_released = list(quads_pts)
t = time.time()
g_empty = winner_with_released(all_released)
print("empty g", g_empty, time.time() - t, flush=True)

# single re-forbid sample
sample_q = quads_pts[::3]
single_flips = []
t = time.time()
for q in sample_q:
    rel = [qq for qq in quads_pts if qq != q]
    g = winner_with_released(rel)
    if g != g_empty:
        single_flips.append([list(p) for p in q])
print("single flips", len(single_flips), "/", len(sample_q), time.time() - t, flush=True)

# order experiment on 12 quads
def count_flips_on_subset(sub_quads) -> int:
    released = set(sub_quads)
    g = winner_with_released(list(released))
    flips = 0
    for q in sub_quads:
        released.discard(q)
        g_new = winner_with_released(list(released))
        if g_new != g:
            flips += 1
        g = g_new
    return flips


random.seed(20260928)
if eight:
    cluster = list(itertools.combinations(e0, 4))[:12]
else:
    cluster = list(quads_pts)[:12]
rand12 = random.sample(quads_pts, 12)
t = time.time()
fl_c = count_flips_on_subset(cluster)
print("cluster12 flips", fl_c, time.time() - t, flush=True)
t = time.time()
fl_r = count_flips_on_subset(rand12)
print("rand12 flips", fl_r, time.time() - t, flush=True)

# B529 minimal g=0 families
def is_g0(family) -> bool:
    return winner_with_released([q for q in quads_pts if q not in set(family)]) == 0


min_families = []
seen_keys = set()
random.seed(1)
for _ in range(10):
    fam = random.sample(quads_pts, 5)
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
        if all(not is_g0([x for x in fam if x != q]) for q in fam):
            seen_keys.add(key)
            min_families.append(fam)

n_empty_inter = 0
for i in range(len(min_families)):
    for j in range(i + 1, len(min_families)):
        if not (set(min_families[i]) & set(min_families[j])):
            n_empty_inter += 1

rep["B527_B530"] = {
    "empty_family_g": g_empty,
    "standard_g": g0,
    "single_reforbid": {"tested": len(sample_q), "flips": len(single_flips), "examples": single_flips[:5]},
    "order_pilot": {
        "subset_size": 12,
        "cluster_flips": fl_c,
        "random_flips": fl_r,
        "n_random_trials": 1,
    },
    "B529_min_families": {
        "n_found": len(min_families),
        "sizes": [len(f) for f in min_families],
        "pairwise_empty_intersection_count": n_empty_inter,
        "families": [[[list(p) for p in q] for q in fam] for fam in min_families],
    },
}

rep["timing_s"] = round(time.time() - t0, 2)
OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
print("wrote", OUT, rep["timing_s"], flush=True)
