#!/usr/bin/env python3
"""B451-B470: rational-centre circles + square-window cut spectra.

Exact integer / Fraction arithmetic only. No floats in decisions.

Definitions
-----------
Circle: set of integer lattice points on a geometric circle with rational
centre (cx, cy) = (px/q, py/q) in lowest terms (common denominator q after
reduction of the pair) and squared radius r2 = num/den (Fraction).

q = centre denominator = lcm of the reduced denominators of cx, cy.

A(C) (window spectrum) = { |P(C) ∩ W| : W axis-parallel square window with
integer corner and integer side length >= 1 } where P(C) is the COMPLETE
lattice-point set of C (infinite-lattice, before board truncation).

Board n x n = points with 0 <= x,y <= n-1.
M(n) = max |P(C) ∩ board| over circles C (equivalently over all translates).
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from fractions import Fraction
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round2_b441.json"


def gcd(a, b):
    while b:
        a, b = b, a % b
    return abs(a)


def det3(r0, r1, r2) -> int:
    return (
        r0[0] * (r1[1] * r2[2] - r1[2] * r2[1])
        - r0[1] * (r1[0] * r2[2] - r1[2] * r2[0])
        + r0[2] * (r1[0] * r2[1] - r1[1] * r2[0])
    )


def circumcircle(p, q, r):
    """Exact circle through 3 non-collinear integer points.

    Returns (cx, cy, r2) as Fractions, or None if collinear.
    """
    (x1, y1), (x2, y2), (x3, y3) = p, q, r
    # standard: 2*det
    d = 2 * det3((x1, y1, 1), (x2, y2, 1), (x3, y3, 1))
    if d == 0:
        return None
    s1 = x1 * x1 + y1 * y1
    s2 = x2 * x2 + y2 * y2
    s3 = x3 * x3 + y3 * y3
    cx = det3((s1, y1, 1), (s2, y2, 1), (s3, y3, 1)) / d
    cy = det3((s1, x1, 1), (s2, x2, 1), (s3, x3, 1)) / d
    # careful with sign of cy
    cy = Fraction(det3((s1, x1, 1), (s2, x2, 1), (s3, x3, 1)), d)
    # r2 = |c-p|^2
    r2 = (cx - x1) ** 2 + (cy - y1) ** 2
    return (Fraction(cx), Fraction(cy), Fraction(r2))


def centre_denom(cx: Fraction, cy: Fraction) -> int:
    return cx.denominator * cy.denominator // gcd(cx.denominator, cy.denominator)


def count_points_on_circle(cx: Fraction, cy: Fraction, r2: Fraction,
                           bound: int) -> list[tuple[int, int]]:
    """All integer (x,y) with (x-cx)^2+(y-cy)^2 = r2 and |x|,|y| <= bound.

    Solved exactly: write cx=px/q, cy=py/q, r2=n/d. Multiply:
    (qx-px)^2 / q^2 + (qy-py)^2 / q^2 = n/d
    (qx-px)^2 + (qy-py)^2 = q^2 n / d
    Need d | q^2 n. Let R2 = q^2 * n / d (must be integer).
    Then u^2+v^2 = R2 with u = qx-px, v = qy-py, u ≡ -px (mod q), v ≡ -py (mod q).
    """
    q = centre_denom(cx, cy)
    # express cx = px/q, cy = py/q (may not be reduced individually)
    px = cx.numerator * (q // cx.denominator)
    py = cy.numerator * (q // cy.denominator)
    n, d = r2.numerator, r2.denominator
    if (q * q * n) % d != 0:
        return []
    R2 = (q * q * n) // d
    if R2 < 0:
        return []
    # enumerate u^2+v^2 = R2, |u|,|v| not too large
    pts = []
    # u from -sqrt to sqrt
    umax = 0
    while (umax + 1) * (umax + 1) <= R2:
        umax += 1
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
            # x = (u+px)/q must be integer
            if (u + px) % q != 0:
                continue
            if (vv + py) % q != 0:
                continue
            x = (u + px) // q
            y = (vv + py) // q
            if abs(x) <= bound and abs(y) <= bound:
                pts.append((x, y))
    return sorted(set(pts))


def count_infinite(cx: Fraction, cy: Fraction, r2: Fraction) -> int:
    """Number of lattice points on the circle, no board bound (use large bound)."""
    q = centre_denom(cx, cy)
    n, d = r2.numerator, r2.denominator
    if (q * q * n) % d != 0:
        return 0
    R2 = (q * q * n) // d
    if R2 < 0:
        return 0
    cnt = 0
    umax = 0
    while (umax + 1) * (umax + 1) <= R2:
        umax += 1
    px = cx.numerator * (q // cx.denominator)
    py = cy.numerator * (q // cy.denominator)
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
            if (u + px) % q != 0:
                continue
            if (vv + py) % q != 0:
                continue
            cnt += 1
    return cnt


def bbox(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def window_spectrum(pts: list[tuple[int, int]]) -> set[int]:
    """A(C) = counts |P ∩ W| over axis-parallel square windows W with
    integer corner (x0,y0) and integer side w>=1 (covers [x0,x0+w-1]x[y0,y0+w-1]).
    """
    if not pts:
        return {0}
    xmin, ymin, xmax, ymax = bbox(pts)
    span = max(xmax - xmin, ymax - ymin) + 3
    A = set()
    for x0 in range(xmin - 2, xmax + 2):
        for y0 in range(ymin - 2, ymax + 2):
            for w in range(1, span + 1):
                c = 0
                for x, y in pts:
                    if x0 <= x <= x0 + w - 1 and y0 <= y <= y0 + w - 1:
                        c += 1
                A.add(c)
    return A


def rect_spectrum(pts: list[tuple[int, int]]) -> set[int]:
    """Same but windows are axis-parallel rectangles (integer sides >=1)."""
    if not pts:
        return {0}
    xmin, ymin, xmax, ymax = bbox(pts)
    A = set()
    for x0 in range(xmin - 2, xmax + 2):
        for y0 in range(ymin - 2, ymax + 2):
            for w in range(1, xmax - xmin + 4):
                for h in range(1, ymax - ymin + 4):
                    c = 0
                    for x, y in pts:
                        if x0 <= x <= x0 + w - 1 and y0 <= y <= y0 + h - 1:
                            c += 1
                    A.add(c)
    return A


def extremal_counts(pts):
    """How many points attain min/max x and min/max y (4 directions)."""
    xmin, ymin, xmax, ymax = bbox(pts)
    n_left = sum(1 for x, y in pts if x == xmin)
    n_right = sum(1 for x, y in pts if x == xmax)
    n_bot = sum(1 for x, y in pts if y == ymin)
    n_top = sum(1 for x, y in pts if y == ymax)
    return {
        "n_left": n_left, "n_right": n_right,
        "n_bot": n_bot, "n_top": n_top,
        "bbox_w": xmax - xmin + 1, "bbox_h": ymax - ymin + 1,
    }


def factor_type(q: int) -> str:
    """2-adic part + classify odd primes."""
    if q <= 0:
        return "?"
    v2 = 0
    t = q
    while t % 2 == 0:
        t //= 2
        v2 += 1
    p1mod4 = []
    p3mod4 = []
    p = 3
    while p * p <= t:
        while t % p == 0:
            t //= p
            if p % 4 == 1:
                p1mod4.append(p)
            else:
                p3mod4.append(p)
        p += 2
    if t > 1:
        if t % 4 == 1:
            p1mod4.append(t)
        else:
            p3mod4.append(t)
    return f"2^{v2}*{'*'.join(map(str, sorted(p1mod4)))}*3mod4:{'*'.join(map(str, sorted(p3mod4)))}"


def enum_circles_from_triples(pts, max_keep=4):
    """Enumerate distinct circles through >=max_keep lattice points of pts."""
    circles = {}
    n = len(pts)
    for i, j, k in combinations(range(n), 3):
        c = circumcircle(pts[i], pts[j], pts[k])
        if c is None:
            continue
        cx, cy, r2 = c
        if r2 <= 0:
            continue
        key = (cx, cy, r2)
        if key in circles:
            continue
        on = count_infinite(cx, cy, r2)
        # sample actual points within a generous bound
        q = centre_denom(cx, cy)
        bound = 64
        P = count_points_on_circle(cx, cy, r2, bound)
        if len(P) >= max_keep:
            circles[key] = {"cx": cx, "cy": cy, "r2": r2, "pts": P, "n_inf": on,
                            "q": centre_denom(cx, cy)}
    return circles


def main():
    out = {}

    # ============================================================
    # B451: same r2, different centre denominators, both >=4 pts,
    #       different lattice-point counts
    # ============================================================
    # Search circles from triples in a box [-6,6]^2
    box = []
    for x in range(-6, 7):
        for y in range(-6, 7):
            box.append((x, y))
    circles = enum_circles_from_triples(box, max_keep=4)
    by_r2 = defaultdict(list)
    for key, c in circles.items():
        by_r2[c["r2"]].append(c)
    b451 = []
    for r2, lst in by_r2.items():
        qs = {c["q"] for c in lst}
        if len(qs) >= 2:
            counts = defaultdict(set)
            for c in lst:
                counts[c["q"]].add(c["n_inf"])
            # need two denominators each with >=4 points, different counts
            cand = {q: cs for q, cs in counts.items() if max(cs) >= 4}
            if len(cand) >= 2:
                vals = [max(cs) for cs in cand.values()]
                if len(set(vals)) >= 2:
                    b451.append({
                        "r2": f"{r2.numerator}/{r2.denominator}",
                        "by_q": {str(q): sorted(cs) for q, cs in sorted(cand.items())},
                    })
    out["B451"] = {
        "n_circles_ge4": len(circles),
        "n_r2_with_multi_q": len(b451),
        "examples": b451[:12],
    }
    print("B451", out["B451"]["n_circles_ge4"], out["B451"]["n_r2_with_multi_q"], flush=True)

    # ============================================================
    # B452: under same diameter (r2) bound, q>=3 best exceeds q=1 best
    # ============================================================
    # For r2 <= 40, compute max lattice points by centre-denominator class
    b452_rows = []
    for r2_bound_num, r2_bound_den in [(20, 1), (25, 1), (40, 1), (50, 1), (100, 1)]:
        best = defaultdict(int)  # class -> max points
        best_wit = {}
        for key, c in circles.items():
            if c["r2"] > Fraction(r2_bound_num, r2_bound_den):
                continue
            q = c["q"]
            cls = "q1" if q == 1 else ("q2" if q == 2 else f"q{q}")
            if c["n_inf"] > best[cls]:
                best[cls] = c["n_inf"]
                best_wit[cls] = {
                    "q": q,
                    "r2": f"{c['r2'].numerator}/{c['r2'].denominator}",
                    "cx": f"{c['cx'].numerator}/{c['cx'].denominator}",
                    "cy": f"{c['cy'].numerator}/{c['cy'].denominator}",
                    "n": c["n_inf"],
                }
        # also brute-force q=1 and q=2 directly via representation counts
        # q=1: centre (0,0) (or any integer), r2 = N integer, pts = r2(N)
        def r2_repr(N):
            if N <= 0:
                return 0
            c = 0
            a = 0
            while a * a <= N:
                b2 = N - a * a
                b = 0
                while b * b < b2:
                    b += 1
                if b * b == b2:
                    # count signed ordered
                    if a == 0 and b == 0:
                        c += 1
                    elif a == 0 or b == 0:
                        c += 2
                    else:
                        c += 4
                a += 1
            return c

        best_q1_direct = 0
        best_q2_direct = 0
        for N in range(1, r2_bound_num + 1):
            best_q1_direct = max(best_q1_direct, r2_repr(N))
            # q=2 half-integer centre: (2x-1)^2+(2y-1)^2 = 4*r2 = N4
            # N4 = a^2+b^2 with a,b odd
            for N4 in range(4, 4 * r2_bound_num + 1):
                if N4 % 4 != 0:
                    continue
                # count odd representations
                cnt = 0
                a = 1
                while a * a <= N4:
                    b2 = N4 - a * a
                    b = 1
                    while b * b < b2:
                        b += 2
                    if b * b == b2 and a % 2 == 1 and b % 2 == 1:
                        if a == b:
                            cnt += 4  # (±a,±b) and (±b,±a) with a=b: 4 sign combos? (±a,±a)=4
                        elif a == 0 or b == 0:
                            cnt += 2
                        else:
                            cnt += 8  # signs and swap
                    a += 2
                best_q2_direct = max(best_q2_direct, cnt)
        b452_rows.append({
            "r2_bound": r2_bound_num,
            "best_from_triples": {k: v for k, v in sorted(best.items())},
            "best_wit": best_wit,
            "best_q1_direct": best_q1_direct,
            "best_q2_direct": best_q2_direct,
            "q3_or_more_best": max((v for k, v in best.items() if k not in ("q1", "q2")), default=0),
        })
        print("B452", r2_bound_num, dict(best), "q1d", best_q1_direct, "q2d", best_q2_direct, flush=True)
    out["B452"] = {"rows": b452_rows}

    # ============================================================
    # B453: factor type of q organises lattice-point upper bounds
    # ============================================================
    b453 = []
    by_q = defaultdict(list)
    for key, c in circles.items():
        by_q[c["q"]].append(c["n_inf"])
    for q in sorted(by_q):
        vals = by_q[q]
        b453.append({
            "q": q,
            "factor_type": factor_type(q),
            "max_pts": max(vals),
            "n_circles": len(vals),
        })
    out["B453"] = {"by_q": b453}
    print("B453", b453, flush=True)

    # ============================================================
    # B454: q=2^a family has smaller minimal containing board than
    #       odd q>=3 for the same lattice-point count m
    # ============================================================
    # For each m, min bbox width among circles with n_inf == m, split by q type
    min_w = {}  # (m, class) -> min width
    for key, c in circles.items():
        P = c["pts"]
        if not P:
            continue
        m = c["n_inf"]
        if m < 4:
            continue
        ext = extremal_counts(P)
        w = max(ext["bbox_w"], ext["bbox_h"])
        q = c["q"]
        cls = "q2pow" if q >= 2 and (q & (q - 1)) == 0 else ("odd" if q % 2 == 1 else "mixed")
        key2 = (m, cls)
        if key2 not in min_w or w < min_w[key2]:
            min_w[key2] = w
    b454 = []
    for m in sorted({k[0] for k in min_w}):
        row = {"m": m}
        for cls in ("q2pow", "odd", "mixed"):
            row[cls] = min_w.get((m, cls))
        b454.append(row)
    out["B454"] = {"min_bbox_by_m": b454}
    print("B454", b454, flush=True)

    # ============================================================
    # B455: q>=3 multi-point circles as residue-class selection of
    #       two-square representations
    # ============================================================
    # For circles with q>=3 and n_inf>=4, look at R2 = q^2 * r2 (integer)
    # and the residue of u= qx-px modulo q that actually realizes points.
    b455 = []
    for key, c in circles.items():
        q = c["q"]
        if q < 3 or c["n_inf"] < 4:
            continue
        cx, cy, r2 = c["cx"], c["cy"], c["r2"]
        n, d = r2.numerator, r2.denominator
        if (q * q * n) % d != 0:
            continue
        R2 = (q * q * n) // d
        px = cx.numerator * (q // cx.denominator)
        py = cy.numerator * (q // cy.denominator)
        # residues (u mod q, v mod q) of realized points
        residues = set()
        for x, y in c["pts"]:
            u = q * x - px
            v = q * y - py
            residues.add((u % q, v % q))
        b455.append({
            "q": q,
            "r2": f"{r2.numerator}/{r2.denominator}",
            "R2": R2,
            "n_inf": c["n_inf"],
            "n_residues": len(residues),
            "q2": q * q,
            "frac_residues": f"{len(residues)}/{q*q}",
        })
    out["B455"] = {"n_q3_circles": len(b455), "rows": b455[:20]}
    print("B455", len(b455), flush=True)

    # ============================================================
    # B456: fixed q, best count not monotone in r2 alone
    # ============================================================
    # For each q, look at (r2, n_inf) pairs: is max-so-far achievable only
    # at isolated r2 with different arithmetic type?
    by_q_r2 = defaultdict(list)
    for key, c in circles.items():
        by_q_r2[c["q"]].append((c["r2"], c["n_inf"]))
    b456 = []
    for q, lst in sorted(by_q_r2.items()):
        lst = sorted(set(lst))
        # record r2 where n_inf reaches a new max
        best = 0
        jumps = []
        for r2, n in lst:
            if n > best:
                best = n
                jumps.append({"r2": f"{r2.numerator}/{r2.denominator}", "n": n})
        # check if there is a jump at larger r2 that is NOT explained by
        # simply multiplying an earlier circle (r2 scales by square)
        # crude: jumps count
        b456.append({"q": q, "n_jumps": len(jumps), "jumps": jumps[:8], "best": best})
    out["B456"] = {"by_q": b456}
    print("B456", b456, flush=True)

    # ============================================================
    # B457: q>=3 circles change count more easily under window translation
    # ============================================================
    # For each circle, |A(C)| (number of distinct window counts) grouped by q class
    b457_rows = []
    for key, c in circles.items():
        P = c["pts"]
        if len(P) < 4:
            continue
        A = window_spectrum(P)
        q = c["q"]
        cls = "q1" if q == 1 else ("q2" if q == 2 else "q3+")
        b457_rows.append({
            "q": q,
            "cls": cls,
            "n_pts": len(P),
            "A": sorted(A),
            "holes": sorted(set(range(len(P) + 1)) - A),
        })
    by_cls = defaultdict(list)
    for r in b457_rows:
        by_cls[r["cls"]].append(len(r["A"]))
    out["B457"] = {
        "mean_|A|_by_cls": {k: sum(v) / len(v) for k, v in by_cls.items()},
        "n_by_cls": {k: len(v) for k, v in by_cls.items()},
        "rows_sample": b457_rows[:15],
    }
    print("B457", out["B457"]["mean_|A|_by_cls"], flush=True)

    # ============================================================
    # B458: first occurrence size determined by primitive circle
    #       equation coefficients
    # ============================================================
    # Circle: A(x^2+y^2) + Dx + Ey + F = 0 with integer A,D,E,F, gcd=1, A>0.
    # Centre denom divides 2A. First board size ~ bbox of the point set.
    b458 = []
    for key, c in list(circles.items())[:200]:
        cx, cy, r2 = c["cx"], c["cy"], c["r2"]
        # clear denominators: use A = lcm
        q = centre_denom(cx, cy)
        # equation: (x-cx)^2+(y-cy)^2 = r2
        # x^2+y^2 -2cx x -2cy y + cx^2+cy^2-r2 = 0
        # multiply by L = lcm(1, den(2cx), den(2cy), den(r2))
        from math import lcm as _lcm

        dens = [1, Fraction(2 * cx).denominator, Fraction(2 * cy).denominator, r2.denominator]
        L = 1
        for d in dens:
            L = _lcm(L, d)
        A = L
        D = int(-2 * cx * L)
        E = int(-2 * cy * L)
        F = int((cx * cx + cy * cy - r2) * L)
        g = gcd(gcd(gcd(abs(A), abs(D)), abs(E)), abs(F))
        if g:
            A, D, E, F = A // g, D // g, E // g, F // g
        P = c["pts"]
        ext = extremal_counts(P) if P else {}
        b458.append({
            "A": A, "D": D, "E": E, "F": F,
            "q": c["q"],
            "n_inf": c["n_inf"],
            "bbox_w": ext.get("bbox_w"),
            "bbox_h": ext.get("bbox_h"),
        })
    out["B458"] = {"sample": b458[:40], "n": len(b458)}
    print("B458", len(b458), flush=True)

    # ============================================================
    # B459 / B460: game-level effects of q>=3 quads
    # ============================================================
    # Classify forbidden quads of n=5 by centre denominator of their circle
    # (or 'collinear'). Then compare P/N flip counts under removal of
    # quads from q>=3 vs q<=2 circles.  This is a sample probe.
    n5 = 5
    pts5 = [(x, y) for y in range(n5) for x in range(n5)]

    def det4(p0, p1, p2, p3):
        (x1, y1), (x2, y2), (x3, y3), (x4, y4) = p0, p1, p2, p3
        rows = [
            (x1 * x1 + y1 * y1, x1, y1, 1),
            (x2 * x2 + y2 * y2, x2, y2, 1),
            (x3 * x3 + y3 * y3, x3, y3, 1),
            (x4 * x4 + y4 * y4, x4, y4, 1),
        ]

        def det(rws):
            if len(rws) == 1:
                return rws[0][0]
            s = 0
            for j in range(len(rws[0])):
                minor = [r[:j] + r[j + 1 :] for r in rws[1:]]
                s += ((-1) ** j) * rws[0][j] * det(minor)
            return s

        return det(rows)

    quads5 = []
    for comb in combinations(range(25), 4):
        if det4(pts5[comb[0]], pts5[comb[1]], pts5[comb[2]], pts5[comb[3]]) == 0:
            m = 0
            for i in comb:
                m |= 1 << i
            quads5.append(m)
    # classify
    hist_q = defaultdict(int)
    coll = 0
    for qm in quads5:
        ids = [i for i in range(25) if (qm >> i) & 1]
        ps = [pts5[i] for i in ids]
        # collinear?
        def col(a, b, c):
            return (b[0] - a[0]) * (c[1] - a[1]) == (b[1] - a[1]) * (c[0] - a[0])

        if col(ps[0], ps[1], ps[2]) and col(ps[0], ps[1], ps[3]):
            coll += 1
            hist_q["collinear"] += 1
        else:
            cc = circumcircle(ps[0], ps[1], ps[2])
            if cc is None:
                hist_q["none"] += 1
            else:
                q = centre_denom(cc[0], cc[1])
                hist_q[f"q{q}"] += 1
    out["B459_B460"] = {
        "n_quads_n5": len(quads5),
        "hist": dict(hist_q),
        "note": "q>=3 quads exist; game-level P/N flip probe not run (needs full Grundy).",
    }
    print("B459/460 hist", dict(hist_q), flush=True)

    # ============================================================
    # B461: r2=25/2 12-pt circle: square window cannot leave 11
    # ============================================================
    # centre (1/2,1/2) type: (2x-1)^2+(2y-1)^2 = 50
    # solutions u^2+v^2=50, u,v odd: (1,7),(5,5),(7,1) and signs
    def circle_pts_half(cxf, cyf, r2f, bound=20):
        cx, cy, r2 = Fraction(cxf), Fraction(cyf), Fraction(r2f)
        return count_points_on_circle(cx, cy, r2, bound)

    P25 = circle_pts_half("1/2", "1/2", "25/2")
    A25 = window_spectrum(P25)
    holes25 = sorted(set(range(len(P25) + 1)) - A25)
    out["B461"] = {
        "n_pts": len(P25),
        "pts": P25,
        "A": sorted(A25),
        "holes": holes25,
        "has_11": 11 in A25,
        "ext": extremal_counts(P25),
    }
    print("B461", len(P25), sorted(A25), "holes", holes25, flush=True)

    # also test all translates of the 12-pt circle (same shape)
    A25_union = set()
    for dx in range(-3, 4):
        for dy in range(-3, 4):
            P = [(x + dx, y + dy) for x, y in P25]
            A25_union |= window_spectrum(P)
    out["B461"]["A_union_over_translates"] = sorted(A25_union)
    out["B461"]["holes_union"] = sorted(set(range(13)) - A25_union)
    print("B461 union", sorted(A25_union), flush=True)

    # ============================================================
    # B462: 11x11 first square board carrying an 11-point circle
    # ============================================================
    # Check: does any circle have >=11 lattice points inside a 10x10 board?
    # and is there one inside 11x11?
    def max_pts_in_board(n):
        best = 0
        wit = None
        # enumerate circles via triples inside a slightly larger box
        boxn = []
        for x in range(-2, n + 3):
            for y in range(-2, n + 3):
                boxn.append((x, y))
        seen = {}
        for i, j, k in combinations(range(len(boxn)), 3):
            c = circumcircle(boxn[i], boxn[j], boxn[k])
            if c is None:
                continue
            cx, cy, r2 = c
            if r2 <= 0:
                continue
            key = (cx, cy, r2)
            if key in seen:
                continue
            P = count_points_on_circle(cx, cy, r2, n + 4)
            inb = [p for p in P if 0 <= p[0] < n and 0 <= p[1] < n]
            seen[key] = len(inb)
            if len(inb) > best:
                best = len(inb)
                wit = (cx, cy, r2, inb)
        return best, wit, len(seen)

    # n=10,11 full triple enum is C(12*12,3)~ 10^5 for n=10 ambient 14x14=196 pts
    # C(196,3) = 1.2e6 — acceptable
    b462 = {}
    for nn in (9, 10, 11):
        best, wit, nc = max_pts_in_board(nn)
        b462[nn] = {
            "M": best,
            "n_circles_checked": nc,
            "wit_r2": f"{wit[2].numerator}/{wit[2].denominator}" if wit else None,
            "wit_c": f"({wit[0]},{wit[1]})" if wit else None,
            "wit_n": len(wit[3]) if wit else None,
        }
        print("B462", nn, best, flush=True)
    out["B462"] = b462

    # ============================================================
    # B463: losing exactly 1 point characterised by extremal multiplicity
    # ============================================================
    b463_rows = []
    for key, c in circles.items():
        P = c["pts"]
        m = len(P)
        if m < 5:
            continue
        A = window_spectrum(P)
        can_m_minus_1 = (m - 1) in A
        ext = extremal_counts(P)
        b463_rows.append({
            "m": m,
            "can_m_minus_1": can_m_minus_1,
            **ext,
        })
    # summary: among circles with m>=5, relation between min-extremal and can_m-1
    agree = 0
    total = 0
    for r in b463_rows:
        # prediction: can_m-1 iff sum of (extremal counts) has some point
        # that is the unique extremal in at least one direction?
        unique_ext = (
            r["n_left"] == 1 or r["n_right"] == 1 or r["n_bot"] == 1 or r["n_top"] == 1
        )
        total += 1
        if unique_ext == r["can_m_minus_1"]:
            agree += 1
    out["B463"] = {
        "n_circles_m_ge5": total,
        "agreement_unique_extremal": agree,
        "rows": b463_rows[:30],
    }
    print("B463", agree, "/", total, flush=True)

    # ============================================================
    # B464: rectangular window realises counts square window does not
    # ============================================================
    b464 = []
    for key, c in list(circles.items())[:80]:
        P = c["pts"]
        if len(P) < 5:
            continue
        A_sq = window_spectrum(P)
        A_re = rect_spectrum(P)
        extra = sorted(A_re - A_sq)
        if extra:
            b464.append({
                "n_pts": len(P),
                "q": c["q"],
                "r2": f"{c['r2'].numerator}/{c['r2'].denominator}",
                "A_sq": sorted(A_sq),
                "A_re": sorted(A_re),
                "extra": extra,
            })
    out["B464"] = {"n_examples": len(b464), "examples": b464[:10]}
    print("B464", len(b464), flush=True)

    # ============================================================
    # B465: q=2 symmetric full circles miss m-1
    # ============================================================
    # centres with BOTH coordinates true half-integers, n_inf = m
    b465_rows = []
    for key, c in circles.items():
        cx, cy = c["cx"], c["cy"]
        if cx.denominator != 2 or cy.denominator != 2:
            continue
        if cx.numerator % 2 == 0 or cy.numerator % 2 == 0:
            continue  # want true half-integer (odd/2)
        m = c["n_inf"]
        if m < 5:
            continue
        P = c["pts"]
        A = window_spectrum(P)
        b465_rows.append({
            "m": m,
            "has_m_minus_1": (m - 1) in A,
            "A": sorted(A),
            "holes": sorted(set(range(m + 1)) - A),
            "r2": f"{c['r2'].numerator}/{c['r2'].denominator}",
        })
    n_half = len(b465_rows)
    n_miss = sum(1 for r in b465_rows if not r["has_m_minus_1"])
    out["B465"] = {
        "n_halfint_circles_m_ge5": n_half,
        "n_missing_m_minus_1": n_miss,
        "rows": b465_rows[:20],
    }
    print("B465", n_miss, "/", n_half, flush=True)

    # ============================================================
    # B466: M(n) increases twice in a row from same family cut improvement
    # ============================================================
    # Use known F-K M(n) table (from findings) for n=2..31
    # and check whether two consecutive increases come from same N.
    M_table = {
        2: 1, 3: 1, 4: 4, 5: 5, 6: 8, 7: 8, 8: 12, 9: 12, 10: 12,
        11: 12, 12: 16, 13: 16, 14: 16, 15: 16, 16: 16, 17: 16, 18: 16,
        19: 16, 20: 16, 21: 16, 22: 16, 23: 16, 24: 16, 25: 20, 26: 24,
        27: 24, 28: 24, 29: 24, 30: 24, 31: 24,
    }
    # witness N from findings (approximate; n=25->650, n=26->650)
    witness_N = {
        8: "25/2", 25: "650", 26: "650",
    }
    jumps = []
    for n in range(3, 32):
        if M_table[n] > M_table[n - 1]:
            jumps.append({"n": n, "M_prev": M_table[n - 1], "M": M_table[n],
                          "witness": witness_N.get(n)})
    consecutive = []
    for i in range(len(jumps) - 1):
        if jumps[i + 1]["n"] == jumps[i]["n"] + 1:
            consecutive.append((jumps[i], jumps[i + 1]))
    out["B466"] = {
        "jumps": jumps,
        "consecutive_jump_pairs": consecutive,
        "M_table_used": M_table,
    }
    print("B466 jumps", jumps, flush=True)

    # ============================================================
    # B467: window spectrum determined by coordinate order of circle points
    # ============================================================
    # Compare A(C) of circles whose point sets have the same x-rank/y-rank
    # pattern (relative order), even if radii differ.
    def order_pattern(pts):
        xs = sorted({p[0] for p in pts})
        ys = sorted({p[1] for p in pts})
        xrank = {v: i for i, v in enumerate(xs)}
        yrank = {v: i for i, v in enumerate(ys)}
        return tuple(sorted((xrank[x], yrank[y]) for x, y in pts))

    by_pat = defaultdict(list)
    for key, c in circles.items():
        P = c["pts"]
        if len(P) < 5:
            continue
        pat = order_pattern(P)
        A = frozenset(window_spectrum(P))
        by_pat[pat].append((c["n_inf"], A))
    same_pat_diff_A = 0
    n_pat = 0
    for pat, lst in by_pat.items():
        if len(lst) < 2:
            continue
        n_pat += 1
        As = {A for _, A in lst}
        if len(As) > 1:
            same_pat_diff_A += 1
    out["B467"] = {
        "n_patterns_with_2plus": n_pat,
        "n_patterns_with_different_A": same_pat_diff_A,
        "note": "if 0, order pattern determines A on this sample",
    }
    print("B467", same_pat_diff_A, "/", n_pat, flush=True)

    # ============================================================
    # B468: higher symmetry -> more holes
    # ============================================================
    # symmetry score = size of D4 orbit of the point set (1..8)
    def d4_orbit_size(pts):
        s = set(pts)
        forms = []
        for x, y in pts:
            forms.extend([
                (x, y), (-x, y), (x, -y), (-x, -y),
                (y, x), (-y, x), (y, -x), (-y, -x),
            ])
        # orbit size = number of distinct sets
        seen = set()
        for flip in range(8):
            # apply permutation of the 8 dihedral transforms
            pass
        # simpler: generate all 8 images
        def transform(pts, k):
            outp = []
            for x, y in pts:
                if k == 0:
                    outp.append((x, y))
                elif k == 1:
                    outp.append((-x, y))
                elif k == 2:
                    outp.append((x, -y))
                elif k == 3:
                    outp.append((-x, -y))
                elif k == 4:
                    outp.append((y, x))
                elif k == 5:
                    outp.append((-y, x))
                elif k == 6:
                    outp.append((y, -x))
                elif k == 7:
                    outp.append((-y, -x))
            return tuple(sorted(outp))

        orb = {transform(pts, k) for k in range(8)}
        return len(orb)

    sym_rows = []
    for key, c in circles.items():
        P = c["pts"]
        m = len(P)
        if m < 5:
            continue
        A = window_spectrum(P)
        holes = sorted(set(range(m + 1)) - A)
        sym_rows.append({
            "m": m,
            "orbit": d4_orbit_size(P),
            "n_holes": len(holes),
            "holes": holes,
            "q": c["q"],
        })
    by_orb = defaultdict(list)
    for r in sym_rows:
        by_orb[r["orbit"]].append(r["n_holes"])
    out["B468"] = {
        "mean_holes_by_orbit": {k: sum(v) / len(v) for k, v in sorted(by_orb.items())},
        "n_by_orbit": {k: len(v) for k, v in sorted(by_orb.items())},
        "rows": sym_rows[:20],
    }
    print("B468", out["B468"]["mean_holes_by_orbit"], flush=True)

    # ============================================================
    # B469: max-point circle triples vs smaller circles covering 4 edges
    # ============================================================
    # For n=8 board, compare: circles with max in-board points vs slightly
    # smaller ones; count how many of the 4 board sides have a point of the
    # circle within distance 0 (on the side) — 'even cover'.
    n8 = 8
    box8 = [(x, y) for y in range(-2, n8 + 2) for x in range(-2, n8 + 2)]
    circ8 = enum_circles_from_triples(box8, max_keep=4)
    cover_rows = []
    for key, c in circ8.items():
        inb = [p for p in c["pts"] if 0 <= p[0] < n8 and 0 <= p[1] < n8]
        if len(inb) < 4:
            continue
        sides = [0, 0, 0, 0]  # top, bottom, left, right
        for x, y in inb:
            if y == 0:
                sides[0] += 1
            if y == n8 - 1:
                sides[1] += 1
            if x == 0:
                sides[2] += 1
            if x == n8 - 1:
                sides[3] += 1
        cover_rows.append({
            "n_in": len(inb),
            "sides": sides,
            "min_side": min(sides),
            "max_side": max(sides),
            "balance": max(sides) - min(sides),
        })
    if cover_rows:
        mx = max(r["n_in"] for r in cover_rows)
        top = [r for r in cover_rows if r["n_in"] == mx]
        below = [r for r in cover_rows if 4 <= r["n_in"] < mx]
        out["B469"] = {
            "M8": mx,
            "n_top": len(top),
            "mean_balance_top": sum(r["balance"] for r in top) / len(top),
            "mean_balance_below": (
                sum(r["balance"] for r in below) / len(below) if below else None
            ),
            "mean_min_side_top": sum(r["min_side"] for r in top) / len(top),
            "mean_min_side_below": (
                sum(r["min_side"] for r in below) / len(below) if below else None
            ),
        }
    else:
        out["B469"] = {"note": "no circles"}
    print("B469", out["B469"], flush=True)

    # ============================================================
    # B470: 3-stone legal-move holes explained by few window-cut types
    # ============================================================
    # For n=5, count legal-move numbers after every safe 3-stone set;
    # see if the missing values are a small set shared with window holes.
    # Sample: enumerate safe 3-sets on n=5 (cheap: C(25,3)=2300).
    n5 = 5
    pts5 = [(x, y) for y in range(n5) for x in range(n5)]
    quads5 = []
    for comb in combinations(range(25), 4):
        if det4(pts5[comb[0]], pts5[comb[1]], pts5[comb[2]], pts5[comb[3]]) == 0:
            m = 0
            for i in comb:
                m |= 1 << i
            quads5.append(m)
    move_counts = defaultdict(int)
    for comb in combinations(range(25), 3):
        occ = 0
        for i in comb:
            occ |= 1 << i
        # safe?
        ok = True
        for q in quads5:
            if (occ & q) == q:
                ok = False
                break
        if not ok:
            continue
        # legal moves
        leg = 0
        for p in range(25):
            if (occ >> p) & 1:
                continue
            nxt = occ | (1 << p)
            good = True
            for q in quads5:
                if (nxt & q) == q:
                    good = False
                    break
            if good:
                leg += 1
        move_counts[leg] += 1
    out["B470"] = {
        "n_safe_3sets": sum(move_counts.values()),
        "move_count_hist": {int(k): v for k, v in sorted(move_counts.items())},
        "missing": sorted(set(range(0, 23)) - {int(k) for k in move_counts}),
    }
    print("B470", out["B470"], flush=True)

    # merge
    prev = json.loads(OUT.read_text()) if OUT.exists() else {}
    prev.setdefault("sections", {})
    for k, v in out.items():
        prev["sections"][k] = v
    OUT.write_text(json.dumps(prev, indent=2, default=str))
    print("saved", OUT)


if __name__ == "__main__":
    main()
