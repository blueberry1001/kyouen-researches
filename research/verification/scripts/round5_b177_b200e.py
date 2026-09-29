#!/usr/bin/env python3
"""Finish B177: 3-point removals on n=4 + random V=10..12 subsets. Write JSON."""
from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from itertools import combinations

sys.path.insert(0, "research/verification/scripts")
from kyouen_core import Board, board_square_minus  # noqa: E402

OUT = "research/verification/round5_b177_b200e.json"


def f_vector_fast(board):
    V = board.V
    f = [0] * (V + 1)

    def dfs(occ, start, size):
        f[size] += 1
        for v in range(start, V):
            nxt = occ | (1 << v)
            ok = True
            for q in board.quads_by_pt[v]:
                if (q & nxt) == q:
                    ok = False
                    break
            if ok:
                dfs(nxt, v + 1, size + 1)

    dfs(0, 0, 0)
    return tuple(f)


def main():
    pts4 = [(x, y) for y in range(4) for x in range(4)]
    by_f = defaultdict(list)
    nboards = 0
    # 3-point removals
    for comb in combinations(range(16), 3):
        name = f"4x4-del{comb}"
        b = board_square_minus(4, [pts4[j] for j in comb])
        fv = f_vector_fast(b)
        g0 = b.solve_grundy()[0]
        by_f[fv].append({"name": name, "g0": g0, "V": b.V})
        nboards += 1
        if nboards % 200 == 0:
            print("3pt", nboards, flush=True)

    # random subsets
    rng = random.Random(99)
    for Vsize in (10, 11, 12):
        seen = set()
        for t in range(40):
            subset = tuple(sorted(rng.sample(range(16), Vsize)))
            if subset in seen:
                continue
            seen.add(subset)
            b = Board([pts4[j] for j in subset], name=f"r{Vsize}_{t}")
            fv = f_vector_fast(b)
            g0 = b.solve_grundy()[0]
            by_f[fv].append({"name": f"r{Vsize}_{t}", "g0": g0, "V": b.V})
            nboards += 1

    coll = []
    for fv, group in by_f.items():
        g0s = {r["g0"] for r in group}
        if len(g0s) > 1:
            coll.append(
                {
                    "g0s": sorted(g0s),
                    "n_members": len(group),
                    "members": [(r["name"], r["g0"]) for r in group[:6]],
                }
            )
    out = {
        "n_boards": nboards,
        "n_unique_f": len(by_f),
        "n_multi_groups": sum(1 for g in by_f.values() if len(g) > 1),
        "n_collisions": len(coll),
        "collisions": coll[:20],
    }
    print("done", out, flush=True)
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()
