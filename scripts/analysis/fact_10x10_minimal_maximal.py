#!/usr/bin/env python3
"""10×10 の極小極大安全配置（どの1点も加えられない安全集合）の探索。

バックトラックで安全集合を伸ばし、サイズ最小の極大集合を完全列挙する。
n は 10 固定。打切り時は complete=false を残す。
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "exploration"
OUT.mkdir(parents=True, exist_ok=True)

N = 10
PTS = N * N


def xy(p: int):
    return (p % N, p // N)


def pid(x: int, y: int) -> int:
    return y * N + x


def d4_images(p: int):
    x, y = xy(p)
    n = N - 1
    return (
        pid(x, y),
        pid(n - x, y),
        pid(x, n - y),
        pid(n - x, n - y),
        pid(y, x),
        pid(n - y, x),
        pid(y, n - x),
        pid(n - y, n - x),
    )


def d4_canon_set(points):
    n = N - 1
    coords = [xy(p) for p in points]
    images = []
    for mode in range(8):
        img = []
        for x, y in coords:
            if mode == 0:
                nx, ny = x, y
            elif mode == 1:
                nx, ny = n - x, y
            elif mode == 2:
                nx, ny = x, n - y
            elif mode == 3:
                nx, ny = n - x, n - y
            elif mode == 4:
                nx, ny = y, x
            elif mode == 5:
                nx, ny = n - y, x
            elif mode == 6:
                nx, ny = y, n - x
            else:
                nx, ny = n - y, n - x
            img.append(pid(nx, ny))
        images.append(tuple(sorted(img)))
    return min(images)


class ForbiddenIndex:
    """For each pair, list of completion points p such that {a,b,c,p} becomes forbidden
    for some c already forced — better: precompute all forbidden quads containing pairs.
    """

    def __init__(self, quads):
        self.pair_to_quads = {}
        for q in quads:
            q = tuple(q)
            for i in range(4):
                for j in range(i + 1, 4):
                    a, b = q[i], q[j]
                    key = (a, b) if a < b else (b, a)
                    self.pair_to_quads.setdefault(key, []).append(q)

    def would_be_forbidden(self, occupied: set[int], new: int) -> bool:
        """True if placing `new` with some 2 of occupied forms a forbidden quad."""
        occ = list(occupied)
        m = len(occ)
        for i in range(m):
            a = occ[i]
            for j in range(i + 1, m):
                b = occ[j]
                key = (min(a, b, new), max(a, b, new))
                # check quads containing pair (min2)
                # simpler: any forbidden quad subset of occupied|{new}
                # use pair (a,b) and see if some quad with (a,b) has other two in set
                pass
        # Correct approach: for each forbidden quad containing new and 2 others, check those 2 in occupied
        # Precompute: new -> list of (c1,c2,c3) other members of quads
        return False  # filled by specialized solver below


def build_forbidden_quads(n=N):
    import itertools

    pts = n * n
    quads = []
    coords = [xy(p) for p in range(pts)]
    for i, j, k, l in itertools.combinations(range(pts), 4):
        xi, yi = coords[i]
        xj, yj = coords[j]
        xk, yk = coords[k]
        xl, yl = coords[l]
        a00 = xi * xi + yi * yi
        a10 = xj * xj + yj * yj
        a20 = xk * xk + yk * yk
        a30 = xl * xl + yl * yl

        def d3(r0, r1, r2):
            return (
                r0[0] * (r1[1] * r2[2] - r1[2] * r2[1])
                - r0[1] * (r1[0] * r2[2] - r1[2] * r2[0])
                + r0[2] * (r1[0] * r2[1] - r1[1] * r2[0])
            )

        A = (
            (a00, xi, yi, 1),
            (a10, xj, yj, 1),
            (a20, xk, yk, 1),
            (a30, xl, yl, 1),
        )
        det = (
            A[0][0] * d3(A[1][1:], A[2][1:], A[3][1:])
            - A[0][1] * d3((A[1][0], A[1][2], A[1][3]), (A[2][0], A[2][2], A[2][3]), (A[3][0], A[3][2], A[3][3]))
            + A[0][2] * d3((A[1][0], A[1][1], A[1][3]), (A[2][0], A[2][1], A[2][3]), (A[3][0], A[3][1], A[3][3]))
            - A[0][3] * d3((A[1][0], A[1][1], A[1][2]), (A[2][0], A[2][1], A[2][2]), (A[3][0], A[3][1], A[3][2]))
        )
        if det == 0:
            quads.append((i, j, k, l))
    return quads


def is_safe(occupied: list[int], forbidden: set[tuple[int, int, int, int]]) -> bool:
    if len(occupied) < 4:
        return True
    s = set(occupied)
    # only need to check 4-subsets containing the newest — caller should pass in order
    # Here full check for safety when len is small
    from itertools import combinations

    for quad in combinations(occupied, 4):
        key = tuple(sorted(quad))
        if key in forbidden:
            return False
    return True


def enumerate_minimal_maximal(forbidden_set, target_size, max_results=1000, time_limit_s=120):
    """Enumerate maximal safe sets of exactly `target_size` (or find min size).

    We search for maximal safe sets and track minimum size.
    A safe set S is maximal if for every p not in S, S∪{p} is unsafe.
    """
    quads_list = list(forbidden_set)
    # index quads by point
    by_point = [[] for _ in range(PTS)]
    for q in quads_list:
        for p in q:
            by_point[p].append(q)

    min_size = [10**9]
    minimal_sets = []
    complete = [True]
    t0 = time.time()
    nodes = [0]

    def safe_with(occ: list[int], new: int) -> bool:
        # check all quads that contain new and 3 from occ
        if len(occ) < 3:
            return True
        s = set(occ)
        for q in by_point[new]:
            others = [p for p in q if p != new]
            if all(p in s for p in others):
                return False
        return True

    def is_maximal(occ: list[int]) -> bool:
        s = set(occ)
        for p in range(PTS):
            if p in s:
                continue
            if safe_with(occ, p):
                return False
        return True

    def dfs(occ: list[int], start_from: int):
        nodes[0] += 1
        if time.time() - t0 > time_limit_s:
            complete[0] = False
            return
        if len(occ) > min_size[0]:
            # can still be maximal but not new minimum; still record if exactly min?
            # for full min spectrum we only care about global min
            pass
        # if cannot extend, maybe maximal
        extended = False
        for p in range(start_from, PTS):
            if p in occ:
                continue
            if safe_with(occ, p):
                extended = True
                occ.append(p)
                dfs(occ, p + 1)
                occ.pop()
                if not complete[0]:
                    return
                if len(minimal_sets) >= max_results and min_size[0] < 10**9:
                    # enough for min-size classification
                    return
        if not extended:
            # maximal
            sz = len(occ)
            if sz < min_size[0]:
                min_size[0] = sz
                minimal_sets.clear()
            if sz == min_size[0]:
                if len(minimal_sets) < max_results:
                    minimal_sets.append(tuple(occ))

    # Empty start
    dfs([], 0)

    return {
        "complete": complete[0],
        "nodes": nodes[0],
        "min_size": None if min_size[0] > 10**8 else min_size[0],
        "n_minimal_sets_recorded": len(minimal_sets),
        "sets": [list(s) for s in minimal_sets],
        "seconds": time.time() - t0,
    }


def main():
    # Prefer a faster C++ path if binary exists; else Python with smaller search.
    print("building forbidden quads (10x10)...", flush=True)
    t0 = time.time()
    quads = build_forbidden_quads()
    print(f"forbidden={len(quads)} in {time.time()-t0:.1f}s", flush=True)
    assert len(quads) == 54441

    # First, find a small maximal set greedily to get an upper bound on min size
    fset = set(tuple(sorted(q)) for q in quads)

    # Greedy: repeatedly add lowest-index safe point
    greedy = []
    for p in range(PTS):
        if safe := True:
            if len(greedy) >= 3:
                s = set(greedy)
                bad = False
                for q in fset:
                    if p in q and sum(1 for x in q if x in s or x == p) == 4:
                        # if all 4 in greedy+{p}
                        if all(x in s or x == p for x in q):
                            bad = True
                            break
                if bad:
                    continue
        greedy.append(p)
    # check maximality of greedy
    def can_add(greedy, p):
        s = set(greedy)
        for q in fset:
            if p in q and all(x in s or x == p for x in q):
                return False
        return True

    # extend greedy to maximal
    changed = True
    while changed:
        changed = False
        for p in range(PTS):
            if p in greedy:
                continue
            if can_add(greedy, p):
                greedy.append(p)
                changed = True
                break
    print(f"greedy maximal size={len(greedy)}", flush=True)

    # DFS for minimal maximal — start with target = find min
    # Use target-size pruning: search only up to min(greedy_size, 12) first
    result = enumerate_minimal_maximal(fset, target_size=len(greedy), max_results=200, time_limit_s=300)

    # refine: record D4 orbits of min sets
    orbits = {}
    for s in result["sets"]:
        key = d4_canon_set(s)
        orbits.setdefault(key, 0)
        orbits[key] += 1

    payload = {
        "board": "10x10",
        "forbidden": len(quads),
        "greedy_maximal_size": len(greedy),
        "greedy_example": greedy,
        "min_maximal_size": result["min_size"],
        "n_sets_recorded": result["n_minimal_sets_recorded"],
        "n_d4_orbits_among_recorded": len(orbits),
        "d4_orbit_multiplicity": {str(k): v for k, v in list(orbits.items())[:20]},
        "complete": result["complete"],
        "nodes": result["nodes"],
        "seconds": result["seconds"],
        "sample_sets": result["sets"][:20],
    }
    out = OUT / "fact_10x10_minimal_maximal.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False), flush=True)
    print(f"wrote {out}", flush=True)


if __name__ == "__main__":
    main()
