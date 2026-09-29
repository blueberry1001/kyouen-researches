#!/usr/bin/env python3
"""Round5 B512: 4x4 delta_K — does any 3-point deletion lower max_safe_size?

Known: n=4 base K=7; all 1-point and 2-point deletions keep K=7 (batch-09).
Test all C(16,3)=560 triples. Also record winner flips for B514/B520 context.
"""
from __future__ import annotations

import json
import sys
import time
from itertools import combinations
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import board_square, board_square_minus  # noqa: E402

OUT = REPO_ROOT / "research" / "verification" / "round5_b401_del3.json"


def max_safe_and_winner(n: int, deleted: tuple[int, ...]) -> tuple[int, int]:
    bd = board_square_minus(n, deleted)
    V = bd.V
    # note: board_square_minus removes points; remaining points re-indexed
    # We need K on the reduced board and empty-board winner.
    # Brute force all subsets of remaining V points (V<=13 after 3 deletions).
    full = (1 << V) - 1
    # legality
    def is_safe(occ: int) -> bool:
        for q in bd.quads:
            if (occ & q) == q:
                return False
        return True

    # win/lose DP + max safe size
    # enumerate safe subsets by BFS
    levels = [[0]]
    seen = {0}
    for _ in range(V):
        nxt = set()
        for occ in levels[-1]:
            empty = full ^ occ
            v = 0
            e = empty
            while e:
                if e & 1:
                    child = occ | (1 << v)
                    if is_safe(child):
                        nxt.add(child)
                e >>= 1
                v += 1
        if not nxt:
            break
        levels.append(sorted(nxt))
        seen |= nxt
    maxk = len(levels) - 1
    # winner
    states = seen
    win = {}
    for k in range(maxk, -1, -1):
        for s in levels[k]:
            empty = full ^ s
            w = False
            e = empty
            v = 0
            while e:
                if e & 1:
                    child = s | (1 << v)
                    if child in states and not win.get(child, True):
                        w = True
                        break
                e >>= 1
                v += 1
            win[s] = w
    g = 1 if win.get(0, False) else 0
    return maxk, g


def main():
    t0 = time.time()
    n = 4
    base_K, base_g = max_safe_and_winner(n, ())
    print(f"base K={base_K} g={base_g}", flush=True)

    # known: singles and pairs keep K — recheck a few then all triples
    drops = []
    flips = []
    n_tested = 0
    for trip in combinations(range(16), 3):
        K, g = max_safe_and_winner(n, trip)
        n_tested += 1
        if K < base_K:
            drops.append({"deleted": list(trip), "K": K, "g": g})
        if g != base_g:
            flips.append({"deleted": list(trip), "K": K, "g": g})
        if n_tested % 50 == 0:
            print(f"  {n_tested}/560 drops={len(drops)} flips={len(flips)} "
                  f"{time.time()-t0:.1f}s", flush=True)

    out = {
        "n": n,
        "base_K": base_K,
        "base_g": base_g,
        "n_triples": n_tested,
        "K_drops": drops,
        "winner_flips": flips[:20],
        "n_K_drops": len(drops),
        "n_winner_flips": len(flips),
        "delta_K_n4": 3 if drops else ">=4",
        "timing_s": round(time.time() - t0, 2),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT)
    print(json.dumps(out, indent=1)[:2000])


if __name__ == "__main__":
    main()
