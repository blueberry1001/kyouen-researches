#!/usr/bin/env python3
"""Harvest many n=8 K=15 safe sets via multi-solution target DFS (SAMPLE)."""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cycle8_lib import RES, det4, stones  # noqa: E402

N = 8
K = 15


def build_triples(n: int):
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


def occupancy(mask, n):
    mem = {}
    for y in range(n):
        for x in range(n):
            mem.setdefault(cell_key(n, x, y), []).append(y * n + x)
    return {f"{k[0]},{k[1]}": sum(1 for p in pts if (mask >> p) & 1) for k, pts in sorted(mem.items())}


def tau_min(mask, triples, n, cap=3):
    best = 99
    for p in range(n * n):
        if (mask >> p) & 1:
            continue
        fam = [o for o in triples[p] if (mask & o) == o]
        if not fam:
            return 0
        act = 0
        for o in fam:
            act |= o
        pts = [i for i in range(n * n) if (act >> i) & 1]
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
        best = min(best, found)
    return best


def harvest(triples, n, target, max_sets=80, node_budget=8_000_000):
    v = n * n
    all_cells = (1 << v) - 1
    found = []
    nodes = 0

    def dfs(cand, count, mask, cc):
        nonlocal nodes
        if len(found) >= max_sets or nodes > node_budget:
            return
        nodes += 1
        need = target - count
        if need == 0:
            found.append(mask)
            return
        if cand.bit_count() < need:
            return
        u = (cand & -cand).bit_length() - 1
        newcand = cand & ~(1 << u)
        undo = []
        ok = True
        for o in triples[u]:
            pc = bin(o & mask).count("1")
            if pc == 2:
                wmask = o & ~mask & all_cells
                if wmask == 0:
                    ok = False
                    break
                w = (wmask & -wmask).bit_length() - 1
                if cc[w] == 0:
                    newcand &= ~(1 << w)
                cc[w] += 1
                undo.append(w)
        if ok:
            dfs(newcand, count + 1, mask | (1 << u), cc)
        for w in undo:
            cc[w] -= 1
        if len(found) >= max_sets:
            return
        dfs(cand & ~(1 << u), count, mask, cc)

    dfs(all_cells, 0, 0, [0] * v)
    return found, nodes


def main():
    t0 = time.time()
    triples, nq = build_triples(N)
    # known witnesses
    seeds = []
    wit = [0x3120140120888207]
    for p in [
        Path("night-research/cycle8_g3_n8_sets.bin"),
        Path("night-research/cycle8_g3_n8_sets2.bin"),
    ]:
        if p.exists():
            data = p.read_bytes()
            for i in range(0, len(data), 8):
                wit.append(int.from_bytes(data[i : i + 8], "little"))
    print(f"quads={nq} seed_witnesses={len(wit)}", flush=True)

    found, nodes = harvest(triples, N, K, max_sets=60, node_budget=6_000_000)
    print(f"DFS harvest found={len(found)} nodes={nodes} t={time.time()-t0:.1f}", flush=True)

    all_sets = set(wit) | set(found)
    # also D4 of all
    from cycle8_lib import apply_perm, d4_perms

    perms = d4_perms(N)
    expanded = set(all_sets)
    for s in list(all_sets):
        for p in perms:
            expanded.add(apply_perm(s, p))
    print(f"after D4 expand {len(expanded)}", flush=True)

    sample = [s for s in expanded if s.bit_count() == K]
    # keep those that are actually safe — check via triples: no completed quad
    def safe(m):
        for p in range(N * N):
            if (m >> p) & 1:
                continue
        # check all quads through triples
        for p in range(N * N):
            for o in triples[p]:
                if (m & o) == o and (m >> p) & 1:
                    return False
        return True

    sample = [s for s in sample if safe(s)]
    print(f"safe sample={len(sample)}", flush=True)

    rhos = [tau_min(s, triples, N) for s in sample]
    occs = [occupancy(s, N) for s in sample]
    o22 = "2,2"
    uses22 = sum(1 for o in occs if o.get(o22, 0) > 0)
    corner_hist = Counter(sum(1 for p in (0, 7, 56, 63) if (s >> p) & 1) for s in sample)

    # pair distances on up to 40
    pair_n = min(len(sample), 40)
    ds = [15 - (sample[i] & sample[j]).bit_count() for i, j in combinations(range(pair_n), 2)]

    # min_det among sample only
    def min_det_sample(S, family):
        pts = stones(S, 64)
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                pair = (1 << pts[i]) | (1 << pts[j])
                if sum(1 for t in family if (t & pair) == pair) == 1:
                    return 2
        return 3  # lower bound among sample

    md = [min_det_sample(s, sample) for s in sample] if len(sample) >= 3 else []

    # save
    out_bin = Path("night-research/cycle8_h_n8_sample.bin")
    out_bin.write_bytes(b"".join(s.to_bytes(8, "little") for s in sample))
    out = {
        "package": "H-n8-harvest",
        "evidence": "SAMPLE (DFS multi-solution + known witnesses + D4; NOT complete n=8 census)",
        "n": 8,
        "K": 15,
        "n_quads": nq,
        "n_samples_safe": len(sample),
        "dfs_found": len(found),
        "dfs_nodes": nodes,
        "rho_hist_cap3": dict(Counter(rhos)),
        "rho_min": min(rhos) if rhos else None,
        "uses_22_orbit": uses22,
        "corner_hist": dict(corner_hist),
        "pair_d_hist": dict(Counter(ds)),
        "min_det_among_sample_hist": dict(Counter(md)) if md else None,
        "min_det_note": "lower bound 3 among sample only; global min_det needs full max-set family",
        "occupancy_examples": occs[:5],
        "seconds": round(time.time() - t0, 2),
        "n7_contrast": {
            "n7_rho_all_2": True,
            "n7_uses22": False,
            "n7_min_det": 2,
        },
    }
    Path(RES / "cycle8_h_n8_sample.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2)[:2500])
    print("Wrote", RES / "cycle8_h_n8_sample.json")


if __name__ == "__main__":
    main()
