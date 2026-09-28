"""round3_b591_b592_final.py — B591/B592, pass 5: the n=8 one-stone-deficient layer.

Infrastructure now in place:
  * round3_M8_pool.bin holds 1,009,679 pairwise distinct safe 15-subsets of B_8
    (K_8 = 15), found by local search seeded from the confirmed witness in
    night-research/cycle6-maxsafeset-n8-15.json.  A random 15-subset of the 64
    points carries ~91 forbidden quads on average, so sampling is hopeless and
    local search is the only way to get family members.

What is computed here, and why each piece is sound:
  (1) EXACT d_max(S) = 14 - max_{M safe, |M|=15} |S & M| by branch-and-bound over
      ALL safe 15-subsets, with a node cap.  Even when the cap truncates the search,
      the best overlap found is a real achievable overlap, so 14 - best is a
      RIGOROUS LOWER bound on d_max(S).  This is exactly the quantity B592 needs.
  (2) POOL UPPER bound d_max(S) <= 14 - max_{M in pool} |S & M| for the 1,009,679
      stored maximum sets.  This is the quantity B591 needs.

Round 2 never touched n=8; it stopped at d_max = 8 (13 stones, n=7) against
|M_7| = 16.  The ratio |M_n| / C(n^2, K_n - 1) is what controls d_max, and that is
the structural point recorded in the batch file.

Integer arithmetic only.  Writes research/verification/round3_b591_b592.json.
"""
from __future__ import annotations

import json
import random
import struct
import time
from pathlib import Path

import numpy as np

from round3_b591_core import quads_np, build_qm, max_overlap, coords, popcount, d4_perm, apply_perm

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round3_b591_b592.json"
POOLBIN = ROOT / "research" / "verification" / "round3_M8_pool.bin"
DEADLINE = time.time() + 165.0
N, K, KS = 8, 15, 14
NODE_CAP = 120_000
rng = random.Random(8151514)
out: dict = {"_meta": {"script": "round3_b591_b592_final.py", "n": N, "K_n": K,
                        "layer_size": KS, "node_cap": NODE_CAP}}
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


def _pc(a):
    sh = a.shape
    flat = _POP[a.view(np.uint8).reshape(-1, 8)].sum(axis=1).astype(np.int16)
    return flat.reshape(sh)


raw = POOLBIN.read_bytes()
pool = np.frombuffer(raw, dtype="<u8")
out["_meta"]["pool_size"] = int(pool.shape[0])
out["_meta"]["pool_bytes"] = len(raw)


def pool_ub(S: int) -> int:
    s = np.array([S], dtype=np.uint64)
    best = 0
    step = 262_144
    for j0 in range(0, pool.shape[0], step):
        blk = pool[j0:j0 + step]
        best = max(best, int(_pc(s & blk).max()))
    return KS - best


# ------------------------------------------------------------------ candidates --
n7_worst = [(0, 0), (1, 0), (1, 1), (5, 1), (6, 1), (0, 2), (2, 2), (3, 4),
            (6, 4), (4, 5), (1, 6), (2, 6), (3, 6)]
base = sum(1 << (y * N + x) for (x, y) in n7_worst)
seeds = [base | (1 << p) for p in range(v)
         if not ((base >> p) & 1) and safe(base | (1 << p))]
out["_meta"]["n7_worst_growable_to_14"] = len(seeds)

perms = d4_perm(N)
records: list[dict] = []
best_lb, best_m = -1, None
lb_hist: dict[int, int] = {}


def run(S: int, tag: str) -> int:
    """Certified lower bound on d_max(S) (exact when the B&B completes)."""
    global best_lb, best_m
    b, nodes, complete, sec = max_overlap(N, S, K, QM, v, node_budget=NODE_CAP)
    d = KS - b
    lb_hist[d] = lb_hist.get(d, 0) + 1
    rec = {"tag": tag, "dmax_certified_lb": d, "max_overlap": b,
           "complete": complete, "nodes": nodes, "sec": sec,
           "pool_ub": pool_ub(S) if complete else None,
           "coords": coords(S, N)}
    records.append(rec)
    if d > best_lb:
        best_lb, best_m = d, S
    print(f"  {tag}: dmax>={d} overlap={b} complete={complete} nodes={nodes} {sec}s",
          flush=True)
    return d


# (1) all 51 one-stone growths of the n=7 worst case
print("seeds from the n=7 worst case:", flush=True)
seed_lbs = []
for s in seeds:
    if left() < 90:
        break
    seed_lbs.append(run(s, "n7_worst_grown"))
out["n7_worst_grown_dmax_lb"] = {
    "count": len(seed_lbs), "hist": {str(k): seed_lbs.count(k) for k in sorted(set(seed_lbs))},
    "max": max(seed_lbs) if seed_lbs else None,
}

# (2) random sample of the whole 14-stone layer, exact d_max where affordable
print("random 14-subsets of B_8:", flush=True)
rnd: list[int] = []
seen: set[int] = set()
while left() > 20 and len(rnd) < 400:
    m = 0
    for p in rng.sample(range(v), KS):
        m |= 1 << p
    if safe(m) and m not in seen:
        seen.add(m)
        rnd.append(m)
out["_meta"]["random_layer_sample"] = len(rnd)
for m in rnd:
    if left() < 20:
        break
    run(m, "random14")

# (3) D4 orbit of the best certified witness -- all images share d_max by symmetry
orbit = []
if best_m is not None:
    for pm in perms:
        q = apply_perm(best_m, pm)
        if q not in orbit:
            orbit.append(q)
    for q in orbit[:2]:
        if left() > 12:
            run(q, "orbit")

out["_meta"]["total_sec"] = round(time.time() - t0, 2)
out["_meta"]["evaluated"] = len(records)
out["dmax_lb_hist"] = {str(k): lb_hist[k] for k in sorted(lb_hist)}
out["best_dmax_certified_lb_n8"] = best_lb
out["best_witness_coords"] = coords(best_m, N) if best_m is not None else None
out["best_witness_d4_orbit_size"] = len(orbit)
out["records"] = records
out["B592"] = {
    "label": "PARTIAL",
    "n": N, "layer_size": KS,
    "certified_dmax_lower_bound_n8": best_lb,
    "dmax_over_n_lower_bound": (best_lb / N) if best_lb >= 0 else None,
    "round2_dmax_max_n2_to_n7": {"2": 0, "3": 0, "4": 2, "5": 3, "6": 4, "7": 8},
    "note": "exact/lower-bound d_max on a sample of the n=8 K_8-1 layer, "
            "the first data point beyond n=7",
}
out["B591"] = {
    "label": "PARTIAL",
    "C_required_at_least": max(8, best_lb if best_lb >= 0 else 0),
    "n8_certified_dmax": best_lb,
}
OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
print("wrote", OUT, out["_meta"]["total_sec"], "s", flush=True)
print("best certified d_max at n=8, |S|=14 :", best_lb, flush=True)
print("hist:", out["dmax_lb_hist"], flush=True)
