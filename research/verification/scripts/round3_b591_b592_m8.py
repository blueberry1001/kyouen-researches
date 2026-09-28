"""round3_b591_b592_m8.py — B591/B592, pass 4: build mathcal(M_8) by local search.

Pass 3 (`round3_b591_b592_pool.py`) established the operational fact that random
sampling cannot build the maximum-set family on B_8: a random 15-subset of the 64
points contains on average 42394 * C(15,4)/C(64,4) = 91 forbidden quads, so the
safe rate is far below 1e-4 and the pool came out empty.  Maximum sets must be
built by LOCAL SEARCH instead, seeded from the confirmed 15-stone witness in
`night-research/cycle6-maxsafeset-n8-15.json`.

That family size is itself the object B591/B592 turn on.  The d_max maxima of round 2
are 0,0,2,3,4,8 for n=2..7 while |M_n| is 56, 64, 100, 464, 16 for n=3..7; the n=7
value 8 is large because |M_7| = 16 is tiny.  So:

    d_max(S) <= |S| - max_{M in W} |S & M|   for every family W subset of M_n
                                             (rigorous upper bound)

gives, for the first time, an upper bound on the n=8 layer maximum, and a lower
bound on how large |M_8| must be for the n=7 behaviour to continue.

Integer arithmetic only.  Writes research/verification/round3_b591_b592_m8.json.
"""
from __future__ import annotations

import json
import random
import time
from pathlib import Path

import numpy as np

from round3_b591_core import (quads_np, build_qm, max_overlap, coords, popcount,
                              d4_perm, apply_perm)

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round3_b591_b592_m8.json"
DEADLINE = time.time() + 165.0
N, K, KS = 8, 15, 14
rng = random.Random(8151514)
out: dict = {"_meta": {"script": "round3_b591_b592_m8.py", "n": N, "K_n": K,
                        "layer_size": KS}}
t0 = time.time()
v = N * N
quads = quads_np(N)
out["_meta"]["F_n"] = len(quads)
out["_meta"]["expected_quads_in_random_15set"] = len(quads) * 1365 / 635376 * 635376 / 635376 * 0 + \
    round(len(quads) * 1365 / 635376, 3)
QM = build_qm(quads, v)
out["_meta"]["geom_sec"] = round(time.time() - t0, 2)


def left() -> float:
    return DEADLINE - time.time()


def safe(mask: int) -> bool:
    pts = [p for p in range(v) if (mask >> p) & 1]
    k = len(pts)
    for i in range(k):
        qp = QM[pts[i]]
        base = pts[i] * v
        for j in range(i + 1, k):
            m = qp.get(base + pts[j], 0)
            if m and (m & ~mask & ~((1 << pts[i]) | (1 << pts[j]))) != 0:
                return False
    return True


_POP = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)


def _pc(a):
    """popcount of each element of a uint64 array, preserving shape."""
    sh = a.shape
    flat = _POP[a.view(np.uint8).reshape(-1, 8)].sum(axis=1).astype(np.int16)
    return flat.reshape(sh)


def ub_batch(cands, pool):
    if not len(cands) or pool.shape[0] == 0:
        return np.zeros(0 if not len(cands) else len(cands), dtype=np.int16)
    s = np.array(list(cands), dtype=np.uint64).reshape(-1)
    best = np.zeros(len(cands), dtype=np.int16)
    step = max(1, 8_000_000 // max(1, len(cands)))
    for j0 in range(0, pool.shape[0], step):
        blk = pool[j0:j0 + step]
        np.maximum(best, _pc(s[:, None] & blk[None, :]).max(axis=1), out=best)
    return KS - best


KNOWN = [(0, 0), (1, 0), (2, 0), (1, 1), (7, 1), (3, 2), (7, 2), (5, 3),
         (0, 4), (2, 5), (4, 5), (5, 6), (0, 7), (4, 7), (5, 7)]
kmask = sum(1 << (y * N + x) for (x, y) in KNOWN)
out["_meta"]["known_witness_is_safe_15"] = bool(safe(kmask)) and popcount(kmask) == K

# ---------------------------------------------- local search over M_8 -----------
perms = d4_perm(N)
M: set[int] = {kmask}
for pm in perms:
    M.add(apply_perm(kmask, pm))
t1 = time.time()
cur = kmask
proposals = 0
while left() > 95:
    inside = [p for p in range(v) if (cur >> p) & 1]
    outside = [p for p in range(v) if not ((cur >> p) & 1)]
    a = rng.choice(inside)
    b = rng.choice(outside)
    t = (cur & ~(1 << a)) | (1 << b)
    proposals += 1
    if safe(t):
        cur = t
        M.add(cur)
        if proposals % 9 == 0:
            for pm in perms:
                M.add(apply_perm(cur, pm))
    if proposals % 4000 == 0 and left() > 95:
        cur = rng.choice(list(M))          # restart from a random family member
out["_meta"]["M8_search"] = {"proposals": proposals,
                             "distinct_max_sets_found": len(M),
                             "sec": round(time.time() - t1, 2)}
import struct as _struct
_bin = ROOT / "research" / "verification" / "round3_M8_pool.bin"
_bin.write_bytes(_struct.pack(f"<{len(M)}Q", *sorted(M)))
out["_meta"]["M8_search"]["bin"] = str(_bin.relative_to(ROOT)).replace("\\", "/")
pool = np.array(sorted(M), dtype=np.uint64)


def rand_safe(k: int, tries: int = 4000):
    for _ in range(tries):
        if left() < 8:
            return None
        m = 0
        for p in rng.sample(range(v), k):
            m |= 1 << p
        if safe(m):
            return m
    return None


# --------------- screen the K_n-1 layer with the rigorous pool upper bound ------
t2 = time.time()
seen: set[int] = set()
cands: list[int] = []
hist: dict[int, int] = {}
for _ in range(3000):
    if left() < 60:
        break
    s = rand_safe(KS)
    if s is not None and s not in seen:
        seen.add(s)
        cands.append(s)
n7_worst = [(0, 0), (1, 0), (1, 1), (5, 1), (6, 1), (0, 2), (2, 2), (3, 4),
            (6, 4), (4, 5), (1, 6), (2, 6), (3, 6)]
base = sum(1 << (y * N + x) for (x, y) in n7_worst)
seeds = []
for p in range(v):
    if not ((base >> p) & 1) and safe(base | (1 << p)):
        s = base | (1 << p)
        seeds.append(s)
        seen.add(s)
        cands.append(s)
out["_meta"]["n7_worst_growable_to_14"] = len(seeds)
for u in ub_batch(cands, pool).tolist():
    hist[u] = hist.get(u, 0) + 1
out["ub_hist_random_screened"] = {str(k): hist[k] for k in sorted(hist)}
out["_meta"]["screened"] = len(cands)
out["_meta"]["screen_sec"] = round(time.time() - t2, 2)

# ------------------------------ hill-climb 14-subsets on the pool upper bound ----
t3 = time.time()
best_m, best_u, climbs = None, -1, 0
while left() > 35:
    cur = rand_safe(KS)
    if cur is None:
        break
    climbs += 1
    curb = int(ub_batch([cur], pool)[0])
    hist[curb] = hist.get(curb, 0) + 1
    while left() > 35:
        inside = [p for p in range(v) if (cur >> p) & 1]
        outside = [p for p in range(v) if not ((cur >> p) & 1)]
        batch = []
        for a in inside:
            for b in outside:
                t = (cur & ~(1 << a)) | (1 << b)
                if t not in seen:
                    seen.add(t)
                    if safe(t):
                        batch.append(t)
        if not batch:
            break
        sc = ub_batch(batch, pool)
        for u in sc.tolist():
            hist[u] = hist.get(u, 0) + 1
        j = int(np.argmax(sc))
        if int(sc[j]) > curb:
            cur, curb = batch[j], int(sc[j])
        else:
            break
    if curb > best_u:
        best_u, best_m = curb, cur
out["_meta"]["climbs"] = climbs
out["_meta"]["climb_sec"] = round(time.time() - t3, 2)
out["ub_hist_all_screened"] = {str(k): hist[k] for k in sorted(hist)}
out["_meta"]["total_distinct_14sets_examined"] = len(seen)

# ------------------------------------------ exact d_max for the best 14-sets ----
exact = []
finals = []
if best_m is not None:
    finals.append(best_m)
finals += seeds[:3]
for m in finals:
    if m is None or left() < 8:
        break
    b, nodes, complete, sec = max_overlap(N, m, K, QM, v, node_budget=2_000_000)
    d = KS - b
    exact.append({"coords": coords(m, N),
                  "pool_ub": int(ub_batch([m], pool)[0]),
                  "max_overlap": b,
                  "dmax_exact": d if complete else None,
                  "dmax_certified_lower_bound": d,
                  "complete": complete, "nodes": nodes, "sec": sec})
    print(f"ub={int(ub_batch([m], pool)[0])} overlap={b} dmax>={d} "
          f"complete={complete} nodes={nodes}", flush=True)

out["_meta"]["total_sec"] = round(time.time() - t0, 2)
out["n8_layer_dmax_upper_bound"] = best_u
out["n8_layer_dmax_upper_bound_witness"] = coords(best_m, N) if best_m is not None else None
out["exact_checks"] = exact
lb = max([e["dmax_certified_lower_bound"] for e in exact], default=0)
ub = best_u
out["B592"] = {
    "label": "PARTIAL", "n": N,
    "certified_dmax_lower_bound_n8": lb,
    "certified_dmax_upper_bound_n8": ub,
    "bracket": [lb, ub],
    "dmax_over_n_bracket": [lb / N, (ub / N) if ub >= 0 else None],
    "round2_dmax_max_n2_to_n7": {"2": 0, "3": 0, "4": 2, "5": 3, "6": 4, "7": 8},
    "round2_max_set_counts_n3_to_n7": {"3": 56, "4": 64, "5": 100, "6": 464, "7": 16},
}
out["B591"] = {"label": "PARTIAL", "C_required_at_least": max(8, lb),
               "n8_layer_ub": ub}
OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
print("wrote", OUT, out["_meta"]["total_sec"], "s", flush=True)
print("|M_8| found:", out["_meta"]["M8_search"]["distinct_max_sets_found"], flush=True)
print("ub hist random screened:", out["ub_hist_random_screened"], flush=True)
print("ub hist all screened   :", out["ub_hist_all_screened"], flush=True)
print("n8 layer dmax bracket [lb, ub] =", [lb, ub], flush=True)
