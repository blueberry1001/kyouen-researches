"""round3_b591_b592.py — B591/B592 (round 3): extend the K_n-1 layer to n=8.

B591 [universal]  |S| = K_n - 1  =>  d_max(S) <= C  (absolute constant C)
B592 [existential] exists c>0 and a sequence of boards with d_max(S) >= c*n

Round 2 reached n=2..7 exactly (d_max max = 0,0,2,3,4,8).  The one-stone-deficient
layer of B_8 (K_8 = 15, so 14 stones) was never touched: the 14-subsets of a 64-point
board cannot be enumerated.  What CAN be done exactly:

  * d_max(S) = |S| - max_{M in mathcal(M_8)} |S & M|, and mathcal(M_8) = all safe
    15-subsets.  Hence for ANY subfamily W of mathcal(M_8):
        d_max(S) <= min_{M in W} |S \\ M|      (upper bound)
  * and a branch-and-bound that maximises |S & M| over ALL safe 15-subsets, run to
    completion, gives d_max(S) exactly.  Run with a node budget it still gives a
    *rigorous lower bound* d_max(S) >= |S| - best_overlap_found.

For B592 (an existence claim) rigorous LOWER bounds on d_max are exactly what is
needed, so an incomplete branch-and-bound is still a valid witness.  For B591
(a universal upper bound) only upper bounds count, and those come from witness pools.

Strategy here: (1) build a pool of safe 15-subsets of B_8 by randomised search,
(2) hill-climb 14-subsets to maximise the pool upper bound on d_max, (3) run the
exact branch-and-bound on the best candidates for a certified lower bound.

Integer arithmetic only.  Hard wall-clock budget; every partial result is still sound.
Writes research/verification/round3_b591_b592.json.
"""
from __future__ import annotations

import json
import random
import time
from pathlib import Path

from round3_b591_core import (quads_np, build_qm, max_overlap, coords, popcount,
                              apply_perm, d4_perm)

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round3_b591_b592.json"

DEADLINE = time.time() + 165.0          # seconds; script must finish inside 3 min
N = 8
K = 15                                  # K_8 = 15 (PROTOCOL.md, confirmed fact)
KS = K - 1                              # 14 = the one-stone-deficient layer

rng = random.Random(20260927)
report: dict = {"_meta": {"script": "round3_b591_b592.py", "n": N, "K_n": K,
                          "layer_size": KS}}


def left() -> float:
    return DEADLINE - time.time()


# ---------------------------------------------------------------- geometry ---
t0 = time.time()
v = N * N
quads = quads_np(N)
report["_meta"]["F_n"] = len(quads)
report["_meta"]["quads_sec"] = round(time.time() - t0, 2)
QM = build_qm(quads, v)
report["_meta"]["qm_sec"] = round(time.time() - t0, 2)
FULL = (1 << v) - 1


def safe(mask: int) -> bool:
    """O(k^3) safety test against the forbidden-quad table."""
    pts = [p for p in range(v) if (mask >> p) & 1]
    k = len(pts)
    for i in range(k):
        qp = QM[pts[i]]
        base = pts[i] * v
        for j in range(i + 1, k):
            m = qp.get(base + pts[j], 0)
            if not m:
                continue
            if (m & ~mask & ~((1 << pts[i]) | (1 << pts[j]))) != 0:
                return False
    return True


def fix(mask: int) -> int | None:
    """Greedily shrink an unsafe mask to a safe subset of the same-or-smaller size."""
    if safe(mask):
        return mask
    pts = [p for p in range(v) if (mask >> p) & 1]
    for p in pts:
        t = mask & ~(1 << p)
        if safe(t):
            return t
    return None


# ------------------------------------------------- pool of max sets (size 15) ---
# K_8 = 15 is a confirmed fact, so every safe 15-subset is a maximum set.
pool: list[int] = []


def rand_safe(k: int) -> int | None:
    for _ in range(4000):
        if left() < 20:
            return None
        order = rng.sample(range(v), k)
        m = 0
        for p in order:
            m |= 1 << p
        if safe(m):
            return m
    return None


perms = d4_perm(N)
t1 = time.time()
while len(pool) < 96 and left() > 25:
    m = rand_safe(K)
    if m is None:
        break
    for pm in perms:
        q = apply_perm(m, pm)
        if q not in pool:
            pool.append(q)
report["_meta"]["pool"] = {"size": len(pool), "sec": round(time.time() - t1, 2)}
# guard: the known n=8 witness from night-research/cycle6-maxsafeset-n8-15.json
known = [(0, 0), (1, 0), (2, 0), (1, 1), (7, 1), (3, 2), (7, 2), (5, 3),
         (0, 4), (2, 5), (4, 5), (5, 6), (0, 7), (4, 7), (5, 7)]
km = 0
for (x, y) in known:
    km |= 1 << (y * N + x)
report["_meta"]["known_witness_safe"] = bool(safe(km)) and popcount(km) == K
if km not in pool:
    pool.append(km)


def dmax_ub(S: int, pool_: list[int]) -> int:
    """Upper bound on d_max(S) from the witness pool: min_{M in pool} |S \\ M|."""
    return min(popcount(S & ~m) for m in pool_)


# -------------------------------------------------- candidate generation ------
cands: list[tuple[int, int]] = []          # (ub, mask)
seen: set[int] = set()


def consider(m: int | None) -> None:
    if m is None or popcount(m) != KS or m in seen or not safe(m):
        return
    seen.add(m)
    cands.append((dmax_ub(m, pool), m))


# (a) the n=7 worst-case 13-stone witness, grown by one stone inside B_8
n7_worst = [(0, 0), (1, 0), (1, 1), (5, 1), (6, 1), (0, 2), (2, 2), (3, 4),
            (6, 4), (4, 5), (1, 6), (2, 6), (3, 6)]
report["_meta"]["n7_worst_safety_in_B8_13"] = None
base = 0
for (x, y) in n7_worst:
    base |= 1 << (y * N + x)
grown = []
for p in range(v):
    if (base >> p) & 1:
        continue
    if safe(base | (1 << p)):
        grown.append(base | (1 << p))
for m in grown:
    consider(m)
report["_meta"]["n7_worst_growable_to14"] = len(grown)
report["_meta"]["n7_worst_ub"] = max([cands[0][0]], default=None) if cands else None

# (b) hill-climb: maximise the pool upper bound on d_max, |S| = 14
t2 = time.time()
while left() > 70:
    start = rand_safe(KS)
    if start is None:
        break
    cur, curb = start, dmax_ub(start, pool)
    improved = True
    while improved and left() > 70:
        improved = False
        inside = [p for p in range(v) if (cur >> p) & 1]
        outside = [p for p in range(v) if not ((cur >> p) & 1)]
        order = [(a, b) for a in inside for b in outside]
        rng.shuffle(order)
        for a, b in order:
            if left() < 70:
                break
            t = (cur & ~(1 << a)) | (1 << b)
            if not safe(t):
                continue
            ub = dmax_ub(t, pool)
            if ub > curb:
                cur, curb, improved = t, ub, True
        consider(cur)
cands.sort(key=lambda z: -z[0])
report["_meta"]["hillclimb"] = {
    "candidates": len(cands),
    "best_pool_ub": cands[0][0] if cands else None,
    "ub_hist": {str(k): sum(1 for u, _ in cands if u == k)
                for k in sorted({u for u, _ in cands})},
    "sec": round(time.time() - t2, 2),
}

# ------------------------------------------- certified d_max (branch & bound) ---
verified: list[dict] = []
seen_v: set[int] = set()
for ub, m in cands:
    if m in seen_v or len(verified) >= 8:
        continue
    seen_v.add(m)
    if left() < 12:
        break
    nb = 400_000
    t3 = time.time()
    best, nodes, complete, sec = max_overlap(N, m, K, QM, v, node_budget=nb)
    lb = KS - best                      # rigorous: d_max(S) >= |S| - best_overlap
    verified.append({
        "mask": int(m),
        "coords": coords(m, N),
        "pool_ub": ub,
        "max_overlap_found": best,
        "dmax_lower_bound": lb,
        "branch_and_bound_complete": complete,
        "nodes": nodes,
        "sec": sec,
        "dmax_over_n_lower_bound": lb / N,
    })
    print(f"ub={ub} best_overlap={best} lb={lb} complete={complete} "
          f"nodes={nodes} {sec}s", flush=True)

report["_meta"]["total_sec"] = round(time.time() - t0, 2)

# --------------------------------------------------------------- summary -----
best_lb = max((v_["dmax_lower_bound"] for v_ in verified), default=None)
report["B592"] = {
    "label": "PARTIAL",
    "verified_n": N,
    "layer_size": KS,
    "dmax_lower_bound_best": best_lb,
    "dmax_over_n_lower_bound": (best_lb / N) if best_lb is not None else None,
    "round2_dmax_max_n2_to_n7": {"2": 0, "3": 0, "4": 2, "5": 3, "6": 4, "7": 8},
    "witnesses": verified,
}
report["B591"] = {
    "label": "PARTIAL",
    "C_required_at_least": max([8, best_lb or 0]),
    "note": ("a witness at n=8 raises the necessary constant from 8; finiteness "
             "still cannot refute the existence of an absolute C"),
}

OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
print("wrote", OUT, report["_meta"]["total_sec"], "s", flush=True)
print("B592 best certified d_max lower bound:", best_lb, flush=True)
