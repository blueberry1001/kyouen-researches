"""round3_b591_b592_pool.py — B591/B592, pass 3: how big is the family mathcal(M_8)?

Why this matters.  n=7 has K_7 = 14 but only |M_7| = 16 maximum sets, and the
n=7 record d_max = 8 (over 13 stones) is exactly a statement about how few maximum
sets there are: a position is far from the maximum layer when the layer is small.
n=6 had 464 maximum sets and max d_max = 4.  So the "d_max/n = 0.5, 0.6, 0.67, 1.14"
trend behind B592 may be an artefact of the collapse |M_7| = 16 rather than a fact
about n.  The decisive missing datum is the size of the maximum-set family on B_8
(K_8 = 15) and the resulting maximum of d_max on the 14-stone layer.

Two rigorous quantities, both cheap:

  (U) pool upper bound.  For any family W subset of M_8 and any safe 14-set S,
      d_max(S) <= min_{M in W} |S \\ M| = 14 - max_{M in W} |S & M|.
      So maximising this over S gives a certified upper bound on the n=8 layer max.

  (L) exact d_max by branch-and-bound over ALL safe 15-subsets (the same routine
      that pass 1 ran to completion in 0.02-0.05 s per call).

The U bound is vectorised with numpy popcounts, so tens of thousands of candidates
can be screened; only the survivors pay for the L computation.

Integer arithmetic only.  Writes research/verification/round3_b591_b592_pool.json.
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
OUT = ROOT / "research" / "verification" / "round3_b591_b592_pool.json"
DEADLINE = time.time() + 165.0

N, K, KS = 8, 15, 14
rng = random.Random(5915928)
out: dict = {"_meta": {"script": "round3_b591_b592_pool.py", "n": N, "K_n": K,
                        "layer_size": KS}}
t0 = time.time()
v = N * N
quads = quads_np(N)
out["_meta"]["F_n"] = len(quads)
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


def _pc(a: np.ndarray) -> np.ndarray:
    return _POP[a.view(np.uint8).reshape(-1, 8)].sum(axis=1).astype(np.int16)


def ub_batch(cands: list[int], pool: np.ndarray) -> np.ndarray:
    """d_max upper bound for each candidate: 14 - max_M |S & M| over the pool."""
    if not len(cands):
        return np.zeros(0, dtype=np.int16)
    s = np.array(cands, dtype=np.uint64)
    best = np.zeros(len(cands), dtype=np.int16)
    step = max(1, 8_000_000 // max(1, len(cands)))
    for j0 in range(0, pool.shape[0], step):
        blk = pool[j0:j0 + step]
        np.maximum(best, _pc(s[:, None] & blk[None, :]).max(axis=1), out=best)
    return KS - best


# ---------------------------------------------------- M_8: build a big pool ----
pool_set: set[int] = set()
perms = d4_perm(N)
attempts = 0
while len(pool_set) < 30000 and left() > 110:
    attempts += 1
    m = 0
    for p in rng.sample(range(v), K):
        m |= 1 << p
    if not safe(m):
        continue
    pool_set.add(m)
    if attempts % 7 == 0:            # add D4 images to reach the orbit quickly
        for pm in perms:
            pool_set.add(apply_perm(m, pm))
pool = np.array(sorted(pool_set), dtype=np.uint64)
out["_meta"]["pool"] = {"distinct_max_sets_found": int(pool.shape[0]),
                        "attempts": attempts,
                        "sec": round(time.time() - t0, 2)}
out["_meta"]["|M_7|_reference"] = 16
out["_meta"]["|M_6|_reference"] = 464

known = [(0, 0), (1, 0), (2, 0), (1, 1), (7, 1), (3, 2), (7, 2), (5, 3),
         (0, 4), (2, 5), (4, 5), (5, 6), (0, 7), (4, 7), (5, 7)]
km = sum(1 << (y * N + x) for (x, y) in known)
out["_meta"]["known_witness_safe"] = bool(safe(km)) and popcount(km) == K
pool_set.add(km)
pool = np.array(sorted(pool_set), dtype=np.uint64)


def rand_safe(k: int) -> int | None:
    for _ in range(2000):
        if left() < 8:
            return None
        m = 0
        for p in rng.sample(range(v), k):
            m |= 1 << p
        if safe(m):
            return m
    return None


# ------------------------------ screen many 14-subsets with the pool upper bound --
t2 = time.time()
seen: set[int] = set()
cands: list[int] = []
hist: dict[int, int] = {}
for _ in range(4000):
    if left() < 95:
        break
    s = rand_safe(KS)
    if s is not None and s not in seen:
        seen.add(s)
        cands.append(s)
# grow the n=7 worst 13-stone witness into a 14-stone one, all 51 ways
n7_worst = [(0, 0), (1, 0), (1, 1), (5, 1), (6, 1), (0, 2), (2, 2), (3, 4),
            (6, 4), (4, 5), (1, 6), (2, 6), (3, 6)]
base = sum(1 << (y * N + x) for (x, y) in n7_worst)
seeds = []
for p in range(v):
    if not ((base >> p) & 1) and safe(base | (1 << p)):
        s = base | (1 << p)
        seeds.append(s)
        if s not in seen:
            seen.add(s)
            cands.append(s)
out["_meta"]["n7_worst_growable_to_14"] = len(seeds)

ubs = ub_batch(cands, pool)
for u in ubs:
    hist[int(u)] = hist.get(int(u), 0) + 1
out["ub_hist_over_screened"] = {str(k): hist[k] for k in sorted(hist)}
out["_meta"]["screened"] = len(cands)
out["_meta"]["screen_sec"] = round(time.time() - t2, 2)

# --------- hill-climb 14-subsets on the pool bound (cheap, vectorised scoring) ----
t3 = time.time()
best_m, best_u = None, -1
climbs = 0
while left() > 45:
    cur = rand_safe(KS)
    if cur is None:
        break
    climbs += 1
    curb = int(ub_batch([cur], pool)[0])
    hist[curb] = hist.get(curb, 0) + 1
    improved = True
    while improved and left() > 45:
        improved = False
        inside = [p for p in range(v) if (cur >> p) & 1]
        outside = [p for p in range(v) if not ((cur >> p) & 1)]
        batch, bmasks = [], []
        for a in inside:
            for b in outside:
                t = (cur & ~(1 << a)) | (1 << b)
                if t not in seen and safe(t):
                    seen.add(t)
                    batch.append(t)
                    bmasks.append((a, b))
        if not batch:
            break
        sc = ub_batch(batch, pool)
        j = int(np.argmax(sc))
        if int(sc[j]) > curb:
            cur = batch[j]
            curb = int(sc[j])
            improved = True
        else:
            break
    for u in sc.tolist():
        hist[u] = hist.get(u, 0) + 1
    if curb > best_u:
        best_u, best_m = curb, cur
out["ub_hist_final"] = {str(k): hist[k] for k in sorted(hist)}
out["_meta"]["climbs"] = climbs
out["_meta"]["climb_sec"] = round(time.time() - t3, 2)
out["_meta"]["total_distinct_candidates"] = len(seen)

# ------------------------------------------- exact d_max for the best candidates --
exact: list[dict] = []
finals = [best_m] if best_m is not None else []
finals += [m for m in seeds if left() > 12][:3]
finals += sorted(set(cands), key=lambda s: -int(ub_batch([s], pool)[0]))[:3]
for m in finals:
    if m is None or left() < 10:
        break
    t4 = time.time()
    b, nodes, complete, sec = max_overlap(N, m, K, QM, v, node_budget=2_000_000)
    d = KS - b
    exact.append({
        "coords": coords(m, N),
        "pool_ub": int(ub_batch([m], pool)[0]),
        "max_overlap": b,
        "dmax_exact": d if complete else None,
        "dmax_certified_lower_bound": d,
        "complete": complete,
        "nodes": nodes,
        "sec": sec,
    })
    print(f"ub={int(ub_batch([m], pool)[0])} overlap={b} dmax>={d} "
          f"complete={complete} nodes={nodes} {sec}s", flush=True)

out["_meta"]["total_sec"] = round(time.time() - t0, 2)
out["best_pool_ub_over_all_searched"] = best_u
out["best_pool_ub_witness"] = coords(best_m, N) if best_m is not None else None
out["exact_checks"] = exact
max_lb = max([e["dmax_certified_lower_bound"] for e in exact], default=0)
out["B592"] = {
    "label": "PARTIAL",
    "n": N,
    "certified_dmax_lower_bound_n8": max_lb,
    "certified_dmax_upper_bound_n8": best_u,
    "dmax_over_n_lower_bound": max_lb / N,
    "dmax_over_n_upper_bound": (best_u / N) if best_u >= 0 else None,
    "note": ("the n=8 layer maximum of d_max is bracketed, not determined; the pool "
             "upper bound is the first upper bound for this layer"),
}
out["B591"] = {
    "label": "PARTIAL",
    "C_required_at_least": max(8, max_lb),
    "note": "C >= 8 forced by n=7; n=8 adds nothing above it, so no new lower bound",
}
OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
print("wrote", OUT, out["_meta"]["total_sec"], "s", flush=True)
print("pool size:", out["_meta"]["pool"]["distinct_max_sets_found"], flush=True)
print("ub hist screened:", out["ub_hist_over_screened"], flush=True)
print("ub hist final   :", out["ub_hist_final"], flush=True)
print("best pool ub:", best_u, " exact lb:", max_lb, flush=True)
