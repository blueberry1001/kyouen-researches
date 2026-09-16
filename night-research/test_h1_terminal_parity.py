#!/usr/bin/env python3
"""H1: terminal-parity locking for maximal kyouen-free sets on n<=6.

For each n, enumerate ALL maximal kyouen-free sets (no grid point can be added).
Check whether all have the same parity, and whether that parity matches the known winner.
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent

WINNERS = {1: "F", 2: "F", 3: "F", 4: "S", 5: "F", 6: "F", 7: "S", 8: "S", 9: "F"}


def forbidden_4sets(n: int) -> list[tuple[int, ...]]:
    def coords(i: int) -> tuple[int, int]:
        return (i % n, i // n)

    def det4(m: list[list[int]]) -> int:
        def det3(a: list[list[int]]) -> int:
            return (
                a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
                - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
                + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0])
            )

        s = 0
        for c in range(4):
            minor = [[m[r][cc] for cc in range(4) if cc != c] for r in range(1, 4)]
            s += ((-1) ** c) * m[0][c] * det3(minor)
        return s

    from itertools import combinations

    out = []
    V = n * n
    for combo in combinations(range(V), 4):
        xs = []
        ys = []
        for p in combo:
            x, y = coords(p)
            xs.append(x)
            ys.append(y)
        m = [[xs[i] * xs[i] + ys[i] * ys[i], xs[i], ys[i], 1] for i in range(4)]
        if det4(m) == 0:
            out.append(combo)
    return out


def enumerate_maximal(n: int, max_sets: int = 200000) -> dict:
    forb = forbidden_4sets(n)
    V = n * n
    # bitsets of forbidden patterns containing each point
    point_forb = [[] for _ in range(V)]
    forb_bits = []
    for idx, F in enumerate(forb):
        b = 0
        for p in F:
            b |= 1 << p
            point_forb[p].append(idx)
        forb_bits.append(b)

    maximal: list[int] = []  # bitmasks
    sizes: list[int] = []

    def ok(mask: int) -> bool:
        # no forbidden 4-set fully inside mask
        # checked incrementally on add
        return True

    def would_forbid(mask: int, v: int) -> bool:
        new = mask | (1 << v)
        for idx in point_forb[v]:
            if (forb_bits[idx] & new) == forb_bits[idx]:
                return True
        return False

    def can_add_any(mask: int) -> bool:
        used = mask
        v = 0
        while v < V:
            if (used >> v) & 1:
                v += 1
                continue
            if not would_forbid(mask, v):
                return True
            v += 1
        return False

    def dfs(mask: int, start: int) -> None:
        if len(maximal) >= max_sets:
            return
        # try add points >= start to keep some order; still need full maximal check
        added = False
        for v in range(start, V):
            if (mask >> v) & 1:
                continue
            if would_forbid(mask, v):
                continue
            added = True
            dfs(mask | (1 << v), v + 1)
            if len(maximal) >= max_sets:
                return
        if not added:
            # may still be extendable by a point < start that was skipped due to order
            if can_add_any(mask):
                return
            maximal.append(mask)
            sizes.append(mask.bit_count())

    dfs(0, 0)

    parities = {s % 2 for s in sizes}
    from collections import Counter

    size_hist = Counter(sizes)
    result = {
        "n": n,
        "V": V,
        "n_forbidden": len(forb),
        "n_maximal_found": len(maximal),
        "hit_cap": len(maximal) >= max_sets,
        "size_hist": dict(sorted(size_hist.items())),
        "parities": sorted(parities),
        "parity_locked": len(parities) == 1,
        "locked_parity": next(iter(parities)) if len(parities) == 1 else None,
        "winner": WINNERS[n],
        "predicted_parity_odd_iff_first_win": (next(iter(parities)) == 1) if len(parities) == 1 else None,
        "matches_winner": (
            (next(iter(parities)) == 1 and WINNERS[n] == "F")
            or (next(iter(parities)) == 0 and WINNERS[n] == "S")
            if len(parities) == 1
            else None
        ),
    }
    return result


def main() -> None:
    results = []
    for n in range(1, 7):
        print(f"n={n} ...", flush=True)
        r = enumerate_maximal(n, max_sets=500000)
        results.append(r)
        print(json.dumps(r, ensure_ascii=False), flush=True)
    (OUT / "h1-terminal-parity.json").write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
