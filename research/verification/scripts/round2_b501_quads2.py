#!/usr/bin/env python3
"""Round2 B523-B526 follow-up: share-3 triples + line/circle bundles on 4x4.
Faster subset of round2_b501_quads.py.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from fractions import Fraction
from itertools import combinations
from math import gcd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, square_points  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "round2_b501.json"


class BoardQuads(Board):
    def __init__(self, points, quads, name=""):
        self.points = list(points)
        self.V = len(self.points)
        self.name = name
        self.rows = [(x * x + y * y, x, y, 1) for (x, y) in self.points]
        self.quads = list(quads)
        self.quads_by_pt = [[] for _ in range(self.V)]
        for m in self.quads:
            for i in range(self.V):
                if m & (1 << i):
                    self.quads_by_pt[i].append(m)
        self.full = (1 << self.V) - 1


def classify_quad(pts):
    (x1, y1), (x2, y2), (x3, y3), (x4, y4) = pts

    def cross(ax, ay, bx, by):
        return ax * by - ay * bx

    c1 = cross(x2 - x1, y2 - y1, x3 - x1, y3 - y1)
    c2 = cross(x2 - x1, y2 - y1, x4 - x1, y4 - y1)
    return "line" if (c1 == 0 and c2 == 0) else "circle"


def solve_w(b):
    g = b.solve_grundy()
    return "first" if g.get(0, 0) > 0 else "second", g.get(0, -1)


def line_key(pts):
    (x1, y1), (x2, y2) = pts[0], pts[1]
    a = y1 - y2
    b = x2 - x1
    c = a * x1 + b * y1
    g = 0
    for t in (a, b, c):
        g = gcd(g, abs(t))
    if g:
        a, b, c = a // g, b // g, c // g
    if a < 0 or (a == 0 and b < 0):
        a, b, c = -a, -b, -c
    return ("L", a, b, c)


def circle_key(pts):
    (x0, y0), (x1, y1), (x2, y2) = pts[0], pts[1], pts[2]
    d = 2 * (x0 * (y1 - y2) + x1 * (y2 - y0) + x2 * (y0 - y1))
    if d == 0:
        return None
    ux = Fraction(
        (x0 * x0 + y0 * y0) * (y1 - y2)
        + (x1 * x1 + y1 * y1) * (y2 - y0)
        + (x2 * x2 + y2 * y2) * (y0 - y1), d
    )
    uy = Fraction(
        (x0 * x0 + y0 * y0) * (x2 - x1)
        + (x1 * x1 + y1 * y1) * (x0 - x2)
        + (x2 * x2 + y2 * y2) * (x1 - x0), d
    )
    r2 = (x0 - ux) ** 2 + (y0 - uy) ** 2
    return ("C", ux, uy, r2)


def main():
    n = 4
    pts = square_points(n)
    base = Board(pts, name="4x4")
    base_w, base_gv = solve_w(base)
    all_quads = list(base.quads)
    kinds = {}
    for m in all_quads:
        ids = [i for i in range(16) if m & (1 << i)]
        kinds[m] = classify_quad([pts[i] for i in ids])
    kind_hist = Counter(kinds.values())

    # share-3 triples only
    by_core = defaultdict(list)
    for m in all_quads:
        ids = [i for i in range(16) if m & (1 << i)]
        for core in combinations(ids, 3):
            by_core[core].append(m)
    triple_cands = []
    for core, ms in by_core.items():
        if len(ms) >= 3:
            for t in combinations(ms, 3):
                triple_cands.append((t, core, len(ms)))
        elif len(ms) == 2:
            # 2 quads sharing 3 points — try adding any third that shares core
            pass
    print(f"share-3 triple cands: {len(triple_cands)}", flush=True)

    triple_flips = []
    tested = 0
    seen = set()
    for t, core, nm in triple_cands:
        key = tuple(sorted(t))
        if key in seen:
            continue
        seen.add(key)
        tested += 1
        qs = [q for q in all_quads if q not in t]
        bd = BoardQuads(pts, qs, name="4x4-3q")
        w, gv = solve_w(bd)
        if w != base_w:
            triple_flips.append(
                {"removed": list(t), "core": list(core),
                 "n_on_core": nm,
                 "kinds": [kinds[x] for x in t], "g": gv}
            )
        if tested >= 120:
            break
    print(f"share-3 triple flips: {len(triple_flips)}/{tested}", flush=True)

    # also: 2 quads sharing 3 pts + 1 disjoint / overlapping
    extra_cands = []
    for core, ms in by_core.items():
        if len(ms) == 2:
            a, b = ms
            for c in all_quads:
                if c != a and c != b:
                    extra_cands.append((a, b, c))
                    if len(extra_cands) >= 60:
                        break
        if len(extra_cands) >= 60:
            break
    extra_flips = []
    et = 0
    for t in extra_cands:
        et += 1
        qs = [q for q in all_quads if q not in t]
        bd = BoardQuads(pts, qs, name="4x4-3q2")
        w, gv = solve_w(bd)
        if w != base_w:
            extra_flips.append({"kinds": [kinds[x] for x in t], "g": gv})
        if et >= 40:
            break
    print(f"extra triple flips: {len(extra_flips)}/{et}", flush=True)

    # bundles: all quads on same line / same circle
    carriers = defaultdict(list)
    for m in all_quads:
        ids = [i for i in range(16) if m & (1 << i)]
        coords = [pts[i] for i in ids]
        k = line_key(coords) if kinds[m] == "line" else circle_key(coords)
        carriers[k].append(m)
    bundle_rows = []
    for k, ms in sorted(carriers.items(), key=lambda kv: -len(kv[1])):
        if len(ms) < 2:
            continue
        qs = [q for q in all_quads if q not in ms]
        bd = BoardQuads(pts, qs, name="bundle")
        w, gv = solve_w(bd)
        bundle_rows.append(
            {"kind": k[0], "n_quads": len(ms), "winner": w, "g": gv,
             "flip": w != base_w,
             "n_pts": len({i for m in ms for i in range(16) if m & (1 << i)})}
        )
    flips_b = [r for r in bundle_rows if r["flip"]]
    print(f"bundles: {len(flips_b)} flips / {len(bundle_rows)}", flush=True)

    # B525 specifically: true circles only
    circ = [r for r in bundle_rows if r["kind"] == "C"]
    line = [r for r in bundle_rows if r["kind"] == "L"]
    circ_flips = [r for r in circ if r["flip"]]
    line_flips = [r for r in line if r["flip"]]

    out = {
        "kind_hist": dict(kind_hist),
        "base_g": base_gv,
        "base_winner": base_w,
        "share3_triples_tested": tested,
        "share3_triple_flips": len(triple_flips),
        "share3_triple_examples": triple_flips[:8],
        "extra_triples_tested": et,
        "extra_triple_flips": len(extra_flips),
        "bundles": bundle_rows,
        "n_bundles": len(bundle_rows),
        "n_bundle_flips": len(flips_b),
        "circles_tested": len(circ),
        "circle_bundle_flips": len(circ_flips),
        "lines_tested": len(line),
        "line_bundle_flips": len(line_flips),
        "circle_flip_examples": circ_flips[:5],
        "line_flip_examples": line_flips[:5],
    }

    if OUT.exists():
        old = json.loads(OUT.read_text(encoding="utf-8"))
    else:
        old = {}
    old.setdefault("quads_n4", {}).update(out)
    # keep prior partial keys if any
    OUT.write_text(json.dumps(old, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
