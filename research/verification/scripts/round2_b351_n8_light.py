#!/usr/bin/env python3
"""Lightweight 8-stone witness analysis only (no heavy search)."""
from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
from kyouen_core import board_square  # noqa: E402

OUT = ROOT / "research" / "verification" / "round2_b351.json"


def mask_ids(m):
    out = []
    while m:
        b = m & -m
        out.append(b.bit_length() - 1)
        m ^= b
    return out


def build_triple_comp(board):
    tc = {}
    for q in board.quads:
        ids = mask_ids(q)
        for p in ids:
            t = q & ~(1 << p)
            tc.setdefault(t, []).append(p)
    return tc


def main():
    data = json.loads(OUT.read_text()) if OUT.exists() else {}
    board = board_square(8)
    tc = build_triple_comp(board)
    V = 64
    W = [0, 1, 6, 20, 24, 32, 34, 60]
    S = sum(1 << i for i in W)
    assert board.is_safe(S)
    # maximal?
    bvec = [0] * V
    for a, b, c in combinations(W, 3):
        tm = (1 << a) | (1 << b) | (1 << c)
        for p in tc.get(tm, ()):
            bvec[p] += 1
    legal = [p for p in range(V) if not ((S >> p) & 1) and bvec[p] == 0]
    empties = [p for p in range(V) if not ((S >> p) & 1)]

    cols = []
    for a, b, c in combinations(W, 3):
        xa, ya = a % 8, a // 8
        xb, yb = b % 8, b // 8
        xc, yc = c % 8, c // 8
        if (xb - xa) * (yc - ya) - (xc - xa) * (yb - ya) == 0:
            cols.append((a, b, c))

    def ldir(t):
        a, b, _ = t
        dx, dy = (b % 8) - (a % 8), (b // 8) - (a // 8)
        g = abs(__import__("math").gcd(dx, dy)) or 1
        dx, dy = dx // g, dy // g
        if dx < 0 or (dx == 0 and dy < 0):
            dx, dy = -dx, -dy
        return (dx, dy)

    dirs = [ldir(t) for t in cols]
    sides = set()
    corners = []
    for i in W:
        x, y = i % 8, i // 8
        if y == 0:
            sides.add("T")
        if y == 7:
            sides.add("B")
        if x == 0:
            sides.add("L")
        if x == 7:
            sides.add("R")
        if (x, y) in ((0, 0), (7, 0), (0, 7), (7, 7)):
            corners.append(i)

    # D4 orbits
    def orb(i):
        x, y = i % 8, i // 8
        pts = set()
        for sx, sy in (
            (x, y),
            (y, x),
            (7 - x, y),
            (x, 7 - y),
            (7 - x, 7 - y),
            (y, 7 - x),
            (7 - y, x),
            (7 - y, 7 - x),
        ):
            pts.add(sy * 8 + sx)
        return frozenset(pts)

    orbits = {}
    for i in W:
        o = orb(i)
        orbits[o] = orbits.get(o, 0) + 1
    orb_sig = tuple(sorted((len(o), c) for o, c in orbits.items()))

    # deletion stats
    del_stats = []
    for a in W:
        S2 = S & ~(1 << a)
        newly = []
        ids2 = [i for i in W if i != a]
        for p in empties:
            ok = True
            for x, y, z in combinations(ids2, 3):
                tm = (1 << x) | (1 << y) | (1 << z)
                if p in tc.get(tm, ()):
                    ok = False
                    break
            if ok:
                newly.append(p)
        del_stats.append({"removed": a, "count": len(newly), "newly": newly})

    # covering: triples that cover >=1 empty
    trip_cov = {}
    for a, b, c in combinations(W, 3):
        tm = (1 << a) | (1 << b) | (1 << c)
        ps = [p for p in tc.get(tm, ()) if not ((S >> p) & 1)]
        if ps:
            trip_cov[(a, b, c)] = ps
    # greedy set cover count
    remaining = set(empties)
    chosen = []
    trips = list(trip_cov.items())
    while remaining:
        best = max(trips, key=lambda tv: len(set(tv[1]) & remaining), default=None)
        if best is None:
            break
        cover = set(best[1]) & remaining
        if not cover:
            break
        chosen.append(best[0])
        remaining -= cover

    # min b among empties (for rho / single coverage)
    b_empties = [(p, bvec[p]) for p in empties]
    min_b = min(b for _, b in b_empties)
    max_b = max(b for _, b in b_empties)

    # rho: tau of each family
    def tau(triples):
        if not triples:
            return 0
        common = triples[0]
        for t in triples[1:]:
            common &= t
        if common:
            return 1
        pts = 0
        for t in triples:
            pts |= t
        pts = mask_ids(pts)
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                cover = (1 << pts[i]) | (1 << pts[j])
                if all(t & cover for t in triples):
                    return 2
        return 3

    fams = {}
    for a, b, c in combinations(W, 3):
        tm = (1 << a) | (1 << b) | (1 << c)
        for p in tc.get(tm, ()):
            if not ((S >> p) & 1):
                fams.setdefault(p, []).append(tm)
    taus = {p: tau(fams[p]) for p in fams}
    rho = min(taus.values()) if taus else None

    # B378: does any deletion give exactly 1 newly legal?
    del_counts = [d["count"] for d in del_stats]

    wit = {
        "S": W,
        "safe": True,
        "maximal": len(legal) == 0,
        "n_legal": len(legal),
        "n_empty": len(empties),
        "n_collinear_triples": len(cols),
        "collinear_triples": cols,
        "line_directions": dirs,
        "n_distinct_directions": len(set(dirs)),
        "sides": sorted(sides),
        "n_sides": len(sides),
        "corners_used": corners,
        "n_corners": len(corners),
        "d4_orbit_sig": orb_sig,
        "min_b": min_b,
        "max_b": max_b,
        "rho": rho,
        "tau_per_empty": taus,
        "deletion_counts": del_counts,
        "deletion": del_stats,
        "covering_triples": len(trip_cov),
        "greedy_circles": len(chosen),
        "collinear_in_cover": sum(1 for t in chosen if t in cols),
    }
    data["n8_witness_light"] = wit
    data["n8_claim_witness_only"] = {
        "B371_has_collinear": len(cols) >= 1,
        "B372_has_2dirs": len(set(dirs)) >= 2,
        "B373_touch_2sides": len(sides) >= 2,
        "B374_no_corner": len(corners) == 0,
        "B378_del_exactly1": 1 in del_counts,
        "B376_cov_note": f"greedy {len(chosen)} circles, collinear {wit['collinear_in_cover']}",
    }
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    print(json.dumps(wit, indent=1)[:2500])
    print("CLAIMS", data["n8_claim_witness_only"])


if __name__ == "__main__":
    main()
