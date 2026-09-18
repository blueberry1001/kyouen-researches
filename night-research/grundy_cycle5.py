#!/usr/bin/env python3
"""Cycle 5: exact Grundy (nimber) structure of Kyouen on small boards.

g(S) = mex { g(S+v) : v legal }; terminal safe positions get g = 0.
"""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "night-research"


def det4(p0, p1, p2, p3) -> int:
    rows = [p0, p1, p2, p3]

    def minor3(r, cols):
        m = [[rows[i][c] for c in cols] for i in r]
        return (
            m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
        )

    det = 0
    for c0 in range(4):
        sign = 1 if c0 % 2 == 0 else -1
        cols = [c for c in range(4) if c != c0]
        det += sign * rows[0][c0] * minor3([1, 2, 3], cols)
    return det


def point_rows(n: int):
    return [(x * x + y * y, x, y, 1) for y in range(n) for x in range(n)]


def forbidden_quads(n: int):
    rows = point_rows(n)
    quads = []
    for ids in combinations(range(n * n), 4):
        if det4(*[rows[i] for i in ids]) == 0:
            quads.append(ids)
    return quads


def build_index(n: int, quads):
    quads_by_pt = [[] for _ in range(n * n)]
    for ids in quads:
        m = 0
        for i in ids:
            m |= 1 << i
        for i in ids:
            quads_by_pt[i].append(m)
    return quads_by_pt


def legal_moves(occ: int, V: int, quads_by_pt):
    moves = []
    empty = ((1 << V) - 1) ^ occ
    v = 0
    while empty:
        if empty & 1:
            mask = occ | (1 << v)
            if all((q & mask) != q for q in quads_by_pt[v]):
                moves.append(v)
        empty >>= 1
        v += 1
    return moves


def mex(values) -> int:
    s = set(values)
    g = 0
    while g in s:
        g += 1
    return g


def grundy_table(n: int, quads_by_pt, max_stones: int | None = None):
    """DFS memo over reachable safe positions. If max_stones is set,
    positions at that stone count are forced to g=0 (capped; not exact)."""
    V = n * n
    grundy: dict[int, int] = {}
    sys.setrecursionlimit(1000000)

    def eval_g(occ: int) -> int:
        g = grundy.get(occ)
        if g is not None:
            return g
        if max_stones is not None and bin(occ).count("1") >= max_stones:
            grundy[occ] = 0
            return 0
        mv = legal_moves(occ, V, quads_by_pt)
        if not mv:
            grundy[occ] = 0
            return 0
        g = mex(eval_g(occ | (1 << u)) for u in mv)
        grundy[occ] = g
        return g

    eval_g(0)
    return grundy



def analyze_board(n: int, max_stones: int | None = None):
    t0 = time.time()
    quads = forbidden_quads(n)
    quads_by_pt = build_index(n, quads)
    tq = time.time() - t0
    print(f"[n={n}] forbidden quads: {len(quads)} ({tq:.2f}s)", flush=True)

    t0 = time.time()
    grundy = grundy_table(n, quads_by_pt, max_stones=max_stones)
    te = time.time() - t0
    capped = max_stones is not None
    print(f"[n={n}] positions: {len(grundy)} ({te:.2f}s) capped={capped}", flush=True)

    by_k = defaultdict(lambda: defaultdict(int))
    for occ, g in grundy.items():
        k = bin(occ).count("1")
        if capped and k >= max_stones:
            continue
        by_k[k][g] += 1

    layer_profiles = {}
    max_g_overall = 0
    nimbers_seen = set()
    for k in sorted(by_k):
        hist = dict(sorted(by_k[k].items()))
        total = sum(hist.values())
        layer_profiles[str(k)] = {
            "count": total,
            "grundy_hist": {str(g): c for g, c in hist.items()},
            "max_grundy": max(hist),
            "zero_rate": hist.get(0, 0) / total,
        }
        max_g_overall = max(max_g_overall, max(hist))
        nimbers_seen.update(hist.keys())

    result = {
        "n": n,
        "forbidden_quads": len(quads),
        "positions_evaluated": len(grundy),
        "capped_at_stones": max_stones,
        "empty_grundy": grundy[0],
        "max_grundy": max_g_overall,
        "nimbers_seen": sorted(nimbers_seen),
        "missing_small_nimbers": [g for g in range(max_g_overall + 1) if g not in nimbers_seen],
        "layer_profiles": layer_profiles,
        "seconds": round(time.time() - t0 + tq, 3),
    }
    return result, grundy, quads_by_pt


def verify_consistency(grundy, quads_by_pt, V, max_stones=None):
    """Check g == mex(child g) on all non-capped positions."""
    bad = 0
    checked = 0
    for occ, g in grundy.items():
        if max_stones is not None and bin(occ).count("1") >= max_stones:
            continue
        mv = legal_moves(occ, V, quads_by_pt)
        child_gs = [grundy.get(occ | (1 << u)) for u in mv]
        if any(c is None for c in child_gs):
            continue
        checked += 1
        if g != mex(child_gs):
            bad += 1
    return {"checked": checked, "mex_violations": bad}



def main(argv):
    sizes = [int(a) for a in argv[1:]] or [2, 3, 4, 5]
    caps = {2: None, 3: None, 4: None, 5: None, 6: 12}
    all_results = {"boards": []}
    for n in sizes:
        cap = caps.get(n)
        result, grundy, quads_by_pt = analyze_board(n, max_stones=cap)
        cons = verify_consistency(grundy, quads_by_pt, n * n, max_stones=cap)
        result["consistency"] = cons
        all_results["boards"].append(result)
        (OUT_DIR / f"cycle5-grundy-n{n}.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        print(
            f"[n={n}] empty_g={result['empty_grundy']} max_g={result['max_grundy']} "
            f"nimbers={result['nimbers_seen']} missing={result['missing_small_nimbers']} "
            f"mex_violations={cons['mex_violations']}/{cons['checked']}",
            flush=True,
        )

    (OUT_DIR / "cycle5-grundy-structure.json").write_text(
        json.dumps(all_results, indent=2), encoding="utf-8"
    )
    print(f"wrote {OUT_DIR / 'cycle5-grundy-structure.json'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

