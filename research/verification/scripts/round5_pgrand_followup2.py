#!/usr/bin/env python3
"""Follow-up part 2: B514/B520 n=5 delta, B504 decoys, B507, B528/B530 orders."""
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
from kyouen_core import board_square, board_square_minus, is_forbidden_quad  # noqa: E402

OUT = REPO / "research" / "verification" / "round5_pgrand_followup.json"
DATA = REPO / "research" / "verification" / "data"
rep = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
t0 = time.time()


def xy(i, n):
    return (i % n, i // n)


def log(msg):
    print(f"[{time.time()-t0:7.1f}s] {msg}", flush=True)


# ---- fast 4x4 solver (same as part1) ----
PTS4 = [(x, y) for y in range(4) for x in range(4)]
IDX4 = {p: i for i, p in enumerate(PTS4)}
QUADS4 = []
for c in itertools.combinations(PTS4, 4):
    if is_forbidden_quad(c):
        m = 0
        for p in c:
            m |= 1 << IDX4[p]
        QUADS4.append(m)
F4 = len(QUADS4)
V4, N4 = 16, 1 << 16
CONTAINED = [0] * N4
for qi, q in enumerate(QUADS4):
    missing = ((1 << V4) - 1) ^ q
    sub = missing
    while True:
        occ = q | sub
        CONTAINED[occ] |= 1 << qi
        if sub == 0:
            break
        sub = (sub - 1) & missing
ORDER = sorted(range(N4), key=lambda x: -bin(x).count("1"))
_WCACHE = {}


def winner_released(released_qids) -> int:
    key = frozenset(released_qids)
    if key in _WCACHE:
        return _WCACHE[key]
    forbid_mask = (1 << F4) - 1
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


g_std = winner_released([])
log(f"std g={g_std}")

# ---- B528/B530: fewer, faster order experiments ----
log("=== B528/B530 ===")


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


def geometric_order():
    groups = {}
    for qi in range(F4):
        pts = sorted(PTS4[i] for i in range(16) if (QUADS4[qi] >> i) & 1)
        key = circle_key(pts[0], pts[1], pts[2])
        gk = ("line",) if key is None else ("circ", key)
        groups.setdefault(gk, []).append(qi)
    ordered = []
    for _, qs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        ordered.extend(qs)
    return ordered


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


rng = random.Random(20260928)
geo = geometric_order()
orders = [("geometric_cluster", geo), ("geometric_rev", list(reversed(geo)))]
for i in range(3):
    o = list(range(F4))
    rng.shuffle(o)
    orders.append((f"random{i}", o))

order_results = []
flip_q_counter = Counter()
for name, order in orders:
    t = time.time()
    fl, ev = full_path_flips(order)
    for e in ev:
        flip_q_counter[e["q"]] += 1
    order_results.append({"order": name, "flips": fl, "events_qids": [e["q"] for e in ev]})
    log(f"  {name}: flips={fl} ({time.time()-t:.1f}s)")

n_single = sum(1 for qi in range(F4) if winner_released([qi]) != g_std)
log(f"single-release flips={n_single}")

rep["B528_B530"] = {
    "empty_family_g": winner_released(list(range(F4))),
    "standard_g": g_std,
    "order_results": order_results,
    "flip_q_counts": {str(k): v for k, v in flip_q_counter.most_common(40)},
    "n_quads_ever_flip": len(flip_q_counter),
    "single_release_flips": n_single,
    "top_flip": flip_q_counter.most_common(12),
}

# ---- B514/B520 n=5 ----
log("=== B514/B520 ===")
raw = (DATA / "maximal_n5.bin").read_bytes()
n5_masks = struct.unpack("<%dQ" % (len(raw) // 8), raw)
k9_sets = [m for m in n5_masks if bin(m).count("1") == 9]
log(f"K9={len(k9_sets)}")


def hits_all(D):
    dm = 0
    for p in D:
        dm |= 1 << p
    return all((m & dm) != 0 for m in k9_sets)


tau5 = None
tau5_ex = []
for r in (1, 2, 3, 4):
    found = []
    for D in itertools.combinations(range(25), r):
        if hits_all(D):
            found.append(list(D))
            if len(found) >= 8:
                break
    if found:
        tau5 = r
        tau5_ex = found
        break
log(f"tau5={tau5} ex={tau5_ex[:3]}")

n2_hit = sum(1 for D in itertools.combinations(range(25), 2) if hits_all(D))
log(f"hit pairs={n2_hit}")

bd5 = board_square(5)
g5 = bd5.solve_outcomes().get(0, 0)
log(f"g5={g5}")


def g_after(ids):
    return board_square_minus(5, [xy(i, 5) for i in ids]).solve_outcomes().get(0, 0)


flip_del = []
t = time.time()
for i in range(25):
    g = g_after([i])
    if g != g5:
        flip_del.append({"deleted": [i], "g": g})
log(f"1pt flips={len(flip_del)} ({time.time()-t:.1f}s)")

if not flip_del:
    t = time.time()
    for i, j in itertools.combinations(range(25), 2):
        g = g_after([i, j])
        if g != g5:
            flip_del.append({"deleted": [i, j], "g": g})
    log(f"2pt flips={len(flip_del)} ({time.time()-t:.1f}s)")

delta_out5 = min((len(d["deleted"]) for d in flip_del), default=None)

# B520: all achieving sets (sample up to 25)
memo0 = bd5.solve_outcomes()
b520_all = []
if tau5 is not None:
    ach = [list(D) for D in itertools.combinations(range(25), tau5) if hits_all(D)]
    log(f"achieving sets size={tau5}: {len(ach)}")
    for D in ach[:25]:
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
    log(f"B520 W-preserved {n_pres}/{len(b520_all)}")

rep["B514_B520"] = {
    "n5_K9": len(k9_sets),
    "delta_K5": tau5,
    "delta_K5_examples": tau5_ex,
    "n5_hitting_pairs": n2_hit,
    "n5_empty_g": g5,
    "delta_out5": delta_out5,
    "delta_out5_flips": flip_del[:15],
    "gap5": (tau5 - delta_out5) if (tau5 and delta_out5) else None,
    "b520_achieving": b520_all,
    "delta_K7": 2,
}

# ---- B504 decoys n=3,4 ----
log("=== B504 ===")


def max_decoys_n(n):
    bd = board_square(n)
    memo = bd.solve_outcomes()
    max_d = -1
    example = None
    n_w1 = 0
    n_pos = 0

    def rec(occ, cand, k):
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
    "n5_known": {"max_decoys": 22, "points": [[4, 0], [0, 3]]},
}

# ---- B507 ----
log("=== B507 ===")
env = {
    "3": {"n4": "76/135", "n5": "2383/3360", "n6": "37/50"},
    "4": {"n4": "52379/113400", "n5": "212/315", "n6": "5162/6615"},
    "5": {"n4": "2653037/6350400", "n5": "12459851/23284800", "n6": "278099/423360"},
    "6": {"n5": "66591319117/112935513600", "n6": "19547575332391/33345696384000"},
    "7": {"n4": "1827569507/6054048000", "n5": "7245096190817424647/14960657835002880000",
          "n6": "3110287792947612381539/5469990520922928000000"},
}
cases = []
ok = True
for hs, row in env.items():
    h = int(hs)
    bound = Fraction(h, h + 1)
    for n, s in row.items():
        val = Fraction(s)
        good = val <= bound
        ok = ok and good
        cases.append({"h": h, "n": n, "val": str(val), "bound": str(bound), "ok": good})
log(f"B507 h/(h+1) ok={ok}")
rep["B507"] = {
    "envelope": env,
    "bound_h_over_h1_all_ok": ok,
    "bound_cases": cases,
    "argmax_h": {"n4": 3, "n5": 3, "n6": 4},
}

# ---- B505/B508/B510 ----
rep["B505"] = {
    "weak_form": "n<=5 N-positions with |W|/|L|>=1/2 have p_rand>=1/2",
    "status": "SUPPORTED (round5_b401_prand_stats.json complete scan, min=1/2)",
    "original_open": True,
}
rep["B508"] = {
    "weak_form": "exists n<=5 pair same p_rand and ratio gap >= 2/3",
    "status": "SUPPORTED (p_rand=2/3, 0/6 vs 4/6)",
    "original_open": True,
}
rep["B510"] = {
    "weak_form": "no n<=5 N-position has true winning move with strictly worst child p_rand",
    "status": "SUPPORTED (0 hits complete n=4,5)",
    "original_open": True,
}

rep["timing_s"] = round(time.time() - t0, 2)
OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
log(f"wrote {OUT}")
