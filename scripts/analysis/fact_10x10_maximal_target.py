#!/usr/bin/env python3
"""サイズ 6–10 の極大安全配置を標的に探索する。"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from fact_10x10_maximal_sample import Engine, build_forbidden, PTS  # noqa: E402

OUT = ROOT / "research" / "exploration"


def main() -> None:
    quads = build_forbidden()
    eng = Engine(quads)
    rng = random.Random(7)

    best = 11
    best_set = [11, 20, 23, 32, 43, 50, 59, 63, 68, 81, 98]
    found = [best_set]

    # Search strategies:
    # 1) random small seeds + greedy extend with various orders
    # 2) start from known small maximal and try swap/replace
    # 3) pure random order greedy (already saw 12)

    for trial in range(8000):
        mode = trial % 4
        if mode == 0:
            occ = rng.sample(range(PTS), 2)
        elif mode == 1:
            occ = rng.sample(range(PTS), 3)
        elif mode == 2:
            occ = rng.sample(range(PTS), 4)
        else:
            occ = [rng.choice([0, 9, 90, 99, 33, 44])]
        s = set(occ)
        # ensure safe
        ok = True
        for i, p in enumerate(occ):
            if not eng.safe_add(s - {p}, p):
                ok = False
                break
        if not ok:
            continue
        S = eng.extend_greedy(sorted(s), rng if trial % 2 == 0 else None)
        if eng.is_maximal(S) and len(S) < best:
            best = len(S)
            best_set = S
            found.append(S)
            print("NEW BEST", best, S, flush=True)
            if best <= 7:
                break

    # Try to shrink the best set by 2-deletions
    improved = True
    while improved:
        improved = False
        for i in range(len(best_set)):
            for j in range(i + 1, len(best_set)):
                cand = [p for t, p in enumerate(best_set) if t not in (i, j)]
                if eng.is_maximal(cand):
                    best_set = cand
                    best = len(cand)
                    improved = True
                    print("2-delete ->", best, best_set, flush=True)
                    break
            if improved:
                break

    payload = {
        "best_size": best,
        "best_set": best_set,
        "all_found": found,
        "trials": 8000,
    }
    path = OUT / "fact_10x10_maximal_target.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", path, "best", best)


if __name__ == "__main__":
    main()
