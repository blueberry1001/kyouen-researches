#!/usr/bin/env python3
"""サイズ12極大集合の縮小と、小サイズ極大の標的探索。"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from fact_10x10_maximal_sample import Engine, build_forbidden, PTS  # noqa: E402

OUT = ROOT / "research" / "exploration"


def main() -> None:
    quads = build_forbidden()
    eng = Engine(quads)
    base = [0, 1, 2, 10, 14, 15, 21, 25, 26, 39, 49, 69]
    print("base size", len(base), "maximal", eng.is_maximal(base), flush=True)

    # Greedy delete
    best = list(base)
    improved = True
    while improved:
        improved = False
        for p in list(best):
            cand = [x for x in best if x != p]
            if cand and eng.is_maximal(cand):
                best = cand
                improved = True
                print("deleted", p, "->", len(best), flush=True)
                break
    print("after delete-only shrink:", best, flush=True)

    # Try all subsets of size 7..11 of the base (C(12,k) small)
    hits = []
    for k in range(6, 12):
        for comb in itertools.combinations(base, k):
            s = list(comb)
            if eng.is_maximal(s):
                hits.append(s)
                print("subset maximal", k, s, flush=True)
                break
        if hits and len(hits[-1]) == k:
            best = hits[-1]

    # Targeted: take 3 points on a large circle and search extensions
    # Use the size-12 circle from spectrum if we can reconstruct one.
    # Brute: random 3-sets that are safe, extend greedily with random order
    import random

    rng = random.Random(1)
    found_small = []
    for trial in range(5000):
        # prefer points near center to block more
        pool = [33, 34, 43, 44, 23, 24, 42, 45, 22, 25, 32, 35, 41, 46, 21, 26]
        if trial < 2000:
            occ = rng.sample(pool, 3)
        else:
            occ = rng.sample(range(PTS), 3)
        s = set(occ)
        if not all(eng.safe_add(s, p) for p in occ[1:]):
            continue
        # verify triple is safe (always true for |S|<4)
        S = eng.extend_greedy(sorted(s), rng)
        if eng.is_maximal(S) and len(S) <= 11:
            found_small.append(S)
            print("found", len(S), S, flush=True)
            if len(S) <= 8:
                break

    payload = {
        "base12": base,
        "delete_shrink": best,
        "subset_hits": hits,
        "small_found": found_small[:10],
        "min_seen": min([len(base)] + [len(x) for x in hits + found_small]),
    }
    path = OUT / "fact_10x10_maximal_shrink12.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    main()
