#!/usr/bin/env python3
"""B181-B190: random greedy play, terminal sizes X_n.

- Exact terminal-size distribution via DP on n<=5 (uniform over L(S) each step).
- Monte Carlo for n=2..8 (and fixed-first-move variants for B187-B188).
- Reach-probability of maximal sets on n=4 (small) for B185-B186.
"""
from __future__ import annotations

import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, board_square  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "batch09_random_greedy.json"


def summarize_dist(dist: dict[int, float]) -> dict:
    mean = sum(t * p for t, p in dist.items())
    var = sum((t - mean) ** 2 * p for t, p in dist.items())
    items = sorted(dist.items())
    # median
    acc = 0.0
    med = None
    for t, p in items:
        acc += p
        if acc >= 0.5:
            med = t
            break
    return {
        "mean": mean,
        "var": var,
        "std": math.sqrt(var),
        "cv": (math.sqrt(var) / mean) if mean else None,
        "median": med,
        "min": items[0][0],
        "max": items[-1][0],
        "dist": {str(t): p for t, p in items},
    }


def monte_carlo(n: int, trials: int, seed: int, first_move: int | None = None) -> dict:
    b = board_square(n)
    rng = random.Random(seed)
    counts = defaultdict(int)
    for _ in range(trials):
        _, sz = b.random_greedy_terminal(rng, first_move=first_move)
        counts[sz] += 1
    dist = {t: c / trials for t, c in sorted(counts.items())}
    s = summarize_dist(dist)
    s["trials"] = trials
    s["seed"] = seed
    s["counts"] = {str(t): c for t, c in sorted(counts.items())}
    s["first_move"] = first_move
    return s


def mc_by_first_move(n: int, trials_each: int, seed: int) -> dict:
    b = board_square(n)
    out = {}
    for p in range(n * n):
        s = monte_carlo(n, trials_each, seed + p, first_move=p)
        x, y = p % n, p // n
        out[f"{p}"] = {"x": x, "y": y, "mean": s["mean"], "median": s["median"],
                       "min": s["min"], "max": s["max"], "trials": trials_each}
    means = [v["mean"] for v in out.values()]
    # classify corner / edge / center-ish
    def cls(x, y):
        if (x, y) in ((0, 0), (0, n - 1), (n - 1, 0), (n - 1, n - 1)):
            return "corner"
        if x in (0, n - 1) or y in (0, n - 1):
            return "edge"
        return "interior"
    by_cls = defaultdict(list)
    for k, v in out.items():
        by_cls[cls(v["x"], v["y"])].append(v["mean"])
    return {
        "per_point": out,
        "max_minus_min_mean": max(means) - min(means),
        "mean_by_class": {k: sum(v) / len(v) for k, v in by_cls.items()},
        "class_counts": {k: len(v) for k, v in by_cls.items()},
        "corner_mean": sum(by_cls.get("corner", [0])) / max(1, len(by_cls.get("corner", [1]))),
        "interior_mean": sum(by_cls.get("interior", [0])) / max(1, len(by_cls.get("interior", [1]))),
    }


def maximal_reach_n4(seed: int, trials: int) -> dict:
    """Estimate random-greedy reach probability of maximal sets on 4x4.

    Enumerate all maximal safe sets by DFS, then measure how often greedy lands
    on each (labeled), and compare with 1/|production paths| proxy = harmonic
    sum of |L| along construction orders.
    """
    b = board_square(4)
    maximals: list[int] = []

    def dfs(occ: int, cand: int):
        # expand greedily in id order; record maximal
        # first check maximal
        mv = b.legal_moves(occ)
        if not mv:
            maximals.append(occ)
            return
        # branch on lowest legal? too many. Instead: branch on all legal adds in order
        # but that enumerates all safe sets (5811) which is fine for n=4.
        for u in mv:
            dfs(occ | (1 << u), cand)

    # simpler: enumerate all reachable safe sets then filter maximal
    outcomes_reach = []
    stack = [0]
    seen = {0}
    while stack:
        occ = stack.pop()
        mv = b.legal_moves(occ)
        if not mv:
            maximals.append(occ)
        for u in mv:
            c = occ | (1 << u)
            if c not in seen:
                seen.add(c)
                stack.append(c)

    max_set = set(maximals)
    # labeled maximal count
    # Monte Carlo: record which maximal is hit
    rng = random.Random(seed)
    hit = defaultdict(int)
    for _ in range(trials):
        occ, sz = b.random_greedy_terminal(rng)
        hit[occ] += 1

    # symmetry classes via D4
    def d4_images(mask: int) -> set[int]:
        pts = b.points
        V = b.V
        # map index by transform
        imgs = set()
        for flipx in (False, True):
            for flipy in (False, True):
                for swap in (False, True):
                    new_pts = []
                    for (x, y) in pts:
                        if flipx:
                            x = 3 - x
                        if flipy:
                            y = 3 - y
                        if swap:
                            x, y = y, x
                        new_pts.append((x, y))
                    # rebuild mask: stone at old index i maps to new index of same coords
                    coord_to_new = {pts[j]: j for j in range(V)}
                    nm = 0
                    for i in range(V):
                        if mask & (1 << i):
                            nm |= 1 << coord_to_new[new_pts[i]]
                    imgs.add(nm)
        return imgs

    # group maximals by orbit
    unassigned = set(max_set)
    orbits = []
    while unassigned:
        m0 = next(iter(unassigned))
        orb = d4_images(m0) & max_set
        # also any maximal in orbit of images
        full_orb = set()
        for m in list(orb) or [m0]:
            full_orb |= d4_images(m)
        members = full_orb & max_set
        if not members:
            members = {m0}
        orbits.append(sorted(members))
        unassigned -= members

    # probability of hitting a maximal set, labeled
    probs = {m: hit.get(m, 0) / trials for m in max_set}
    # production-path weight proxy: product of 1/|L| over a canonical construction
    # Instead measure: number of legal construction sequences ending at m.
    # DP: ways(empty->m) = sum over predecessors. Count construction orders.
    ways: dict[int, int] = defaultdict(int)
    ways[0] = 1
    # process by increasing popcount
    by_size = defaultdict(list)
    for occ in seen:
        by_size[occ.bit_count()].append(occ)
    for k in range(0, b.V + 1):
        for occ in by_size.get(k, []):
            for u in b.legal_moves(occ):
                ways[occ | (1 << u)] += ways[occ]

    # for each maximal, sum of products of 1/|L| along all orders = reach prob (exact)
    # exact reach prob via DP on subsets already known from exact_terminal_dist;
    # here: reach prob of each maximal = ways-weighted product of 1/|L(S_i)|
    reach_memo: dict[int, dict[int, float]] = {}

    def reach_from(occ: int) -> dict[int, float]:
        hit = reach_memo.get(occ)
        if hit is not None:
            return hit
        mv = b.legal_moves(occ)
        if not mv:
            d = {occ: 1.0}
            reach_memo[occ] = d
            return d
        acc: dict[int, float] = defaultdict(float)
        w = 1.0 / len(mv)
        for u in mv:
            for t, p in reach_from(occ | (1 << u)).items():
                acc[t] += p * w
        d = dict(acc)
        reach_memo[occ] = d
        return d

    reach_exact = reach_from(0)

    # compare empirical vs exact; symmetry: mean exact reach per orbit vs size
    orbit_rows = []
    for members in orbits:
        ex = sum(reach_exact[m] for m in members)
        em = sum(hit.get(m, 0) / trials for m in members)
        stab = 8 * len(members) / max(1, len(d4_images(members[0])))  # rough
        orbit_rows.append({
            "orbit_size": len(members),
            "exact_reach": ex,
            "emp_reach": em,
            "exact_per_set": ex / len(members),
            "max_stab_order_est": max(len(d4_images(m)) for m in members),
            "example": members[0],
        })
    orbit_rows.sort(key=lambda r: -r["exact_per_set"])

    # B185: spread of reach among same-size maximals
    by_sz = defaultdict(list)
    for m, p in reach_exact.items():
        by_sz[m.bit_count()].append(p)
    spread = {}
    for sz, ps in sorted(by_sz.items()):
        ps = sorted(ps)
        spread[str(sz)] = {
            "count": len(ps),
            "min": ps[0],
            "max": ps[-1],
            "ratio_max_min": (ps[-1] / ps[0]) if ps[0] > 0 else None,
            "mean": sum(ps) / len(ps),
        }

    # B186: correlation of stabilizer size with per-set reach, same size
    stab_vs_reach = []
    for m, p in reach_exact.items():
        stab = len(d4_images(m))
        stab_vs_reach.append((stab, p, m.bit_count()))
    # within each size, does larger stab => larger reach?
    agree = 0
    total_pairs = 0
    for sz in by_sz:
        items = [(s, p) for s, p, k in stab_vs_reach if k == sz]
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                total_pairs += 1
                si, pi = items[i]
                sj, pj = items[j]
                if si == sj:
                    continue
                if (si > sj) == (pi > pj):
                    agree += 1
    return {
        "n": 4,
        "n_maximal": len(max_set),
        "n_orbits": len(orbits),
        "trials": trials,
        "size_spread": spread,
        "stab_reach_pair_agree_rate": (agree / total_pairs) if total_pairs else None,
        "total_pairs": total_pairs,
        "orbits_top": orbit_rows[:8],
        "orbits_bottom": orbit_rows[-4:],
        "K4_maximal_sizes": sorted(by_sz.keys()),
    }


def main():
    results = {"exact": {}, "mc": {}, "mc_first_move": {}, "n4_maximal_reach": {}}

    # Exact terminal distributions n=2..5
    for n in range(2, 6):
        b = board_square(n)
        dist = b.exact_terminal_dist()
        s = summarize_dist(dist)
        s["n"] = n
        s["K_n_estimate"] = max(dist.keys())
        s["F_n"] = len(b.quads)
        results["exact"][str(n)] = s
        print(f"exact n={n} mean={s['mean']:.4f} var={s['var']:.4f} med={s['median']} "
              f"range=({s['min']},{s['max']}) states={len(b.quads)}F", flush=True)

    # Monte Carlo n=2..8
    for n, trials in ((2, 2000), (3, 2000), (4, 2000), (5, 2000), (6, 1500), (7, 800), (8, 400)):
        s = monte_carlo(n, trials, seed=20260927 + n)
        s["n"] = n
        results["mc"][str(n)] = s
        print(f"mc n={n} mean={s['mean']:.4f} std={s['std']:.4f} med={s['median']} "
              f"range=({s['min']},{s['max']}) trials={trials}", flush=True)

    # Fixed first move n=5,6 (B187-B188)
    for n, trials in ((5, 300), (6, 200)):
        results["mc_first_move"][str(n)] = mc_by_first_move(n, trials, seed=20260928 + n)
        print(f"first-move sweep n={n} done", flush=True)

    # n=4 maximal reach (B185-B186)
    results["n4_maximal_reach"] = maximal_reach_n4(seed=77, trials=20000)
    print("n4 maximal reach done", flush=True)

    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
