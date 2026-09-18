#!/usr/bin/env python3
"""Deep-dive into Cycle 5 Grundy findings on n=4, n=5."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "night-research"

sys.path.insert(0, str(OUT_DIR))
from grundy_cycle5 import (
    build_index,
    forbidden_quads,
    legal_moves,
    mex,
)


def d4_orbit(n: int, occ: int) -> list[int]:
    V = n * n
    pts = [(i % n, i // n) for i in range(V) if occ >> i & 1]

    def to_occ(transform):
        o = 0
        for (x, y) in pts:
            nx, ny = transform(x, y)
            o |= 1 << (ny * n + nx)
        return o

    ts = [
        lambda x, y: (x, y),
        lambda x, y: (n - 1 - x, y),
        lambda x, y: (x, n - 1 - y),
        lambda x, y: (n - 1 - x, n - 1 - y),
        lambda x, y: (y, x),
        lambda x, y: (n - 1 - y, x),
        lambda x, y: (y, n - 1 - x),
        lambda x, y: (n - 1 - y, n - 1 - x),
    ]
    return sorted(set(to_occ(t) for t in ts))


def canonical(orbit: list[int]) -> int:
    return min(orbit)


def grundy_all(n: int, quads_by_pt) -> dict[int, int]:
    V = n * n
    memo: dict[int, int] = {}
    sys.setrecursionlimit(1000000)

    def ev(occ: int) -> int:
        if occ in memo:
            return memo[occ]
        mv = legal_moves(occ, V, quads_by_pt)
        if not mv:
            memo[occ] = 0
            return 0
        g = mex(ev(occ | (1 << u)) for u in mv)
        memo[occ] = g
        return g

    ev(0)
    return memo


def cell_name(n: int, v: int) -> str:
    return f"({v % n},{v // n})"


def analyze_n5(quads_by_pt):
    n, V = 5, 25
    g = grundy_all(n, quads_by_pt)
    losing_first = [v for v in range(V) if g[1 << v] != 0]

    seen_orbits = {}
    for v in range(V):
        orb = canonical(d4_orbit(n, 1 << v))
        seen_orbits.setdefault(orb, []).append(v)

    orbit_table = []
    for orb, members in sorted(seen_orbits.items(), key=lambda kv: kv[0]):
        rep = members[0]
        orbit_table.append({
            "rep": cell_name(n, rep),
            "orbit_size": len(d4_orbit(n, 1 << rep)),
            "grundy": g[1 << rep],
            "first_move_result": "WIN" if g[1 << rep] == 0 else "LOSS",
        })

    agg = {}
    for orb, members in sorted(seen_orbits.items(), key=lambda kv: kv[0]):
        rep = members[0]
        if g[1 << rep] == 0:
            continue
        occ = 1 << rep
        mv = legal_moves(occ, V, quads_by_pt)
        hist = defaultdict(int)
        for u in mv:
            hist[g[occ | (1 << u)]] += 1
        agg[cell_name(n, rep)] = {
            "orbit_size": len(d4_orbit(n, 1 << rep)),
            "grundy": g[1 << rep],
            "child_nimber_hist": {str(k): hist[k] for k in sorted(hist)},
        }

    return {
        "orbit_table": orbit_table,
        "losing_first_uniform_grundy": sorted(set(g[1 << v] for v in losing_first)),
        "losing_first_child_patterns_by_orbit": agg,
    }


def analyze_n4(quads_by_pt):
    n, V = 4, 16
    g = grundy_all(n, quads_by_pt)

    pairs = list(combinations(range(V), 2))
    nonzero = []
    unsafe = 0
    for a, b in pairs:
        occ = (1 << a) | (1 << b)
        if occ not in g:
            unsafe += 1
            continue
        if g[occ] != 0:
            nonzero.append((a, b, g[occ], canonical(d4_orbit(n, occ))))

    by_orbit = defaultdict(list)
    for a, b, gg, orb in nonzero:
        by_orbit[orb].append((cell_name(n, a), cell_name(n, b), gg))

    orbit_summary = []
    for orb, members in sorted(by_orbit.items(), key=lambda kv: kv[0]):
        gs = sorted(set(m[2] for m in members))
        orbit_summary.append({
            "orbit_size": len(d4_orbit(n, orb)),
            "grundy_values": gs,
            "uniform": len(gs) == 1,
            "example": members[0][:2],
            "count": len(members),
        })

    return {
        "k2_total_pairs": len(pairs),
        "k2_unsafe_pairs": unsafe,
        "k2_safe_pairs": len(pairs) - unsafe,
        "k2_nonzero_count": len(nonzero),
        "k2_nonzero_orbits": orbit_summary,
    }


def main():
    res = {}
    for n in (4, 5):
        quads = forbidden_quads(n)
        qbp = build_index(n, quads)
        if n == 4:
            res["n4"] = analyze_n4(qbp)
        else:
            res["n5"] = analyze_n5(qbp)
    (OUT_DIR / "cycle5-grundy-deepdive.json").write_text(
        json.dumps(res, indent=2), encoding="utf-8"
    )
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

