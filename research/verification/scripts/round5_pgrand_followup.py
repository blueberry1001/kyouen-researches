#!/usr/bin/env python3
"""Fast 4x4 release-game solver + remaining follow-up items.

Optimized: precompute contained-quad masks per occupancy.
"""
from __future__ import annotations

import itertools
import json
import random
import struct
import sys
import time
from collections import Counter
from fractions import Fraction
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import (  # noqa: E402
    board_square,
    board_square_minus,
    is_forbidden_quad,
)

OUT = REPO / "research" / "verification" / "round5_pgrand_followup.json"
DATA = REPO / "research" / "verification" / "data"
rep: dict = {}
t0 = time.time()


def xy(i: int, n: int) -> tuple[int, int]:
    return (i % n, i // n)


def log(msg: str) -> None:
    print(f"[{time.time()-t0:7.1f}s] {msg}", flush=True)


# ---------------- 4x4 geometry ----------------
PTS4 = [(x, y) for y in range(4) for x in range(4)]
IDX4 = {p: i for i, p in enumerate(PTS4)}
QUADS4: list[int] = []
QUAD_FS: list[frozenset] = []
for c in itertools.combinations(PTS4, 4):
    if is_forbidden_quad(c):
        m = 0
        for p in c:
            m |= 1 << IDX4[p]
        QUADS4.append(m)
        QUAD_FS.append(frozenset(c))
F4 = len(QUADS4)
log(f"4x4 F={F4}")

V4 = 16
N4 = 1 << V4

# Precompute: for each occ, bitmask over quads that are fully contained
log("precomputing contained-quad masks...")
CONTAINED = [0] * N4
for qi, q in enumerate(QUADS4):
    # all occ that contain q: iterate supersets of q within 16 bits
    missing = ((1 << V4) - 1) ^ q
    sub = missing
    while True:
        occ = q | sub
        CONTAINED[occ] |= 1 << qi
        if sub == 0:
            break
        sub = (sub - 1) & missing

# Precompute popcount-descending order
ORDER = sorted(range(N4), key=lambda x: -bin(x).count("1"))
# Precompute children bit (empty positions) — computed on the fly is fine
log("precompute done")

_WCACHE: dict[frozenset, int] = {}


def winner_released(released_qids) -> int:
    key = frozenset(released_qids)
    hit = _WCACHE.get(key)
    if hit is not None:
        return hit
    forbid_mask = ((1 << F4) - 1)
    for q in key:
        forbid_mask &= ~(1 << q)
    legal = bytearray(N4)
    for occ in range(N4):
        legal[occ] = 1 if (CONTAINED[occ] & forbid_mask) == 0 else 0
    win = bytearray(N4)
    full = (1 << V4) - 1
    for occ in ORDER:
        if not legal[occ]:
            continue
        w = 0
        e = full ^ occ
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
    _WCACHE[key] = g
    return g


# ---------------- B522-B524 ----------------
log("=== B522-B524 ===")


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
for a, b, c in itertools.combinations(PTS4, 3):
    key = circle_key(a, b, c)
    if key is None:
        continue
    ux2, uy2, d = key
    ref = (a[0] * d - ux2) ** 2 + (a[1] * d - uy2) ** 2
    on = frozenset(p for p in PTS4 if (p[0] * d - ux2) ** 2 + (p[1] * d - uy2) ** 2 == ref)
    if len(on) >= 4:
        circ_sets.add(on)
eight = [s for s in circ_sets if len(s) == 8]
log(f"8-point circles: {len(eight)}")

g_std = winner_released([])
log(f"standard g={g_std}")

qid_of = {fs: qi for qi, fs in enumerate(QUAD_FS)}
e0 = sorted(eight[0])
bundle = [qid_of[frozenset(comb)] for comb in itertools.combinations(e0, 4)]
g_bundle = winner_released(bundle)
log(f"bundle={len(bundle)} g={g_bundle} flips={g_bundle != g_std}")


def minimize_family(fam: list[int]) -> list[int]:
    fam = list(fam)
    changed = True
    while changed:
        changed = False
        for q in list(fam):
            trial = [x for x in fam if x != q]
            if winner_released(trial) != g_std:
                fam = trial
                changed = True
    return fam


t = time.time()
min_fam = minimize_family(bundle)
log(f"greedy-min size={len(min_fam)} ({time.time()-t:.1f}s) qids={min_fam}")


def quads_common_points(qids) -> list[tuple[int, int]]:
    inter = None
    for q in qids:
        pts = frozenset(PTS4[i] for i in range(16) if (QUADS4[q] >> i) & 1)
        inter = pts if inter is None else (inter & pts)
    return sorted(inter) if inter else []


min_pts = quads_common_points(min_fam)
min_pts_set = frozenset(min_pts)
# common 3-subsets
common3 = [list(c) for c in itertools.combinations(min_pts, 3)] if len(min_pts) >= 3 else []
log(f"min family common points={min_pts}, common3={len(common3)}")

# inclusion-minimal?
incl_min = True
if min_fam:
    for q in min_fam:
        if winner_released([x for x in min_fam if x != q]) != g_std:
            incl_min = False
            break
log(f"inclusion-minimal={incl_min}")

# describe min family quads as point tuples
min_fam_pts = []
for q in min_fam:
    pts = sorted(PTS4[i] for i in range(16) if (QUADS4[q] >> i) & 1)
    min_fam_pts.append(pts)
log(f"min family quads: {min_fam_pts}")

# Triple search
rng = random.Random(20260928)
bundle_triple_flips = []
n_bt = 0
for trip in itertools.combinations(bundle, 3):
    n_bt += 1
    if winner_released(trip) != g_std:
        bundle_triple_flips.append(list(trip))
log(f"bundle triples={n_bt} flips={len(bundle_triple_flips)}")

rand_triple_flips = []
n_rt = 0
for _ in range(4000):
    trip = rng.sample(range(F4), 3)
    n_rt += 1
    if winner_released(trip) != g_std:
        rand_triple_flips.append(list(trip))
log(f"rand triples={n_rt} flips={len(rand_triple_flips)}")

# triples with 2 from min_fam and 1 other
min_triple_flips = []
if len(min_fam) >= 2:
    outside = [q for q in range(F4) if q not in set(min_fam)]
    for pair in itertools.combinations(min_fam, 2):
        for o in outside:
            trip = list(pair) + [o]
            if winner_released(trip) != g_std:
                min_triple_flips.append(trip)
    log(f"min_fam-pair+1 triples flips={len(min_triple_flips)}")

rep["B522_B524"] = {
    "F": F4,
    "standard_g": g_std,
    "eight_points": e0,
    "bundle_size": len(bundle),
    "bundle_g": g_bundle,
    "bundle_flips": g_bundle != g_std,
    "greedy_min_size": len(min_fam),
    "greedy_min_qids": min_fam,
    "greedy_min_quads_pts": min_fam_pts,
    "greedy_min_common_points": min_pts,
    "greedy_min_common_3sets": common3,
    "greedy_min_inclusion_minimal": incl_min,
    "bundle_triples_tested": n_bt,
    "bundle_triple_flips": bundle_triple_flips,
    "rand_triples_tested": n_rt,
    "rand_triple_flips": rand_triple_flips,
    "minfam_pair_plus1_triple_flips": min_triple_flips,
}

# ---------------- B528/B530 orders ----------------
log("=== B528/B530 orders ===")


def full_path_flips(order_qids):
    released = set(order_qids)
    g = winner_released(released)
    flips = 0
    events = []
    for q in order_qids:
        released.discard(q)
        g_new = winner_released(released)
        if g_new != g:
            flips += 1
            events.append({"q": q, "from": g, "to": g_new})
        g = g_new
    return flips, events


def geometric_order() -> list[int]:
    groups: dict = {}
    for qi, fs in enumerate(QUAD_FS):
        pts = sorted(fs)
        key = circle_key(pts[0], pts[1], pts[2])
        gk = ("line",) if key is None else ("circ", key)
        groups.setdefault(gk, []).append(qi)
    ordered = []
    for _, qs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        ordered.extend(qs)
    return ordered


geo = geometric_order()
orders = [("geometric_cluster", geo), ("geometric_rev", geo[::-1])]
for i in range(5):
    o = list(range(F4))
    rng.shuffle(o)
    orders.append((f"random{i}", o))

order_results = []
flip_q_counter: Counter = Counter()
for name, order in orders:
    t = time.time()
    fl, ev = full_path_flips(order)
    for e in ev:
        flip_q_counter[e["q"]] += 1
    order_results.append({"order": name, "flips": fl, "events_qids": [e["q"] for e in ev]})
    log(f"  {name}: flips={fl} ({time.time()-t:.1f}s)")

n_single = 0
single_flip_q = []
for qi in range(F4):
    if winner_released([qi]) != g_std:
        n_single += 1
        single_flip_q.append(qi)
log(f"single-release flips={n_single}/{F4}")

rep["B528_B530"] = {
    "empty_family_g": winner_released(range(F4)),
    "standard_g": g_std,
    "order_results": order_results,
    "flip_q_counts": {str(k): v for k, v in flip_q_counter.most_common(40)},
    "n_quads_ever_flip_in_orders": len(flip_q_counter),
    "single_release_flips": n_single,
    "single_release_flip_qids": single_flip_q,
    "top_flip": flip_q_counter.most_common(15),
}

# ---------------- B514/B520 n=5 ----------------
log("=== B514/B520 n=5 ===")
raw = (DATA / "maximal_n5.bin").read_bytes()
n5_masks = struct.unpack("<%dQ" % (len(raw) // 8), raw)
k9_sets = [m for m in n5_masks if bin(m).count("1") == 9]
log(f"K=9 sets={len(k9_sets)}")


def hits_all_n5(D) -> bool:
    dm = 0
    for p in D:
        dm |= 1 << p
    return all((m & dm) != 0 for m in k9_sets)


tau5 = None
tau5_examples = []
for r in (1, 2, 3, 4):
    found = []
    for D in itertools.combinations(range(25), r):
        if hits_all_n5(D):
            found.append(list(D))
            if len(found) >= 8:
                break
    if found:
        tau5 = r
        tau5_examples = found
        break
log(f"delta_K(5)=tau={tau5} examples={tau5_examples[:3]}")

n2_hit = sum(1 for D in itertools.combinations(range(25), 2) if hits_all_n5(D))
log(f"hitting pairs={n2_hit}")

bd5 = board_square(5)
g5_empty = bd5.solve_outcomes().get(0, 0)
log(f"n=5 empty g={g5_empty}")


def g_after(ids):
    b = board_square_minus(5, [xy(i, 5) for i in ids])
    return b.solve_outcomes().get(0, 0)


flip_del = []
t = time.time()
for i in range(25):
    g = g_after([i])
    if g != g5_empty:
        flip_del.append({"deleted": [i], "g": g})
log(f"1-pt flips={len(flip_del)} ({time.time()-t:.1f}s)")

if not flip_del:
    t = time.time()
    for i, j in itertools.combinations(range(25), 2):
        g = g_after([i, j])
        if g != g5_empty:
            flip_del.append({"deleted": [i, j], "g": g})
    log(f"2-pt flips={len(flip_del)} ({time.time()-t:.1f}s)")

delta_out5 = min((len(d["deleted"]) for d in flip_del), default=None)

b520 = None
if tau5_examples:
    D = tau5_examples[0]
    bdel = board_square_minus(5, [xy(i, 5) for i in D])
    Kdel = bdel.max_safe_size()
    gdel = bdel.solve_outcomes().get(0, 0)
    memo = bdel.solve_outcomes()
    memo0 = bd5.solve_outcomes()
    remaining = sorted(i for i in range(25) if i not in set(D))
    mism = []
    for ri, orig in enumerate(remaining):
        wred = 1 if memo.get(1 << ri, 1) == 0 else 0
        worig = 1 if memo0.get(1 << orig, 1) == 0 else 0
        if wred != worig:
            mism.append(orig)
    b520 = {
        "D_ids": D,
        "K_after": Kdel,
        "g_after": gdel,
        "g_before": g5_empty,
        "w_mismatches": mism,
        "w_preserved_on_remaining": len(mism) == 0,
        "n_remaining": len(remaining),
    }
    log(f"B520 D={D} K={Kdel} g={gdel} mism={len(mism)}")

# Also try ALL tau5 achieving sets for B520 W-preservation
b520_all = []
if tau5 is not None and tau5 <= 3:
    # enumerate all achieving sets of size tau5 (or sample if many)
    ach = []
    for D in itertools.combinations(range(25), tau5):
        if hits_all_n5(D):
            ach.append(list(D))
    log(f"all delta_K achieving sets size={tau5}: {len(ach)}")
    for D in ach[:20]:
        bdel = board_square_minus(5, [xy(i, 5) for i in D])
        gdel = bdel.solve_outcomes().get(0, 0)
        memo = bdel.solve_outcomes()
        remaining = sorted(i for i in range(25) if i not in set(D))
        mism = []
        for ri, orig in enumerate(remaining):
            wred = 1 if memo.get(1 << ri, 1) == 0 else 0
            worig = 1 if memo0.get(1 << orig, 1) == 0 else 0
            if wred != worig:
                mism.append(orig)
        b520_all.append({
            "D_ids": D,
            "g_after": gdel,
            "w_mismatches": mism,
            "w_preserved": len(mism) == 0,
        })
    n_pres = sum(1 for x in b520_all if x["w_preserved"])
    log(f"B520 among {len(b520_all)} achieving sets, W-preserved={n_pres}")

rep["B514_B520"] = {
    "n5_K9_sets": len(k9_sets),
    "delta_K5": tau5,
    "delta_K5_examples": tau5_examples,
    "n5_hitting_pairs": n2_hit,
    "n5_empty_g": g5_empty,
    "delta_out5": delta_out5,
    "delta_out5_flips": flip_del[:15],
    "gap5": (tau5 - delta_out5) if (tau5 and delta_out5) else None,
    "b520_first_witness": b520,
    "b520_all_achieving": b520_all,
    "delta_K7": 2,
}

# ---------------- B504 n=3,n=4 decoys ----------------
log("=== B504 decoys ===")


def max_decoys_n(n: int) -> dict:
    bd = board_square(n)
    memo = bd.solve_outcomes()
    max_d = -1
    example = None
    n_w1 = 0
    n_pos = 0

    def rec(occ: int, cand: int, k: int):
        nonlocal max_d, example, n_w1, n_pos
        moves = bd.legal_moves(occ)
        if moves:
            n_pos += 1
            W = sum(1 for u in moves if memo.get(occ | (1 << u), 1) == 0)
            if W == 1:
                n_w1 += 1
                n_lose = len(moves) - W
                decoys = n_lose - W
                if decoys > max_d:
                    max_d = decoys
                    example = {
                        "points": [xy(v, n) for v in range(bd.V) if (occ >> v) & 1],
                        "k": k,
                        "n_legal": len(moves),
                        "W": W,
                        "L": n_lose,
                        "decoys": decoys,
                    }
        remain = cand
        while remain:
            b = remain & -remain
            v = b.bit_length() - 1
            remain ^= b
            nxt = occ | b
            if bd.is_safe(nxt):
                rec(nxt, remain, k + 1)

    rec(0, bd.full, 0)
    return {"max_decoys": max_d, "n_pos": n_pos, "n_W1": n_w1, "example": example}


n3d = max_decoys_n(3)
log(f"n3 {n3d}")
n4d = max_decoys_n(4)
log(f"n4 {n4d}")

rep["B504"] = {
    "n3": n3d,
    "n4": n4d,
    "n5_known": {"max_decoys": 22, "points": [[4, 0], [0, 3]], "occ": 32784},
}

# ---------------- B507 envelope ----------------
log("=== B507 ===")
env = {
    "3": {"n4": "76/135", "n5": "2383/3360", "n6": "37/50"},
    "4": {"n4": "52379/113400", "n5": "212/315", "n6": "5162/6615"},
    "5": {"n4": "2653037/6350400", "n5": "12459851/23284800", "n6": "278099/423360"},
    "6": {"n5": "66591319117/112935513600", "n6": "19547575332391/33345696384000"},
    "7": {"n4": "1827569507/6054048000", "n5": "7245096190817424647/14960657835002880000",
          "n6": "3110287792947612381539/5469990520922928000000"},
}
cand_ok = True
cand_cases = []
for hs, row in env.items():
    h = int(hs)
    bound = Fraction(h, h + 1)
    for n, s in row.items():
        val = Fraction(s)
        ok = val <= bound
        cand_ok = cand_ok and ok
        cand_cases.append({"h": h, "n": n, "val": str(val), "bound": str(bound), "ok": ok})
log(f"B507 h/(h+1) all_ok={cand_ok}")

rep["B507"] = {
    "envelope": env,
    "bound_h_over_h1_all_ok": cand_ok,
    "bound_cases": cand_cases,
    "argmax_h": {"n4": 3, "n5": 3, "n6": 4},
}

# ---------------- B505/B508/B510 existing-data weak forms ----------------
rep["B505"] = {
    "weak_form": "n<=5 all N-positions with |W|/|L|>=1/2 have p_rand>=1/2",
    "status": "SUPPORTED (round5_b401_prand_stats.json complete scan)",
    "original": "unbounded [存在] remains open",
}
rep["B508"] = {
    "weak_form": "exists n<=5 pair with same p_rand and ratio gap >= 2/3",
    "status": "SUPPORTED (p_rand=2/3, ratios 0/6 vs 4/6)",
    "original": "arbitrarily large gap open",
}
rep["B510"] = {
    "weak_form": "no n<=5 N-position has true winning move with strictly worst child p_rand",
    "status": "SUPPORTED (0 hits complete n=4,5)",
    "original": "unbounded [存在] open",
}

rep["timing_s"] = round(time.time() - t0, 2)
OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
log(f"wrote {OUT}")
