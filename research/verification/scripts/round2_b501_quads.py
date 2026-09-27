#!/usr/bin/env python3
"""Round2 B521-B530: forbidden-quad removal on 4x4 (and n=3).

Remove some forbidden quads from the constraint set (i.e. those 4-point
sets become legal) and re-solve empty-board winner.
Outputs research/verification/round2_b501.json (quads section).
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, board_square, det4, square_points  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "round2_b501.json"


class BoardQuads(Board):
    """Board with a custom forbidden-quad list (subset of geometric quads)."""

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


def quad_mask(ids):
    m = 0
    for i in ids:
        m |= 1 << i
    return m


def classify_quad(pts):
    """Return 'line' or 'circle' (true circle, not collinear)."""
    # collinear iff area of any triangle among 3 is 0... use slopes
    # check if all 4 collinear: det of 3 vectors
    (x1, y1), (x2, y2), (x3, y3), (x4, y4) = pts
    # cross of (p2-p1, p3-p1) and (p2-p1, p4-p1)
    def cross(ax, ay, bx, by):
        return ax * by - ay * bx
    c1 = cross(x2 - x1, y2 - y1, x3 - x1, y3 - y1)
    c2 = cross(x2 - x1, y2 - y1, x4 - x1, y4 - y1)
    if c1 == 0 and c2 == 0:
        return "line"
    return "circle"


def solve_w(g_map):
    return "first" if g_map.get(0, 0) > 0 else "second"


def main():
    data = {}
    # --- n=4: 194 forbidden quads ---
    n = 4
    pts = square_points(n)
    base = Board(pts, name="4x4")
    base_g = base.solve_grundy()
    base_w = solve_w(base_g)
    base_gv = base_g.get(0, -1)
    all_quads = list(base.quads)
    print(f"[quads] n=4 F={len(all_quads)} empty g={base_gv} winner={base_w}", flush=True)

    # classify
    kinds = {}
    for m in all_quads:
        ids = [i for i in range(16) if m & (1 << i)]
        coords = [pts[i] for i in ids]
        kinds[m] = classify_quad(coords)
    kind_hist = Counter(kinds.values())

    # --- B521/B522: remove 1, 2, 3 quads ---
    # single removal
    single_flips = []
    for m in all_quads:
        qs = [q for q in all_quads if q != m]
        b = BoardQuads(pts, qs, name="4x4-1q")
        g = b.solve_grundy()
        if solve_w(g) != base_w:
            single_flips.append({"removed": m, "kind": kinds[m],
                                 "ids": [i for i in range(16) if m & (1 << i)],
                                 "g": g.get(0, -1)})
    print(f"[quads] n=4 single removals: {len(single_flips)} flips", flush=True)

    # pair removals: all C(194,2)=18721 is a lot of full solves.
    # Restrict to: (a) pairs of harmless singles (not in single_flips),
    # (b) pairs sharing 3 points, (c) one line + one circle sharing 3pts.
    harmless = [m for m in all_quads if m not in {r["removed"] for r in single_flips}]
    print(f"[quads] harmless singles: {len(harmless)}", flush=True)

    def share3(a, b):
        return bin(a & b).count("1") >= 3

    pair_candidates = []
    seen = set()
    # share-3 pairs among all quads
    for i, j in combinations(range(len(all_quads)), 2):
        a, b = all_quads[i], all_quads[j]
        if share3(a, b):
            key = (a, b)
            if key not in seen:
                seen.add(key)
                pair_candidates.append((a, b))
    # plus 80 random-ish pairs of harmless
    import itertools
    hp = list(combinations(harmless[:40], 2))[:80]
    for a, b in hp:
        key = (min(a, b), max(a, b))
        if key not in seen:
            seen.add(key)
            pair_candidates.append((a, b))
    print(f"[quads] pair candidates: {len(pair_candidates)}", flush=True)

    pair_flips = []
    pair_tested = 0
    for a, b in pair_candidates:
        pair_tested += 1
        qs = [q for q in all_quads if q != a and q != b]
        bd = BoardQuads(pts, qs, name="4x4-2q")
        g = bd.solve_grundy()
        if solve_w(g) != base_w:
            pair_flips.append(
                {"removed": [a, b],
                 "kinds": [kinds[a], kinds[b]],
                 "share3": share3(a, b),
                 "g": g.get(0, -1)}
            )
    print(f"[quads] pair flips: {len(pair_flips)}/{pair_tested}", flush=True)

    # triple removals: among pair-flips or share-3 clusters
    triple_flips = []
    triple_tested = 0
    # take share-3 triples (3 quads on same 3 points)
    by_core = defaultdict(list)
    for m in all_quads:
        ids = [i for i in range(16) if m & (1 << i)]
        for core in combinations(ids, 3):
            by_core[core].append(m)
    triple_cands = []
    for core, ms in by_core.items():
        if len(ms) >= 3:
            for t in combinations(ms, 3):
                triple_cands.append(t)
    # plus triples from pair_flips extended
    for rec in pair_flips[:20]:
        a, b = rec["removed"]
        for c in all_quads:
            if c != a and c != b:
                triple_cands.append((a, b, c))
    print(f"[quads] triple cands: {len(triple_cands)}", flush=True)
    seen3 = set()
    for t in triple_cands:
        key = tuple(sorted(t))
        if key in seen3:
            continue
        seen3.add(key)
        triple_tested += 1
        qs = [q for q in all_quads if q not in t]
        bd = BoardQuads(pts, qs, name="4x4-3q")
        g = bd.solve_grundy()
        if solve_w(g) != base_w:
            triple_flips.append(
                {"removed": list(t),
                 "kinds": [kinds[x] for x in t],
                 "g": g.get(0, -1)}
            )
        if triple_tested >= 80:
            break
    print(f"[quads] triple flips: {len(triple_flips)}/{triple_tested}", flush=True)

    # --- B525/B526: remove ALL quads of one circle / one line ---
    # group by geometric carrier: for lines, the line direction+offset;
    # for circles, center/radius. Reconstruct from point sets.
    def line_key(ids):
        # line through 2 points; all 4 collinear
        p = [pts[i] for i in ids]
        # find two distinct
        (x1, y1), (x2, y2) = p[0], p[1]
        # a*x+b*y=c with a=y1-y2, b=x2-x1, c=a*x1+b*y1
        a = y1 - y2
        b = x2 - x1
        c = a * x1 + b * y1
        g = 0
        for t in (a, b, c):
            g = __import__("math").gcd(g, abs(t))
        if g:
            a, b, c = a // g, b // g, c // g
        if a < 0 or (a == 0 and b < 0):
            a, b, c = -a, -b, -c
        return ("L", a, b, c)

    def circle_key(ids):
        # circumcircle of first 3, verify 4th
        # solve center as intersection of perpendicular bisectors — use integer
        # Instead: pack the 4 points sorted as key (same circle iff same set
        # of cocircular pts — but different quads can share a circle).
        # Compute circumcenter rationally.
        import fractions
        p = [pts[i] for i in ids]

        def circum(q0, q1, q2):
            (x0, y0), (x1, y1), (x2, y2) = q0, q1, q2
            d = 2 * (x0 * (y1 - y2) + x1 * (y2 - y0) + x2 * (y0 - y1))
            if d == 0:
                return None
            ux = (
                (x0 * x0 + y0 * y0) * (y1 - y2)
                + (x1 * x1 + y1 * y1) * (y2 - y0)
                + (x2 * x2 + y2 * y2) * (y0 - y1)
            ) / d
            uy = (
                (x0 * x0 + y0 * y0) * (x2 - x1)
                + (x1 * x1 + y1 * y1) * (x0 - x2)
                + (x2 * x2 + y2 * y2) * (x1 - x0)
            ) / d
            r2 = (x0 - ux) ** 2 + (y0 - uy) ** 2
            return (ux, uy, r2)

        c = circum(p[0], p[1], p[2])
        if c is None:
            return None
        ux, uy, r2 = c
        # use Fraction-free: double is OK if we round; better exact
        from fractions import Fraction
        # redo with Fraction
        def fr_circum(q0, q1, q2):
            (x0, y0), (x1, y1), (x2, y2) = q0, q1, q2
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
            return (ux, uy, r2)

        fc = fr_circum(p[0], p[1], p[2])
        return ("C", fc[0], fc[1], fc[2])

    carriers = defaultdict(list)
    for m in all_quads:
        ids = tuple(i for i in range(16) if m & (1 << i))
        coords = [pts[i] for i in ids]
        if kinds[m] == "line":
            k = line_key(ids)
        else:
            k = circle_key(ids)
        carriers[k].append(m)

    bundle_flips = []
    bundle_tested = 0
    for k, ms in carriers.items():
        if len(ms) < 2:
            continue
        bundle_tested += 1
        qs = [q for q in all_quads if q not in ms]
        bd = BoardQuads(pts, qs, name=f"4x4-bundle")
        g = bd.solve_grundy()
        if solve_w(g) != base_w:
            bundle_flips.append(
                {"carrier_kind": k[0] if k else "?",
                 "n_quads": len(ms),
                 "g": g.get(0, -1)}
            )
    print(f"[quads] bundles: {bundle_flips} / {bundle_tested}", flush=True)

    data["quads_n4"] = {
        "F": len(all_quads),
        "kind_hist": dict(kind_hist),
        "base_g": base_gv,
        "base_winner": base_w,
        "B521_single_removal_flips": len(single_flips),
        "B521_single_examples": single_flips[:5],
        "B522_pairs_tested": pair_tested,
        "B522_pair_flips": len(pair_flips),
        "B522_pair_examples": [
            {"kinds": r["kinds"], "share3": r["share3"], "g": r["g"]}
            for r in pair_flips[:8]
        ],
        "B522_triples_tested": triple_tested,
        "B522_triple_flips": len(triple_flips),
        "B522_triple_examples": [
            {"kinds": r["kinds"], "g": r["g"]} for r in triple_flips[:8]
        ],
        "B523_share3_triple_flips": sum(
            1 for r in triple_flips if len({tuple(sorted(r["removed"]))}) == 1
        ),
        "B525_B526_bundles_tested": bundle_tested,
        "B525_B526_bundle_flips": bundle_flips,
    }

    # --- n=3: F=1, removing the only quad makes everything free ---
    n = 3
    pts3 = square_points(n)
    b3 = Board(pts3, name="3x3")
    g3 = b3.solve_grundy()
    # remove the single quad
    b3b = BoardQuads(pts3, [], name="3x3-1q")
    g3b = b3b.solve_grundy()
    data["quads_n3"] = {
        "F": len(b3.quads),
        "base_g": g3.get(0, -1),
        "base_winner": solve_w(g3),
        "after_remove_all_g": g3b.get(0, -1),
        "after_remove_all_winner": solve_w(g3b),
    }

    if OUT.exists():
        old = json.loads(OUT.read_text(encoding="utf-8"))
    else:
        old = {}
    old.update(data)
    OUT.write_text(json.dumps(old, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
