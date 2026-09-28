"""round3_b591_b592_exact.py — B591/B592, second pass: use the EXACT d_max objective.

Pass 1 (`round3_b591_b592.py`, output `round3_b591_b592.json`) showed that a pool of
96 witness maximum sets only certifies d_max ~ 3 on B_8, while random hill-climbing
against that pool is a weak surrogate: most B_8 14-subsets simply sit inside some
15-subset (a "4-in-a-row" style genericity argument gives d_max = 0 or 1 for typical
S).  So we optimise d_max itself.

For a fixed S, d_max(S) = |S| - max_{M safe, |M|=K} |S & M| is maximised by a
branch-and-bound over safe K-subsets.  Round 1 showed that call is cheap and always
terminates (748-2806 nodes).  So the full loop is affordable:

  repeat until the time budget runs out:
      S <- random safe 14-subset
      repeat: for every (a in S, b not in S), propose S' = S - a + b
             if safe(S') and dmax(S') > dmax(S): take it
      record S whenever dmax(S) is a new record

dmax is monotone, so the inner hill-climb never decreases the certified lower bound:
every value it reports is a rigorous d_max, and the running maximum is a
certified lower bound on max_{|S|=K_n-1} d_max(S) for n=8.

Integer arithmetic only.  Writes research/verification/round3_b591_b592_exact.json.
"""
from __future__ import annotations

import json
import random
import time
from pathlib import Path

from round3_b591_core import (quads_np, build_qm, max_overlap, coords, popcount,
                              d4_perm, apply_perm)

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round3_b591_b592_exact.json"

DEADLINE = time.time() + 170.0
N, K, KS = 8, 15, 14

rng = random.Random(591592)
out: dict = {"_meta": {"script": "round3_b591_b592_exact.py", "n": N, "K_n": K,
                        "layer_size": KS}}

t0 = time.time()
v = N * N
quads = quads_np(N)
out["_meta"]["F_n"] = len(quads)
QM = build_qm(quads, v)
out["_meta"]["geom_sec"] = round(time.time() - t0, 2)
FULL = (1 << v) - 1


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


_cache: dict[int, int] = {}


def dmax(S: int) -> int:
    """EXACT d_max(S): 14 - max |S & M| over all safe 15-subsets M."""
    hit = _cache.get(S)
    if hit is not None:
        return hit
    best, _n, _c, _s = max_overlap(N, S, K, QM, v, node_budget=10 ** 9)
    d = popcount(S) - best
    _cache[S] = d
    return d


def rand_safe(k: int) -> int | None:
    for _ in range(3000):
        if left() < 8:
            return None
        m = 0
        for p in rng.sample(range(v), k):
            m |= 1 << p
        if safe(m):
            return m
    return None


perms = d4_perm(N)
records: list[int] = []          # masks with their d_max, increasing d_max
best_d, best_m = -1, None
dmax_hist: dict[int, int] = {}
restarts = 0
moves = 0

while left() > 10:
    cur = rand_safe(KS)
    if cur is None:
        break
    restarts += 1
    curb = dmax(cur)
    dmax_hist[curb] = dmax_hist.get(curb, 0) + 1
    improved = True
    while improved and left() > 10:
        improved = False
        inside = [p for p in range(v) if (cur >> p) & 1]
        outside = [p for p in range(v) if not ((cur >> p) & 1)]
        moves_list = [(a, b) for a in inside for b in outside]
        rng.shuffle(moves_list)
        for a, b in moves_list:
            if left() < 10:
                break
            t = (cur & ~(1 << a)) | (1 << b)
            if not safe(t):
                continue
            d = dmax(t)
            dmax_hist[d] = dmax_hist.get(d, 0) + 1
            if d > curb:
                cur, curb, improved = t, d, True
                moves += 1
                if d > best_d:
                    best_d, best_m = d, t
    if best_m is not None and curb > best_d:
        best_d, best_m = curb, cur

# D4-orbit of the record: every image has the same d_max (board symmetry)
orbit = []
if best_m is not None:
    for pm in perms:
        q = apply_perm(best_m, pm)
        if q not in orbit:
            orbit.append(q)

out["_meta"].update({
    "restarts": restarts,
    "accepting_moves": moves,
    "distinct_dmax_evaluations": len(_cache),
    "sec": round(time.time() - t0, 2),
})
out["dmax_hist_over_visited"] = {str(k): dmax_hist[k] for k in sorted(dmax_hist)}

# ---- exact census of the 13 seeds grown from the n=7 worst case, for the record --
n7_worst = [(0, 0), (1, 0), (1, 1), (5, 1), (6, 1), (0, 2), (2, 2), (3, 4),
            (6, 4), (4, 5), (1, 6), (2, 6), (3, 6)]
base = 0
for (x, y) in n7_worst:
    base |= 1 << (y * N + x)
seeds = []
for p in range(v):
    if not ((base >> p) & 1) and safe(base | (1 << p)):
        s = base | (1 << p)
        seeds.append({"mask": int(s), "dmax": dmax(s),
                      "coords": coords(s, N)})
out["n7_worst_grown_to_14"] = seeds

out["B592"] = {
    "label": "PARTIAL",
    "n": N,
    "layer_size": KS,
    "dmax_certified_max_over_visited": best_d,
    "dmax_over_n": (best_d / N) if best_d >= 0 else None,
    "certified_lower_bound_on_max_dmax": best_d,
    "witness_coords": coords(best_m, N) if best_m is not None else None,
    "witness_d4_orbit_size": len(orbit),
    "witness_d4_distinct": [coords(m, N) for m in orbit],
    "method": "exact branch-and-bound d_max, hill-climbed; every value is certified",
}
out["B591"] = {
    "label": "PARTIAL",
    "C_required_at_least": max(8, best_d if best_d >= 0 else 0),
    "n8_dmax_max_lower_bound": best_d,
    "note": ("an n=8 witness forces C >= the n=8 value; finiteness can never refute "
             "an absolute C, and completeness of the n=8 layer is not attained"),
}

OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
print("wrote", OUT, out["_meta"]["sec"], "s", flush=True)
print("restarts", restarts, "distinct dmax evals", len(_cache), flush=True)
print("dmax hist:", out["dmax_hist_over_visited"], flush=True)
print("BEST certified dmax at n=8, |S|=14 :", best_d, flush=True)
print("dmax/n =", (best_d / N) if best_d >= 0 else None, flush=True)
print("witness:", coords(best_m, N) if best_m is not None else None, flush=True)
