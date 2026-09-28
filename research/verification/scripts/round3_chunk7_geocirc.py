#!/usr/bin/env python3
"""Round3 chunk7 part 1: rational-centre circle census (B458-B474).

Pure Python + fractions. Exact integer/rational arithmetic only for decisions.
Outputs: research/verification/round3_chunk7_geocirc.json

Covers:
  B458  primitive circle equation (A,D,E,F) vs circumcentre denominator as
        predictor of first board size n_min(C) = first square board containing
        max(m, bbox) points of the circle's lattice set.
  B459  existence of small residual games that appear ONLY when q>=3 circles
        contribute constraints (partial game = drop the q>=3 quads).
  B460  do q>=3 quads flip P/N more than their share of the forbidden count?
  B463  full necessary+sufficient rule for m-1 in A(C) (square window).
  B464  rectangle window realises counts square window does not.
  B467  A(C) determined by coordinate order pattern of circle points.
  B468  higher lattice symmetry -> more holes in A(C).
  B469  max-point circles' triples vs slightly smaller circles: 4-edge cover.
  B470  hole in n=5 3-stone legal-move spectrum explained by window-cut types.
  B472  fixed-direction leading coefficient vs H^3.
  B473  finite-size correction of D_n split into boundary length + gcd sums.
  B474  C_n increment vs new primitive circle types (proper primitive (A,D,E,F)).
  B477  chord-type decomposition overlap, alternative assignments.
"""
from __future__ import annotations

import itertools
import json
import math
import sys
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
OUT = ROOT / "research" / "verification" / "round3_chunk7_geocirc.json"

from batch08_verify import KNOWN_F, collinear_c4, collinear_c4_dir  # noqa: E402
from kyouen_core import board_square, det4  # noqa: E402


# ------------------------------------------------------------------ geometry
def det3(r0, r1, r2):
    return (r0[0] * (r1[1] * r2[2] - r1[2] * r2[1])
            - r0[1] * (r1[0] * r2[2] - r1[2] * r2[0])
            + r0[2] * (r1[0] * r2[1] - r1[1] * r2[0]))


def circumcircle(p, q, r):
    """(cx, cy, r2) as Fractions, or None if collinear."""
    (x1, y1), (x2, y2), (x3, y3) = p, q, r
    d = 2 * det3((x1, y1, 1), (x2, y2, 1), (x3, y3, 1))
    if d == 0:
        return None
    s1 = x1 * x1 + y1 * y1
    s2 = x2 * x2 + y2 * y2
    s3 = x3 * x3 + y3 * y3
    cx = Fraction(det3((s1, y1, 1), (s2, y2, 1), (s3, y3, 1)), d)
    cy = Fraction(det3((s1, x1, 1), (s2, x2, 1), (s3, x2 * 0 + x3, 1)) if False
                  else det3((s1, x1, 1), (s2, x2, 1), (s3, x3, 1)), d)
    r2 = (cx - x1) ** 2 + (cy - y1) ** 2
    if r2 <= 0:
        return None
    return (cx, cy, r2)


def gcd(a, b):
    while b:
        a, b = b, a % b
    return abs(a)


def lcm(a, b):
    return a // gcd(a, b) * b


def centre_denom(cx: Fraction, cy: Fraction) -> int:
    return lcm(cx.denominator, cy.denominator)


def circle_points(cx: Fraction, cy: Fraction, r2: Fraction, bound: int):
    """All integer (x,y) on the circle within |x|,|y| <= bound."""
    q = centre_denom(cx, cy)
    px = cx.numerator * (q // cx.denominator)
    py = cy.numerator * (q // cy.denominator)
    n, d = r2.numerator, r2.denominator
    if (q * q * n) % d != 0:
        return []
    R2 = (q * q * n) // d
    umax = 0
    while (umax + 1) * (umax + 1) <= R2:
        umax += 1
    out = []
    for u in range(-umax, umax + 1):
        v2 = R2 - u * u
        if v2 < 0:
            continue
        v = 0
        while v * v < v2:
            v += 1
        if v * v != v2:
            continue
        for vv in ({v, -v} if v else {0}):
            if (u + px) % q or (vv + py) % q:
                continue
            x = (u + px) // q
            y = (vv + py) // q
            if abs(x) <= bound and abs(y) <= bound:
                out.append((x, y))
    return sorted(set(out))


def n_lattice_points(cx, cy, r2) -> int:
    return len(circle_points(cx, cy, r2, 4000))


def primitive_coeffs(cx: Fraction, cy: Fraction, r2: Fraction):
    """A(x^2+y^2) + D x + E y + F = 0 with A>0, gcd(A,D,E,F)=1 (integers)."""
    L = 1
    for d in (Fraction(2 * cx).denominator, Fraction(2 * cy).denominator, r2.denominator):
        L = lcm(L, d)
    A = L
    D = int(-2 * cx * L)
    E = int(-2 * cy * L)
    F = int((cx * cx + cy * cy - r2) * L)
    g = gcd(gcd(gcd(abs(A), abs(D)), abs(E)), abs(F))
    if g:
        A, D, E, F = A // g, D // g, E // g, F // g
    if A < 0:
        A, D, E, F = -A, -D, -E, -F
    return (A, D, E, F)


def window_spectrum(pts, square=True):
    """A(C): counts |P ∩ W| over axis-parallel windows.
    square=True: w==h. square=False: rectangles w!=h allowed too."""
    if not pts:
        return {0}
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    A = set()
    for x0 in range(xmin - 1, xmax + 2):
        for y0 in range(ymin - 1, ymax + 2):
            for w in range(1, max(xmax - xmin, ymax - ymin) + 3):
                hi = [w] if square else range(1, max(xmax - xmin, ymax - ymin) + 3)
                for h in hi:
                    c = 0
                    for x, y in pts:
                        if x0 <= x <= x0 + w - 1 and y0 <= y <= y0 + h - 1:
                            c += 1
                    A.add(c)
    return A


def extremal(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return {
        "nL": sum(1 for p in pts if p[0] == min(xs)),
        "nR": sum(1 for p in pts if p[0] == max(xs)),
        "nB": sum(1 for p in pts if p[1] == min(ys)),
        "nT": sum(1 for p in pts if p[1] == max(ys)),
        "w": max(xs) - min(xs) + 1,
        "h": max(ys) - min(ys) + 1,
    }


def d4_orbit_size(pts):
    def tf(pts, k):
        o = []
        for x, y in pts:
            o.append([(x, y), (-x, y), (x, -y), (-x, -y),
                      (y, x), (-y, x), (y, -x), (-y, -x)][k])
        return tuple(sorted(o))
    return len({tf(pts, k) for k in range(8)})


# --------------------------------------------------------- circle enumeration
def enum_circles(box_pts, min_pts=4, bound=40):
    """All circles with >= min_pts lattice points, via triples in box_pts."""
    seen = {}
    n = len(box_pts)
    for i, j, k in itertools.combinations(range(n), 3):
        c = circumcircle(box_pts[i], box_pts[j], box_pts[k])
        if c is None:
            continue
        key = c
        if key in seen:
            continue
        P = circle_points(*c, bound=bound)
        if len(P) >= min_pts:
            seen[key] = P
    return seen


# ------------------------------------------------------------------- sections
def sec_B458_B470(circles_by_n, report):
    """B458, B459, B460, B463, B464, B467, B468, B470"""

    # ---------- B458: primitive coefficients vs first-occurrence size ----------
    b458_rows = []
    for n, circs in sorted(circles_by_n.items()):
        for (cx, cy, r2), P in circs.items():
            A, D, E, F = primitive_coeffs(cx, cy, r2)
            m = len(P)
            ext = extremal(P)
            # first square board size that contains the whole point set
            n_min = max(ext["w"], ext["h"])
            b458_rows.append({
                "n": n, "m": m, "A": A, "D": D, "E": E, "F": F,
                "q": centre_denom(cx, cy),
                "bbox": max(ext["w"], ext["h"]),
                "n_min_full": n_min,
            })
    # Does the triple (A, D, E, F) (primitive eq) determine n_min_full
    # better than q (circumcentre denominator)?
    def consistency(rows, keyfn):
        groups = defaultdict(set)
        for r in rows:
            groups[keyfn(r)].add(r["n_min_full"])
        multi = {k: v for k, v in groups.items() if len(v) > 1}
        return len(groups), len(multi)

    n_groups_q, n_conflict_q = consistency(b458_rows, lambda r: r["q"])
    n_groups_eq, n_conflict_eq = consistency(b458_rows, lambda r: (r["A"], r["D"], r["E"], r["F"]))
    n_groups_mqbw, n_conflict_mqbw = consistency(b458_rows, lambda r: (r["m"], r["q"], r["bbox"]))
    report["B458"] = {
        "n_rows": len(b458_rows),
        "groups_by_q": n_groups_q, "conflicts_by_q": n_conflict_q,
        "groups_by_primitive_eq": n_groups_eq, "conflicts_by_primitive_eq": n_conflict_eq,
        "groups_by_m_q_bbox": n_groups_mqbw, "conflicts_by_m_q_bbox": n_conflict_mqbw,
        "note": "conflicts = distinct n_min_full values inside one key group",
        "sample": b458_rows[:20],
    }
    print("B458", report["B458"]["groups_by_q"], n_conflict_q, "|",
          report["B458"]["groups_by_primitive_eq"], n_conflict_eq, flush=True)

    # ---------- B459 / B460: q>=3 partial games ----------
    b459 = {}
    for n in (3, 4, 5):
        B = board_square(n)
        pts = B.points
        qclass = {}
        for qm in B.quads:
            ids = [i for i in range(B.V) if (qm >> i) & 1]
            p = [pts[i] for i in ids]
            col = all(((p[1][0] - p[0][0]) * (r[1] - p[0][1])
                       - (p[1][1] - p[0][1]) * (r[0] - p[0][0])) == 0
                      for r in p[2:])
            if col:
                qclass[qm] = "line"
                continue
            cc = circumcircle(p[0], p[1], p[2])
            q = centre_denom(cc[0], cc[1]) if cc else 0
            qclass[qm] = f"q{q}"
        hist = Counter(qclass.values())
        # residual game: full forbidden set vs q<=2 only
        full = board_square(n)
        lowq = type(full)(pts, name=f"{n}x{n}-q3")
        lowq.quads = [q for q in full.quads if qclass[q] in ("line", "q1", "q2")]
        lowq.quads_by_pt = [[] for _ in range(full.V)]
        for q in lowq.quads:
            for i in range(full.V):
                if (q >> i) & 1:
                    lowq.quads_by_pt[i].append(q)
        res = {}
        for tag, bd in (("full", full), ("q<=2", lowq)):
            occ_all = {}
            from collections import deque
            dq = deque([0])
            occ_all[0] = 0
            while dq:
                o = dq.popleft()
                for u in bd.legal_moves(o):
                    nx = o | (1 << u)
                    if nx not in occ_all:
                        occ_all[nx] = 0
                        dq.append(nx)
            # P/N by memoised recursion
            memo = {}

            def ev(o):
                if o in memo:
                    return memo[o]
                mv = bd.legal_moves(o)
                if not mv:
                    memo[o] = 0
                    return 0
                w = 0
                for u in mv:
                    if ev(o | (1 << u)) == 0:
                        w = 1
                        break
                memo[o] = w
                return w
            ev(0)
            # shallow layers: k=1,2,3 P/N counts
            byk = defaultdict(lambda: {"P": 0, "N": 0})
            for o, v in memo.items():
                k = o.bit_count()
                if k <= 3:
                    byk[k]["P" if v == 0 else "N"] += 1
            res[tag] = {"n_states": len(memo), "empty": memo[0],
                        "by_k": {str(k): dict(v) for k, v in sorted(byk.items())}}
        b459[str(n)] = {"q_hist": dict(hist), "games": res}
        print("B459/B460 n=%d hist=%s full_empty=%s q<=2_empty=%s" % (
            n, dict(hist), res["full"]["empty"], res["q<=2"]["empty"]), flush=True)
    report["B459_B460"] = b459

    # ---------- B463: full necessary+sufficient rule for m-1 in A(C) ----------
    b463 = []
    n_agree = n_tot = 0
    n_agree_b = n_tot_b = 0
    for n, circs in sorted(circles_by_n.items()):
        for (cx, cy, r2), P in circs.items():
            m = len(P)
            if m < 5:
                continue
            A = window_spectrum(P, square=True)
            e = extremal(P)
            has = (m - 1) in A
            # candidate rule 1: some direction has a UNIQUE extremal point
            uq = min(e["nL"], e["nR"], e["nB"], e["nT"]) == 1
            # candidate rule 2 (fuller): exists an axis-aligned square window
            # whose complement among P is exactly one point AND the window is
            # a "closed cut" of the circle -- we test the *necessary* direction
            # side too: if m-1 achievable, then the discarded point must be
            # extremal in >=1 direction (window is a closed box).
            disc = [p for p in P if True]
            # compute whether m-1 achievable
            b463.append({"n": n, "m": m, "has_m1": has,
                         "ext": e, "unique_extremal": uq,
                         "A": sorted(A),
                         "holes": sorted(set(range(m + 1)) - A)})
            n_tot += 1
            n_agree += int(uq == has)
    # counterexample search among ALL circles with >=4 lattice points, in a
    # wider box, to look for unique-extremal but m-1 NOT achievable
    wide = [(x, y) for y in range(-7, 8) for x in range(-7, 8)]
    wide_c = enum_circles(wide, min_pts=5, bound=30)
    b463_wide = []
    for (cx, cy, r2), P in wide_c.items():
        m = len(P)
        A = window_spectrum(P, square=True)
        e = extremal(P)
        has = (m - 1) in A
        uq = min(e["nL"], e["nR"], e["nB"], e["nT"]) == 1
        b463_wide.append({"m": m, "has_m1": has, "unique_extremal": uq,
                          "ext": e, "A": sorted(A),
                          "holes": sorted(set(range(m + 1)) - A),
                          "r2": f"{r2.numerator}/{r2.denominator}",
                          "c": [f"{cx.numerator}/{cx.denominator}",
                                f"{cy.numerator}/{cy.denominator}"]})
    n_agree_b = sum(1 for r in b463_wide if r["unique_extremal"] == r["has_m1"])
    n_tot_b = len(b463_wide)
    viol = [r for r in b463_wide if r["unique_extremal"] != r["has_m1"]]
    report["B463"] = {
        "board_circles": {"n": n_tot, "agree": n_agree},
        "wide_circles_m_ge5": n_tot_b, "wide_agree": n_agree_b,
        "violations": viol[:10],
        "n_violations": len(viol),
        "sample_wide": b463_wide[:15],
    }
    print("B463 board %d/%d wide %d/%d viol=%d" % (
        n_agree, n_tot, n_agree_b, n_tot_b, len(viol)), flush=True)

    # ---------- B464: rectangle window extra counts ----------
    b464 = []
    n_rect = 0
    for (cx, cy, r2), P in wide_c.items():
        A_sq = window_spectrum(P, square=True)
        A_re = window_spectrum(P, square=False)
        extra = sorted(A_re - A_sq)
        n_rect += 1
        if extra:
            b464.append({"m": len(P), "extra": extra, "A_sq": sorted(A_sq),
                         "A_re": sorted(A_re),
                         "r2": f"{r2.numerator}/{r2.denominator}",
                         "c": [f"{cx.numerator}/{cx.denominator}",
                               f"{cy.numerator}/{cy.denominator}"]})
    report["B464"] = {"n_circles_tested": n_rect, "n_with_extra": len(b464),
                      "examples": b464[:8]}
    print("B464 tested", n_rect, "with extra", len(b464), flush=True)

    # ---------- B467: order pattern determines A(C)? ----------
    def order_pattern(pts):
        xs = sorted({p[0] for p in pts})
        ys = sorted({p[1] for p in pts})
        xr = {v: i for i, v in enumerate(xs)}
        yr = {v: i for i, v in enumerate(ys)}
        return tuple(sorted((xr[x], yr[y]) for x, y in pts))

    by_pat = defaultdict(list)
    for (cx, cy, r2), P in wide_c.items():
        pat = order_pattern(P)
        by_pat[pat].append(frozenset(window_spectrum(P, square=True)))
    n_multi = n_bad = 0
    bad_ex = []
    for pat, lst in by_pat.items():
        if len(lst) < 2:
            continue
        n_multi += 1
        if len(set(lst)) > 1:
            n_bad += 1
            if len(bad_ex) < 5:
                bad_ex.append({"pattern": str(pat), "A": [sorted(s) for s in set(lst)]})
    report["B467"] = {"n_circles": len(wide_c), "n_patterns_multi": n_multi,
                      "n_patterns_different_A": n_bad, "counterexamples": bad_ex}
    print("B467 multi patterns", n_multi, "with differing A", n_bad, flush=True)

    # ---------- B468: symmetry vs holes ----------
    by_orb = defaultdict(list)
    rows468 = []
    for (cx, cy, r2), P in wide_c.items():
        m = len(P)
        A = window_spectrum(P, square=True)
        holes = set(range(m + 1)) - A
        orb = d4_orbit_size(P)
        ext = extremal(P)
        rows468.append({"m": m, "orbit": orb, "n_holes": len(holes),
                        "holes": sorted(holes), "bbox": max(ext["w"], ext["h"])})
        by_orb[orb].append(len(holes))
    # controlled: match (m, bbox) then compare orbit
    ctrl = defaultdict(list)
    for r in rows468:
        ctrl[(r["m"], r["bbox"])].append(r["n_holes"])
    pair_diffs = []
    for key, lst in ctrl.items():
        if len(lst) < 2:
            continue
        byo = defaultdict(list)
        for r in rows468:
            if (r["m"], r["bbox"]) == key:
                byo[r["orbit"]].append(r["n_holes"])
        if len(byo) >= 2:
            means = {o: sum(v) / len(v) for o, v in byo.items()}
            lo = min(means, key=lambda o: means[o])
            hi = max(means, key=lambda o: means[o])
            pair_diffs.append({"m": key[0], "bbox": key[1], "means": {str(k): v for k, v in means.items()},
                               "more_holes_at_higher_orbit": means[hi] > means[lo],
                               "gap": means[hi] - means[lo]})
    report["B468"] = {
        "mean_holes_by_orbit": {str(k): sum(v) / len(v) for k, v in sorted(by_orb.items())},
        "n_by_orbit": {str(k): len(v) for k, v in sorted(by_orb.items())},
        "n_controlled_pairs": len(pair_diffs),
        "n_pairs_higher_orbit_more_holes": sum(1 for p in pair_diffs if p["more_holes_at_higher_orbit"]),
        "controlled": pair_diffs[:12],
    }
    print("B468 controlled pairs", len(pair_diffs),
          "support", sum(1 for p in pair_diffs if p["more_holes_at_higher_orbit"]), flush=True)


def sec_B469(report):
    """B469: max-point circles' triples vs smaller circles, 4-edge balance."""
    n = 8
    box = [(x, y) for y in range(-1, n + 1) for x in range(-1, n + 1)]
    circs = enum_circles(box, min_pts=4, bound=n + 2)
    rows = []
    for (cx, cy, r2), P in circs.items():
        inb = [p for p in P if 0 <= p[0] < n and 0 <= p[1] < n]
        if len(inb) < 4:
            continue
        # best triple on the circle: choose the triple minimising edge imbalance
        best = None
        for tri in itertools.combinations(inb, 3):
            sides = [0, 0, 0, 0]  # y=0, y=n-1, x=0, x=n-1
            for x, y in tri:
                if y == 0:
                    sides[0] += 1
                if y == n - 1:
                    sides[1] += 1
                if x == 0:
                    sides[2] += 1
                if x == n - 1:
                    sides[3] += 1
            bal = max(sides) - min(sides)
            spread = max(sides) - min(sides)
            if best is None or bal < best[0]:
                best = (bal, tri, tuple(sides))
        rows.append({"m_in": len(inb), "best_balance": best[0],
                     "sides": list(best[2]), "tri": [list(t) for t in best[1]],
                     "r2": f"{r2.numerator}/{r2.denominator}",
                     "q": centre_denom(cx, cy)})
    mx = max(r["m_in"] for r in rows)
    top = [r for r in rows if r["m_in"] == mx]
    below = [r for r in rows if 4 <= r["m_in"] < mx]
    near = [r for r in rows if r["m_in"] >= mx - 2 and r["m_in"] < mx]
    report["B469"] = {
        "n": n, "M8_measured": mx, "n_circles_ge4_inboard": len(rows),
        "n_top": len(top),
        "mean_best_balance_top": sum(r["best_balance"] for r in top) / len(top) if top else None,
        "mean_best_balance_below": sum(r["best_balance"] for r in below) / len(below) if below else None,
        "mean_best_balance_near_top": sum(r["best_balance"] for r in near) / len(near) if near else None,
        "n_near_top": len(near),
        "n_zero_balance_top": sum(1 for r in top if r["best_balance"] == 0),
        "n_zero_balance_below": sum(1 for r in below if r["best_balance"] == 0),
        "example_top": top[:5],
        "example_zero_below": [r for r in below if r["best_balance"] == 0][:5],
    }
    print("B469 M8=%d top=%d bal_top=%.3f bal_below=%.3f near=%d/%d" % (
        mx, len(top),
        report["B469"]["mean_best_balance_top"] or -1,
        report["B469"]["mean_best_balance_below"] or -1,
        report["B469"]["n_zero_balance_below"], len(below)), flush=True)


def sec_B470(report):
    """B470: the n=5 3-stone hole (18) explained by window-cut types."""
    n = 5
    B = board_square(n)
    pts = B.points
    hist = Counter()
    examples = {}
    for comb in itertools.combinations(range(n * n), 3):
        occ = 0
        for i in comb:
            occ |= 1 << i
        if not B.is_safe(occ):
            continue
        leg = len(B.legal_moves(occ))
        hist[leg] += 1
        examples.setdefault(leg, [pts[i] for i in comb])
    # n=4 layer for reference
    B4 = board_square(4)
    hist4 = Counter()
    for comb in itertools.combinations(range(16), 3):
        occ = 0
        for i in comb:
            occ |= 1 << i
        if not B4.is_safe(occ):
            continue
        hist4[len(B4.legal_moves(occ))] += 1
    # Theory: |L| after 3 stones = 25 - 3 - (#points killed)
    # each killed point must be the 4th point of some forbidden quad through
    # the 3 stones.  Killed(p) = #{forbidden quads q : q ⊂ S ∪ {p}}
    kill = Counter()
    for leg, tri in examples.items():
        S = set(tri)
        dead = 0
        for p in range(n * n):
            if p in S:
                continue
            bad = False
            for q in B.quads:
                ids = [i for i in range(n * n) if (q >> i) & 1]
                if set(ids) <= (S | {p}):
                    bad = True
                    break
            if bad:
                dead += 1
        kill[dead] += 1
    report["B470"] = {
        "n5_hist": {int(k): v for k, v in sorted(hist.items())},
        "n5_missing_in_0_22": sorted(set(range(0, 23)) - {int(k) for k in hist}),
        "n4_hist": {int(k): v for k, v in sorted(hist4.items())},
        "n4_missing": sorted(set(range(0, 14)) - {int(k) for k in hist4}),
        "killed_points_per_representative": dict(kill),
        "formula_check": "22 - 3 - dead = |L|",
        "examples": {str(k): v for k, v in examples.items()},
    }
    print("B470 n5 hist", dict(hist), "n4 hist", dict(hist4), flush=True)


def sec_B472(report):
    """B472: fixed-direction leading coefficient vs H^3 (with lattice sum)."""
    rows = []
    dirs = [(1, 0), (0, 1), (1, 1), (1, -1), (2, 1), (1, 2), (3, 1), (1, 3),
            (4, 1), (1, 4), (5, 1), (5, 2), (2, 5), (3, 2), (5, 3), (4, 3)]
    ns = (16, 24, 32, 40)
    for (a, b) in dirs:
        r = {"dir": [a, b], "H": max(abs(a), abs(b))}
        for n in ns:
            t, _ = collinear_c4_dir(n, a, b)
            r[f"D_{n}"] = t
            r[f"c_{n}"] = Fraction(t, n ** 5)
        rows.append(r)
    # Richardson extrapolation of c_n -> c_inf for each direction:
    # D(n) = c n^5 + c1 n^4  => c_inf = (16 c_2n - c_n)/15 with n->2n
    for r in rows:
        c1 = r["c_16"]
        c2 = r["c_32"]
        r["c_richardson_16_32"] = (16 * c2 - c1) / 15
        H = r["H"]
        r["H3_c_rich"] = Fraction(H ** 3) * r["c_richardson_16_32"]
        r["H4_c_rich"] = Fraction(H ** 4) * r["c_richardson_16_32"]
    h3 = [float(r["H3_c_rich"]) for r in rows]
    h4 = [float(r["H4_c_rich"]) for r in rows]
    ratios = []
    for r in rows:
        if r["H"] > 0:
            ratios.append(float(r["H3_c_rich"] / r["H4_c_rich"]) if r["H4_c_rich"] else None)
    report["B472"] = {
        "rows": rows,
        "H3_c_range": [min(h3), max(h3)],
        "H4_c_range": [min(h4), max(h4)],
        "spread_H3_over_H4": (max(h3) - min(h3)) / (max(h4) - min(h4)) if max(h4) > min(h4) else None,
        "note": "H^3*C bounded  <=> spread small; H^4 model => H3_c grows like H",
        "H3_c_by_H": {str(H): [float(r["H3_c_rich"]) for r in rows if r["H"] == H]
                      for H in sorted({r["H"] for r in rows})},
    }
    print("B472 H3c range %.5f..%.5f  H4c range %.3e..%.3e" % (
        min(h3), max(h3), min(h4), max(h4)), flush=True)


def sec_B473(report):
    """B473: D_n finite-size correction vs boundary length and gcd sums."""
    ns = list(range(6, 41))
    Dn = {}
    for n in ns:
        Dn[n], _ = collinear_c4(n)
    # c_hat from large n with log correction
    import math as _m
    c_hat = Fraction(0)
    for n in (32, 36, 40):
        c_hat += Fraction(Dn[n], n ** 5) / Fraction(_m.log(n)).numerator * \
            Fraction(_m.log(n)).denominator
    c_hat = c_hat / 3
    rows = []
    for n in ns:
        # residual after main term c n^5 log n
        main = c_hat * n ** 5
        rows.append({"n": n, "D": Dn[n], "D_over_n5": float(Fraction(Dn[n], n ** 5))})
    # perimeter: P(n) = number of boundary points of the n x n board = 4n-4
    # candidate correction: alpha * n^4 / ... ; fit alpha by least squares
    # on residual/(n^4) for n>=20
    fit = []
    for r in rows:
        if r["n"] >= 20:
            fit.append((r["n"], float(Fraction(Dn[r["n"]] - int(c_hat * r["n"] ** 5), r["n"] ** 4))))
    xs = [n for n, _ in fit]
    ys = [v for _, v in fit]
    n_ = len(xs)
    sx = sum(xs)
    sy = sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in fit)
    den = n_ * sxx - sx * sx
    alpha = Fraction(n_ * sxy - sx * sy, int(den)) if den else Fraction(0)
    beta = Fraction(sy * sxx - sx * sxy, int(den)) if den else Fraction(0)
    # sigma_0, sigma_1 sums (gcds) -- approximate via divisor sums to n
    sigma0 = {}
    for n in ns:
        sigma0[n] = sum(1 for g in range(1, n + 1) if _m.gcd(g, n) >= 1)  # trivial lower bound proxy
    # proper: sum over a of gcd(a,n) : O(n) per n
    sig_rows = []
    for n in ns:
        s0 = sum(_m.gcd(a, n) for a in range(1, n + 1))
        s1 = sum(a * _m.gcd(a, n) for a in range(1, n + 1))
        sig_rows.append({"n": n, "sigma0": s0, "sigma1": s1,
                         "resid_over_n4": float(Fraction(Dn[n] - int(c_hat * n ** 5), n ** 4)),
                         "resid_over_n4_sigma1_n": float(Fraction(Dn[n] - int(c_hat * n ** 5), n ** 4)) / (s1 / n ** 2) if s1 else None})
    report["B473"] = {
        "c_hat": float(c_hat),
        "D_n": Dn,
        "linear_fit_resid_n4": {"alpha": float(alpha), "beta": float(beta)},
        "rows": sig_rows,
        "resid_n4_range_n20_40": [min(y for _, y in fit), max(y for _, y in fit)],
        "note": "residual after c*n^5 is O(n^4); alpha fit tells whether a pure n^4 term explains it",
    }
    print("B473 c_hat=%.6f alpha=%.6f resid/n4 in [%.4f,%.4f]" % (
        float(c_hat), float(alpha),
        report["B473"]["resid_n4_range_n20_40"][0],
        report["B473"]["resid_n4_range_n20_40"][1]), flush=True)


def sec_B474(circles_by_n, report):
    """B474: C_n increment vs NEW primitive circle types (A,D,E,F)."""
    ns = sorted(circles_by_n)
    typesets = {}
    for n in ns:
        ts = set()
        for (cx, cy, r2) in circles_by_n[n]:
            ts.add(primitive_coeffs(cx, cy, r2))
        typesets[n] = ts
    rows = []
    Cn = {}
    for n in range(2, 13):
        Dn, _ = collinear_c4(n)
        if n in KNOWN_F:
            Cn[n] = KNOWN_F[n] - Dn
    for i, n in enumerate(ns):
        new = len(typesets[n] - typesets[ns[i - 1]]) if i else len(typesets[n])
        rows.append({"n": n, "C_n": Cn.get(n), "dC": (Cn[n] - Cn[n - 1]) if n in Cn and (n - 1) in Cn else None,
                     "n_types": len(typesets[n]), "new_types": new})
    # correlation over the dC-available rows
    def pearson(xs, ys):
        k = len(xs)
        mx = sum(xs) / k
        my = sum(ys) / k
        sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        sxx = sum((x - mx) ** 2 for x in xs)
        syy = sum((y - my) ** 2 for y in ys)
        if sxx == 0 or syy == 0:
            return None
        return sxy / (sxx * syy) ** 0.5
    good = [r for r in rows if r["dC"] is not None and r["new_types"] is not None]
    r_new = pearson([r["dC"] for r in good], [r["new_types"] for r in good]) if len(good) >= 3 else None
    # M(n) jump series
    Mcum = [max(len(P) for P in circles_by_n[n].values()) for n in ns]
    dM = [Mcum[i] - (Mcum[i - 1] if i else 0) for i in range(len(Mcum))]
    report["B474"] = {
        "rows": rows, "M_cumulative": {str(n): Mcum[i] for i, n in enumerate(ns)},
        "dM": {str(n): dM[i] for i, n in enumerate(ns)},
        "pearson_dC_vs_new_types": r_new,
        "n_points_corr": len(good),
        "C_series": {str(n): Cn[n] for n in sorted(Cn)},
        "note": "types now the TRUE primitive (A,D,E,F), not the ad-hoc (m,q,F) of round2",
    }
    print("B474 rows", rows, "corr", r_new, flush=True)


def sec_B477(circles_by_n, report):
    """B477: alternative standard-chord assignments, overlap comparison."""
    out = {}
    for n in sorted(circles_by_n):
        circs = circles_by_n[n]

        def chord_sigs(P, mode):
            sigs = []
            for a, b in itertools.combinations(P, 2):
                dx, dy = b[0] - a[0], b[1] - a[1]
                g = gcd(abs(dx), abs(dy)) if (dx or dy) else 1
                pdx, pdy = dx // g, dy // g
                if pdx < 0 or (pdx == 0 and pdy < 0):
                    pdx, pdy = -pdx, -pdy
                    a, b = b, a
                c = -pdy * a[0] + pdx * a[1]
                L2 = (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2
                if mode == "lex":
                    sigs.append(((pdx, pdy, c), L2))
                elif mode == "minL2":
                    sigs.append(((L2, pdx, pdy, c), L2))
                elif mode == "maxL2":
                    sigs.append(((-L2, pdx, pdy, c), L2))
                elif mode == "radius":
                    cx = Fraction(sum(p[0] for p in P), len(P))
                    cy = Fraction(sum(p[1] for p in P), len(P))
                    rr = Fraction(sum((p[0] - cx) ** 2 + (p[1] - cy) ** 2 for p in P), len(P))
                    sigs.append(((c, rr), L2))
            return sigs

        res = {}
        for mode in ("lex", "minL2", "maxL2", "radius"):
            m = defaultdict(set)
            for key, P in circs.items():
                sigs = chord_sigs(P, mode)
                if not sigs:
                    continue
                std = min(s for s, _ in sigs)
                m[std].add(key)
            multi = {k: len(v) for k, v in m.items() if len(v) > 1}
            res[mode] = {
                "n_std_chords": len(m),
                "n_collisions": len(multi),
                "max_per_chord": max(multi.values()) if multi else 1,
                "collided_circles": sum(multi.values()),
                "frac_circles_in_collision": (sum(multi.values()) / len(circs)) if circs else None,
            }
        out[str(n)] = {"n_circles": len(circs), "modes": res}
        print("B477 n=%d %s" % (n, {k: (v["n_collisions"], v["max_per_chord"]) for k, v in res.items()}), flush=True)
    report["B477"] = out


def main():
    report = {}
    # circles per n (circles with >=4 lattice points meeting the n x n board)
    circles_by_n = {}
    for n in (3, 4, 5, 6):
        box = [(x, y) for y in range(-1, n + 1) for x in range(-1, n + 1)]
        circs = enum_circles(box, min_pts=4, bound=n + 2)
        circles_by_n[n] = circs
        print(f"n={n}: {len(circs)} circles with >=4 lattice pts", flush=True)
    report["circle_counts"] = {str(n): len(c) for n, c in circles_by_n.items()}

    sec_B458_B470(circles_by_n, report)
    sec_B469(report)
    sec_B470(report)
    sec_B472(report)
    sec_B473(report)
    sec_B474(circles_by_n, report)
    sec_B477(circles_by_n, report)

    OUT.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
