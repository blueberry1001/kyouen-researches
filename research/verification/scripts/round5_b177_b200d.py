#!/usr/bin/env python3
"""B185 reach-prob MC (n=4,5), B197 children variance sample, B177 3-point removals."""
from __future__ import annotations

import json
import random
import sys
from collections import Counter, defaultdict

sys.path.insert(0, "research/verification/scripts")
from kyouen_core import board_square, board_square_minus  # noqa: E402

OUT = "research/verification/round5_b177_b200d.json"


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
    out = {}

    # ---------- B185: MC reach of maximal terminals ----------
    print("=== B185 MC ===", flush=True)
    for n, N in ((4, 30000), (5, 8000)):
        b = board_square(n)
        rng = random.Random(7)
        reach = Counter()
        for _ in range(N):
            occ = 0
            while True:
                mv = b.legal_moves(occ)
                if not mv:
                    reach[occ] += 1
                    break
                occ |= 1 << mv[rng.randrange(len(mv))]
        total = sum(reach.values())
        by_size_mass = Counter()
        by_size_nhit = Counter()
        by_size_probs = defaultdict(list)
        for occ, cnt in reach.items():
            s = occ.bit_count()
            by_size_mass[s] += cnt
            by_size_nhit[s] += 1
            by_size_probs[s].append(cnt / total)
        # true maximal counts by size via max_safe + known spectrum
        rec = {
            "N": total,
            "n_terminals_hit": len(reach),
            "mass_by_size": {str(s): v / total for s, v in sorted(by_size_mass.items())},
            "hit_count_by_size": dict(by_size_nhit),
            "reach_stats_by_size": {
                str(s): {
                    "mean": sum(ps) / len(ps),
                    "min": min(ps),
                    "max": max(ps),
                    "max_over_min": (max(ps) / min(ps)) if min(ps) > 0 else None,
                }
                for s, ps in sorted(by_size_probs.items())
            },
        }
        out[f"b185_n{n}_mc"] = rec
        print(f"n={n}", rec["mass_by_size"], rec["reach_stats_by_size"], flush=True)

    # exact small: n=4 size-5 vs size-7 reach via DP on a few terminals? skip.

    # ---------- B197: children residual-need2 variance, P vs N ----------
    print("=== B197 ===", flush=True)
    with open("research/verification/round5_b231_n5_grundy.json") as f:
        gmap = json.load(f)
    b = board_square(5)
    quads = b.quads
    from statistics import pvariance

    groups = defaultdict(lambda: {"P": [], "N": []})
    step = 11  # ~13.7k states
    i = 0
    for kstr, g in gmap.items():
        i += 1
        if i % step != 0:
            continue
        occ = int(kstr)
        k = occ.bit_count()
        lm = b.legal_moves(occ)
        if len(lm) < 2:
            continue
        child_n2 = []
        for p in lm:
            nxt = occ | (1 << p)
            n2 = 0
            for q in quads:
                if 4 - (q & nxt).bit_count() == 2:
                    n2 += 1
            child_n2.append(n2)
        var = pvariance(child_n2)
        groups[(k, len(lm))]["P" if g == 0 else "N"].append(var)

    both = []
    for key, d in groups.items():
        if d["P"] and d["N"]:
            mp = sum(d["P"]) / len(d["P"])
            mn = sum(d["N"]) / len(d["N"])
            both.append(
                {
                    "k": key[0],
                    "L": key[1],
                    "n_P": len(d["P"]),
                    "n_N": len(d["N"]),
                    "var_P": mp,
                    "var_N": mn,
                    "P_minus_N": mp - mn,
                }
            )
    out["b197"] = {
        "matched_keys": len(both),
        "keys_P_greater": sum(1 for x in both if x["P_minus_N"] > 0),
        "keys_N_greater": sum(1 for x in both if x["P_minus_N"] < 0),
        "mean_P_minus_N": (sum(x["P_minus_N"] for x in both) / len(both) if both else None),
        "examples_top": sorted(both, key=lambda x: -abs(x["P_minus_N"]))[:12],
    }
    print("B197", out["b197"], flush=True)

    # ---------- B177: n=4 minus 3 points (560) + random V=10..12 subsets ----------
    print("=== B177 3-point ===", flush=True)
    pts4 = [(x, y) for y in range(4) for x in range(4)]
    from itertools import combinations

    by_f = defaultdict(list)
    coll = []
    nboards = 0
    # 3-point removals: 560 boards, V=13 — f_vector_fast is OK
    for comb in combinations(pts4, 3):
        name = "4x4-del" + "".join(str(p) for p in comb)
        b = board_square_minus(4, list(comb))
        fv = f_vector_fast(b)
        g0 = b.solve_grundy()[0]
        rec = {"name": name, "f": list(fv), "g0": g0, "V": b.V}
        by_f[fv].append(rec)
        nboards += 1
        if nboards % 100 == 0:
            print("  3pt", nboards, flush=True)

    # random subsets of 4x4 with V=10,11,12
    rng = random.Random(99)
    for Vsize in (10, 11, 12):
        seen = set()
        for t in range(80):
            subset = tuple(sorted(rng.sample(range(16), Vsize)))
            if subset in seen:
                continue
            seen.add(subset)
            pts = [pts4[j] for j in subset]
            b = board_square_minus(4, [])  # dummy
            from kyouen_core import Board

            b = Board(pts, name=f"rand{Vsize}")
            fv = f_vector_fast(b)
            g0 = b.solve_grundy()[0]
            rec = {"name": f"rand{Vsize}_{t}", "f": list(fv), "g0": g0, "V": b.V}
            by_f[fv].append(rec)
            nboards += 1

    for fv, group in by_f.items():
        g0s = {r["g0"] for r in group}
        if len(g0s) > 1:
            coll.append(
                {
                    "g0s": sorted(g0s),
                    "members": [(r["name"], r["g0"]) for r in group[:8]],
                    "n_members": len(group),
                }
            )
    out["b177_extra"] = {
        "n_boards": nboards,
        "n_unique_f": len(by_f),
        "n_collision_groups": len(coll),
        "collisions": coll[:20],
        "multi_groups": sum(1 for g in by_f.values() if len(g) > 1),
    }
    print("B177 extra", out["b177_extra"]["n_boards"], "collisions", len(coll), flush=True)

    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()
