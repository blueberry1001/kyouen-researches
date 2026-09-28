#!/usr/bin/env python3
"""Round3 chunk5 - B300 depth-2 move-tree isomorphism counterexample search.

A depth-d move tree from S is the rooted, point-labelled tree of legal moves down
to depth d (structure = branching legality only, labels are board points).  Two
positions S,T on the same board have isomorphic depth-d trees when there is a
bijection sigma of the board with sigma(S)=T that carries the tree of S onto the
tree of T.  For d=1 this is "|L(S)| equal and the multiset {|L(S+p)|} equal"; for
d=2 additionally the multiset over children of the sorted child-histograms
{(|L|, child-hist) for children} must match, up to the point relabelling.

We search for pairs (S,T) with equal d-depth tree invariants but opposite P/N.

Output: research/verification/round3_chunk5_b300.json
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from round3_chunk5_sharp import Game, bits, h_all  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round3_chunk5_b300.json"


def tree_invariant(game, Lc, occ, depth):
    """Canonical, label-free invariant of the legal-move tree down to `depth`.

    level(occ, 0) = ("leaf", |L(occ)|)
    level(occ, d) = ("node", sorted(multiset of level(child, d-1) for legal child))
    This is a *label-free* abstraction: it forgets which points are moved but
    keeps the shape of the branching legality structure.  Two positions with the
    same invariant have isomorphic depth-d trees up to point relabelling.
    """
    memo = {}

    def inv(o, d):
        key = (o, d)
        if key in memo:
            return memo[key]
        mv = Lc[o]
        if d == 0:
            val = ("L", len(mv))
        else:
            val = ("N", tuple(sorted(inv(o | (1 << u), d - 1) for u in mv)))
        memo[key] = val
        return val

    return inv(occ, depth)


def main():
    out = {}
    for n, kmax in ((4, 7), (5, 4)):
        t0 = time.time()
        game = Game(n)
        reach = game.reachable()
        g, Lc = game.grundy_all(reach)
        print(f"[n={n}] states={len(reach)} g0={g[0]} ({time.time()-t0:.1f}s)", flush=True)

        stats = []
        for occ in reach:
            k = occ.bit_count()
            if k < 2 or k > kmax:
                continue
            stats.append((occ, k, g[occ], len(Lc[occ])))
        print(f"[n={n}] candidates k=2..{kmax}: {len(stats)}", flush=True)

        res = {"n": n, "kmax": kmax, "n_candidates": len(stats)}
        for d in (1, 2):
            groups = defaultdict(list)
            for occ, k, gv, L in stats:
                groups[(k, tree_invariant(game, Lc, occ, d))].append((occ, k, gv, L))
            nsplit = 0
            ex = []
            for key, lst in groups.items():
                ps = [x for x in lst if x[2] == 0]
                ns = [x for x in lst if x[2] != 0]
                if ps and ns:
                    nsplit += 1
                    if len(ex) < 4:
                        ex.append({
                            "k": key[0],
                            "P": list(bits(ps[0][0])), "g_P": ps[0][2], "L_P": ps[0][3],
                            "N": list(bits(ns[0][0])), "g_N": ns[0][2], "L_N": ns[0][3],
                            "group_size": len(lst),
                        })
            res[f"depth{d}"] = {
                "n_groups": len(groups),
                "n_pn_split_groups": nsplit,
                "examples": ex,
                "verdict": "FOUND" if nsplit else "none_in_range",
            }
            print(f"[n={n}] depth={d}: groups={len(groups)} pn_split={nsplit}", flush=True)
        out[f"n{n}"] = res
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
