#!/usr/bin/env python3
"""Cycle 8E light: n=8 15-stone SAMPLE from the known witness D4 orbit only.

Full/random DFS target search for many K=15 sets was attempted and is too
expensive here; per user priority we cut E after A–D delivered structure.
Evidence: SAMPLE, n=8 sets from D4(witness), not a population claim.
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import NR, RES, apply_perm, d4_perms, det4, stones  # noqa: E402


def pts_to_mask(pts, n):
    m = 0
    for x, y in pts:
        m |= 1 << (y * n + x)
    return m


def safe_mask(mask, n):
    v = n * n
    rows = [[x * x + y * y, x, y, 1] for y in range(n) for x in range(n)]
    pts = stones(mask, v)
    for a, b, c, d in combinations(pts, 4):
        if det4([rows[a], rows[b], rows[c], rows[d]]) == 0:
            return False
    return True


def cell_key(n, x, y):
    return min(
        {
            (x, y),
            (n - 1 - x, y),
            (x, n - 1 - y),
            (n - 1 - x, n - 1 - y),
            (y, x),
            (n - 1 - y, x),
            (y, n - 1 - x),
            (n - 1 - y, n - 1 - x),
        }
    )


def orbit_members(n):
    mem = {}
    for y in range(n):
        for x in range(n):
            mem.setdefault(cell_key(n, x, y), []).append(y * n + x)
    return mem


def occupancy(mask, n):
    mem = orbit_members(n)
    return {f"{k[0]},{k[1]}": sum(1 for p in pts if (mask >> p) & 1) for k, pts in mem.items()}


def build_triples(n):
    v = n * n
    rows = [[x * x + y * y, x, y, 1] for y in range(n) for x in range(n)]
    triples = [[] for _ in range(v)]
    nq = 0
    for a in range(v - 3):
        for b in range(a + 1, v - 2):
            for c in range(b + 1, v - 1):
                for d in range(c + 1, v):
                    if det4([rows[a], rows[b], rows[c], rows[d]]) != 0:
                        continue
                    nq += 1
                    q = (1 << a) | (1 << b) | (1 << c) | (1 << d)
                    for t in (a, b, c, d):
                        triples[t].append(q & ~(1 << t))
    return triples, nq


def tau_min(mask, triples, n, cap=3):
    v = n * n
    best = 99
    for p in range(v):
        if (mask >> p) & 1:
            continue
        fam = [o for o in triples[p] if (mask & o) == o]
        if not fam:
            return 0
        act = 0
        for o in fam:
            act |= o
        pts = [i for i in range(v) if (act >> i) & 1]
        found = None
        for t in range(1, cap + 1):
            for comb in combinations(pts, t):
                cm = 0
                for x in comb:
                    cm |= 1 << x
                if all(cm & o for o in fam):
                    found = t
                    break
            if found is not None:
                break
        if found is None:
            found = cap + 1
        if found < best:
            best = found
            if best == 0:
                return 0
    return best


def main():
    n = 8
    t0 = time.time()
    triples, nq = build_triples(n)
    wit = json.loads((NR / "cycle6-maxsafeset-n8-15.json").read_text(encoding="utf-8"))
    seed = pts_to_mask(wit["witness"], n)
    assert seed.bit_count() == 15
    assert safe_mask(seed, n)
    perms = d4_perms(n)
    samples = sorted({apply_perm(seed, p) for p in perms})
    print(f"quads={nq} D4_samples={len(samples)}", flush=True)

    # 1-swap neighbors that stay size-15 safe
    swap_hits = 0
    swap_dest = set()
    empties = [p for p in range(64) if not (seed >> p) & 1]
    occ = stones(seed, 64)
    for v in empties:
        for r in occ:
            s2 = (seed & ~(1 << r)) | (1 << v)
            if safe_mask(s2, n):
                swap_hits += 1
                swap_dest.add(s2)
    print(f"1-swap safe destinations from seed: {swap_hits} ({len(swap_dest)} distinct)", flush=True)

    rho = [tau_min(s, triples, n, cap=3) for s in samples]
    occs = [occupancy(s, n) for s in samples]
    # all D4 images share occupancy up to permutation of cells — report seed occ
    corner_hist = Counter(
        sum(1 for p in (0, 7, 56, 63) if (s >> p) & 1) for s in samples
    )
    o22 = orbit_members(n)[cell_key(n, 2, 2)]
    uses22 = sum(1 for s in samples if any((s >> p) & 1 for p in o22))

    # pair distances within D4 orbit
    ds = [15 - (samples[i] & samples[j]).bit_count() for i, j in combinations(range(len(samples)), 2)]

    out = {
        "package": "E",
        "evidence": "SAMPLE — D4 orbit of one known n=8 15-stone witness; random multi-witness DFS cut as too expensive after A–D",
        "n": 8,
        "K": 15,
        "n_quads": nq,
        "n_samples": len(samples),
        "seed_witness": wit["witness"],
        "rho_hist_cap3": dict(Counter(rho)),
        "rho_min": min(rho),
        "occupancy_seed": occs[0],
        "corner_hist": dict(corner_hist),
        "uses_orbit_2_2": uses22,
        "pair_distance_hist": dict(Counter(ds)),
        "one_swap_safe_from_seed": swap_hits,
        "one_swap_distinct_sets": len(swap_dest),
        "seconds": round(time.time() - t0, 2),
        "comparison_to_n7": {
            "n7_rho_all_2": True,
            "n7_one_swap_zero": True,
            "n8_sample_note": "if rho_min>=2 and one_swap==0, sample is consistent with n=7 rigidity; if one_swap>0 or rho=1, n=8 differs",
        },
    }
    path = RES / "cycle8_e_n8_sample.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    (NR / "cycle8_e_n8_sample.bin").write_bytes(b"".join(s.to_bytes(8, "little") for s in samples))
    print(json.dumps(out, indent=2))
    print("Wrote", path)


if __name__ == "__main__":
    main()
