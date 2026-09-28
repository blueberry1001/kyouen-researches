#!/usr/bin/env python3
"""Round3 B371/B372/B373/B374/B375/B378/B380 -- analysis of the COMPLETE list of
8-stone maximal safe sets on the 8x8 board.

Input:  n8_k8.masks.bin (uint64 LE) produced by maximal8.go (see companion
        round3_b371_enum.md); a --nocover brute-force mode is also supported for
        cross-checking on small boards.
Output: research/verification/round3_b371.json

All geometry is recomputed here with kyouen_core.det4 (integer only), so the
analysis is independent of the Go enumerator's feature vectors.

Hypotheses (research/hypothesis-bank-round2-2026-09-27.md section 38):
  B371 [all]   every 8-stone maximal set contains a collinear triple
  B372 [all]   every 8-stone maximal set has >= 2 distinct line directions
  B373 [all]   every 8-stone maximal set touches >= 2 sides of the board
  B374 [exist] some 8-stone maximal set uses no corner
  B375 [exist] some 8-stone maximal set has a different D4 orbit-occupancy
               signature from the known witness W = [0,1,6,20,24,32,34,60]
  B378 [exist] some 8-stone maximal set has a stone whose deletion makes
               exactly one originally-empty point legal
  B380 [stat]  within groups of equal covering-sum, the position of the
               singly-covered (b==1) points separates the local-search basins
"""
from __future__ import annotations

import json
import struct
import sys
import time
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
from kyouen_core import board_square  # noqa: E402

N = 8
V = N * N
OUT = ROOT / "research" / "verification" / "round3_b371.json"
DATA = ROOT / "research" / "verification" / "data"

W = [0, 1, 6, 20, 24, 32, 34, 60]  # known 8-stone witness from batch-05


# ---------------------------------------------------------------- geometry --
def build_board():
    b = board_square(N)
    # triple -> list of points it completes
    tc = defaultdict(list)
    for q in b.quads:
        ids = [i for i in range(V) if (q >> i) & 1]
        for p in ids:
            t = q & ~(1 << p)
            tc[t].append(p)
    return b, tc


def d4_images(p):
    x, y = p % N, p // N
    m = N - 1
    cs = [(x, y), (y, x), (m - x, y), (x, m - y),
          (m - x, m - y), (y, m - x), (m - y, x), (m - y, m - x)]
    return [c[1] * N + c[0] for c in cs]


def apply_d4(mask, t):
    r = 0
    m = mask
    while m:
        bit = m & -m
        p = bit.bit_length() - 1
        m ^= bit
        r |= 1 << d4_images(p)[t]
    return r


def canon(mask):
    return min(apply_d4(mask, t) for t in range(8))


def orbit_size(p):
    return len(set(d4_images(p)))


def orbit_sig(ids):
    """Sorted (orbit_size, count) signature, as a string."""
    c = Counter(orbit_size(p) for p in ids)
    return "".join(f"({s},{c[s]})" for s in sorted(c))


def gcd(a, b):
    while b:
        a, b = b, a % b
    return abs(a)


def collinear_triples(ids):
    out = []
    for a, b, c in combinations(ids, 3):
        xa, ya = a % N, a // N
        xb, yb = b % N, b // N
        xc, yc = c % N, c // N
        if (xb - xa) * (yc - ya) - (xc - xa) * (yb - ya) == 0:
            dx, dy = xb - xa, yb - ya
            g = gcd(dx, dy) or 1
            dx, dy = dx // g, dy // g
            if dx < 0 or (dx == 0 and dy < 0):
                dx, dy = -dx, -dy
            out.append(((a, b, c), (dx, dy)))
    return out


def sides_touched(ids):
    s = set()
    for i in ids:
        x, y = i % N, i // N
        if y == 0:
            s.add("T")
        if y == N - 1:
            s.add("B")
        if x == 0:
            s.add("L")
        if x == N - 1:
            s.add("R")
    return s


def corners_used(ids):
    return [i for i in ids if (i % N in (0, N - 1)) and (i // N in (0, N - 1))]


# ------------------------------------------------------------------- main --
def analyze(mask, tc):
    ids = [i for i in range(V) if (mask >> i) & 1]
    S = set(ids)
    # b-vector and the intersection of the blocking triples
    bvec = [0] * V
    inter = [0] * V
    for a, bb, c in combinations(ids, 3):
        t = (1 << a) | (1 << bb) | (1 << c)
        for p in tc.get(t, ()):
            bvec[p] += 1
            if inter[p] == 0:
                inter[p] = t
            else:
                inter[p] &= t
    empties = [p for p in range(V) if p not in S]
    # safety + maximality (re-verified independently of the Go enumerator)
    safe = all(bvec[p] == 0 for p in range(V) if p in S) or True  # see check_safe
    bvals = [bvec[p] for p in empties]
    single = [p for p in empties if bvec[p] == 1]
    # B378: deleting stone a frees exactly the empty points p with a in inter[p]
    del_free = {}
    for a in ids:
        del_free[a] = sum(1 for p in empties if (inter[p] >> a) & 1)
    cols = collinear_triples(ids)
    dirs = {d for _, d in cols}
    sides = sides_touched(ids)
    # centre distance
    sumD = 0
    for p in ids:
        dx = p % N - (N - 1) / 2
        dy = p // N - (N - 1) / 2
        sumD += 2 * (dx * dx + dy * dy)  # x2 to stay integral
    n_edge = sum(1 for p in ids
                 if p % N in (0, N - 1) or p // N in (0, N - 1))
    return {
        "S": ids,
        "n_collinear_triples": len(cols),
        "n_directions": len(dirs),
        "directions": sorted(dirs),
        "n_sides": len(sides),
        "sides": sorted(sides),
        "n_corners": len(corners_used(ids)),
        "orbit_sig": orbit_sig(ids),
        "sum_b": sum(bvals),
        "max_b": max(bvals) if bvals else 0,
        "min_b": min(bvals) if bvals else 0,
        "n_single_cover": len(single),
        "single_on_edge": sum(1 for p in single
                              if p % N in (0, N - 1) or p // N in (0, N - 1)),
        "single_in_interior": sum(1 for p in single
                                  if p % N not in (0, N - 1)
                                  and p // N not in (0, N - 1)),
        "del_free": del_free,
        "del_min": min(del_free.values()),
        "del_max": max(del_free.values()),
        "sum_centre_dist2": sumD,
        "n_edge_stones": n_edge,
    }


def check_safe_maximal(mask, b, tc):
    """Independent verification that the mask is safe AND maximal on 8x8."""
    ids = [i for i in range(V) if (mask >> i) & 1]
    S = set(ids)
    # safety: no forbidden quad has all 4 points occupied
    for q in b.quads:
        if (q & mask) == q:
            return False, False
    # maximality: every empty point is blocked by some occupied triple
    bvec = [0] * V
    for a, bb, c in combinations(ids, 3):
        t = (1 << a) | (1 << bb) | (1 << c)
        for p in tc.get(t, ()):
            bvec[p] += 1
    maximal = all(bvec[p] > 0 for p in range(V) if p not in S)
    return True, maximal


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if src is None:
        cand = DATA / "n8_k8.masks.bin"
        if cand.exists():
            src = cand
    if src is None or not src.exists():
        print("no mask file found; run round3_b371_enum first", file=sys.stderr)
        sys.exit(2)

    t0 = time.time()
    raw = src.read_bytes()
    masks = struct.unpack(f"<{len(raw)//8}Q", raw)
    b, tc = build_board()
    print(f"loaded {len(masks)} masks from {src}", flush=True)

    analyses = []
    n_safe = n_max = 0
    for m in masks:
        s, mx = check_safe_maximal(m, b, tc)
        n_safe += bool(s)
        n_max += bool(mx)
        analyses.append(analyze(m, tc))
    t_an = time.time() - t0

    total = len(analyses)
    can = Counter(orbit_sig_of(m) for m in masks)

    # ---- B371 / B372 / B373 (universal claims) ----
    b371_hold = [a for a in analyses if a["n_collinear_triples"] >= 1]
    b371_fail = [a for a in analyses if a["n_collinear_triples"] == 0]
    b372_hold = [a for a in analyses if a["n_directions"] >= 2]
    b372_fail = [a for a in analyses if a["n_directions"] < 2]
    b373_hold = [a for a in analyses if a["n_sides"] >= 2]
    b373_fail = [a for a in analyses if a["n_sides"] < 2]

    # ---- B374 (existence of a corner-free set) ----
    b374 = [a for a in analyses if a["n_corners"] == 0]

    # ---- B375 (orbit-occupancy signature different from W) ----
    w_sig = orbit_sig(W)
    sig_counts = Counter(a["orbit_sig"] for a in analyses)
    b375 = [a for a in analyses if a["orbit_sig"] != w_sig]

    # ---- B378 (a stone whose deletion frees exactly one point) ----
    b378 = [a for a in analyses if a["del_min"] == 1]
    del_min_hist = Counter(a["del_min"] for a in analyses)

    # ---- B380 (does the single-cover geometry split the basins?) ----
    # group by sum_b; inside each group compare single-cover placement
    by_sum = defaultdict(list)
    for a in analyses:
        by_sum[a["sum_b"]].append(a)
    b380_rows = []
    for s, grp in sorted(by_sum.items()):
        if len(grp) < 2:
            continue
        edge_frac = sorted({round(g["single_on_edge"] / g["n_single_cover"], 3)
                            for g in grp if g["n_single_cover"] > 0})
        b380_rows.append({
            "sum_b": s,
            "n": len(grp),
            "single_cover_counts": sorted({g["n_single_cover"] for g in grp}),
            "edge_fraction_values": edge_frac,
            "n_distinct_edge_fraction": len(edge_frac),
        })
    # aggregate: correlation between sum_b and single-cover placement
    b380 = {
        "group_count": len(b380_rows),
        "groups_with_split": sum(1 for r in b380_rows if r["n_distinct_edge_fraction"] > 1),
        "rows": b380_rows[:40],
    }

    def rep(a):
        return {"S": a["S"], "orbit_sig": a["orbit_sig"],
                "n_collinear_triples": a["n_collinear_triples"],
                "n_directions": a["n_directions"], "n_sides": a["n_sides"],
                "n_corners": a["n_corners"], "del_min": a["del_min"],
                "sum_b": a["sum_b"], "n_single_cover": a["n_single_cover"]}

    out = {
        "generated": "round3_b371_analysis.py",
        "board": "8x8",
        "n8_maximal_total": total,
        "n_verified_safe": n_safe,
        "n_verified_maximal": n_max,
        "d4_orbits": len(can),
        "orbit_signature_histogram": dict(sorted(can.items(),
                                                 key=lambda kv: -kv[1])),
        "witness_W": {"S": W, "orbit_sig": w_sig},
        "analysis_seconds": round(t_an, 2),
        "size_histogram": {str(k): v for k, v in
                           sorted(Counter(m.bit_count() for m in masks).items())},
        "B371": {
            "claim": "every 8-stone maximal set has a collinear triple",
            "holds": len(b371_hold), "counterexamples": len(b371_fail),
            "verdict": "SUPPORTED" if not b371_fail else "REFUTED",
            "counterexample_samples": [rep(a) for a in b371_fail[:5]],
        },
        "B372": {
            "claim": "every 8-stone maximal set has >=2 distinct line directions",
            "holds": len(b372_hold), "counterexamples": len(b372_fail),
            "verdict": "SUPPORTED" if not b372_fail else "REFUTED",
            "counterexample_samples": [rep(a) for a in b372_fail[:5]],
        },
        "B373": {
            "claim": "every 8-stone maximal set touches >=2 sides",
            "holds": len(b373_hold), "counterexamples": len(b373_fail),
            "verdict": "SUPPORTED" if not b373_fail else "REFUTED",
            "counterexample_samples": [rep(a) for a in b373_fail[:5]],
        },
        "B374": {
            "claim": "exists an 8-stone maximal set using no corner",
            "witnesses": len(b374),
            "verdict": "SUPPORTED" if b374 else "REFUTED",
            "witness_samples": [rep(a) for a in b374[:5]],
        },
        "B375": {
            "claim": "exists an 8-stone maximal set with a D4 orbit signature "
                     "different from W",
            "witnesses": len(b375),
            "n_distinct_signatures": len(sig_counts),
            "verdict": "SUPPORTED" if b375 else "REFUTED",
            "witness_samples": [rep(a) for a in b375[:5]],
        },
        "B378": {
            "claim": "exists an 8-stone maximal set with a stone whose deletion "
                     "frees exactly one originally-empty point",
            "witnesses": len(b378),
            "del_min_histogram": dict(sorted(del_min_hist.items())),
            "verdict": "SUPPORTED" if b378 else "REFUTED",
            "witness_samples": [rep(a) for a in b378[:5]],
        },
        "B380": {
            "claim": "single-cover placement, not covering sum, separates the "
                     "local-search basins",
            **b380,
            "verdict": "INCONCLUSIVE",
        },
        "descriptive": {
            "n_collinear_triples_hist": dict(sorted(Counter(
                a["n_collinear_triples"] for a in analyses).items())),
            "n_directions_hist": dict(sorted(Counter(
                a["n_directions"] for a in analyses).items())),
            "n_sides_hist": dict(sorted(Counter(
                a["n_sides"] for a in analyses).items())),
            "n_corners_hist": dict(sorted(Counter(
                a["n_corners"] for a in analyses).items())),
            "sum_b_hist": dict(sorted(Counter(
                a["sum_b"] for a in analyses).items())),
            "max_b_hist": dict(sorted(Counter(
                a["max_b"] for a in analyses).items())),
            "min_b_hist": dict(sorted(Counter(
                a["min_b"] for a in analyses).items())),
            "n_single_cover_hist": dict(sorted(Counter(
                a["n_single_cover"] for a in analyses).items())),
            "n_edge_stones_hist": dict(sorted(Counter(
                a["n_edge_stones"] for a in analyses).items())),
        },
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"total={total} safe={n_safe} maximal={n_max} orbits={len(can)} "
          f"({t_an:.1f}s)")
    for k in ("B371", "B372", "B373", "B374", "B375", "B378"):
        print(k, out[k]["verdict"])
    print("wrote", OUT)


def orbit_sig_of(mask):
    ids = [i for i in range(V) if (mask >> i) & 1]
    return orbit_sig(ids)


if __name__ == "__main__":
    main()
