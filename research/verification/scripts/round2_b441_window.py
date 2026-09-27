#!/usr/bin/env python3
"""Fast window-cut probes only (B461/B463/B464/B465). No board searches."""
from __future__ import annotations

import json
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

OUT = Path(r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round2_b441.json")


def count_points(cx: Fraction, cy: Fraction, r2: Fraction, bound: int = 30):
    q = cx.denominator * cy.denominator
    from math import gcd

    q = cx.denominator * cy.denominator // gcd(cx.denominator, cy.denominator)
    px = cx.numerator * (q // cx.denominator)
    py = cy.numerator * (q // cy.denominator)
    n, d = r2.numerator, r2.denominator
    if (q * q * n) % d != 0:
        return []
    R2 = (q * q * n) // d
    pts = []
    umax = 0
    while (umax + 1) ** 2 <= R2:
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
            if (u + px) % q or (vv + py) % q:
                continue
            x = (u + px) // q
            y = (vv + py) // q
            if abs(x) <= bound and abs(y) <= bound:
                pts.append((x, y))
    return sorted(set(pts))


def window_spectrum(pts, extra=2):
    if not pts:
        return {0}
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    span = max(xmax - xmin, ymax - ymin) + 3
    A = set()
    for x0 in range(xmin - extra, xmax + extra):
        for y0 in range(ymin - extra, ymax + extra):
            for w in range(1, span + 1):
                c = sum(1 for x, y in pts if x0 <= x <= x0 + w - 1 and y0 <= y <= y0 + w - 1)
                A.add(c)
    return A


def rect_spectrum(pts):
    if not pts:
        return {0}
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    A = set()
    for x0 in range(xmin - 2, xmax + 2):
        for y0 in range(ymin - 2, ymax + 2):
            for w in range(1, xmax - xmin + 4):
                for h in range(1, ymax - ymin + 4):
                    c = sum(
                        1
                        for x, y in pts
                        if x0 <= x <= x0 + w - 1 and y0 <= y <= y0 + h - 1
                    )
                    A.add(c)
    return A


def extremes(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    return {
        "nL": sum(1 for x, y in pts if x == xmin),
        "nR": sum(1 for x, y in pts if x == xmax),
        "nB": sum(1 for x, y in pts if y == ymin),
        "nT": sum(1 for x, y in pts if y == ymax),
        "w": xmax - xmin + 1,
        "h": ymax - ymin + 1,
    }


def main():
    out = {}

    # ---- B461: r2=25/2, centre (1/2,1/2) ----
    P = count_points(Fraction(1, 2), Fraction(1, 2), Fraction(25, 2))
    A = window_spectrum(P)
    holes = sorted(set(range(len(P) + 1)) - A)
    out["B461"] = {
        "n_pts": len(P),
        "pts": P,
        "A": sorted(A),
        "holes": holes,
        "has_11": 11 in A,
        "ext": extremes(P),
    }
    # all translates (dx,dy in -3..3)
    U = set()
    for dx in range(-3, 4):
        for dy in range(-3, 4):
            Pt = [(x + dx, y + dy) for x, y in P]
            U |= window_spectrum(Pt)
    out["B461"]["A_union_translates"] = sorted(U)
    out["B461"]["holes_union"] = sorted(set(range(13)) - U)
    print("B461", len(P), "A", sorted(A), "holes", holes, flush=True)

    # other centres of same family: (3/2,1/2) etc. — same shape, same A
    # also r2=25/2 with centre (0,0)? no lattice pts. centre (1/2,3/2)?
    for cx, cy in [(Fraction(3, 2), Fraction(1, 2)), (Fraction(1, 2), Fraction(3, 2)),
                   (Fraction(-1, 2), Fraction(1, 2))]:
        P2 = count_points(cx, cy, Fraction(25, 2))
        A2 = window_spectrum(P2)
        out["B461"].setdefault("variants", []).append({
            "c": f"({cx},{cy})", "n": len(P2), "A": sorted(A2),
            "has_11": 11 in A2,
        })

    # ---- B463 / B465: a family of half-integer-centre circles ----
    # r2 = (a^2+b^2)/4 with a,b odd: r2 = (2k+1)^2+(2l+1)^2 / 4
    half_rows = []
    for a in range(1, 16, 2):
        for b in range(1, 16, 2):
            r2 = Fraction(a * a + b * b, 4)
            for cx, cy in [(Fraction(1, 2), Fraction(1, 2)), (Fraction(1, 2), Fraction(3, 2)),
                           (Fraction(3, 2), Fraction(1, 2))]:
                P = count_points(cx, cy, r2)
                m = len(P)
                if m < 5:
                    continue
                A = window_spectrum(P)
                ext = extremes(P)
                unique_ext = 1 in (ext["nL"], ext["nR"], ext["nB"], ext["nT"])
                half_rows.append({
                    "r2": f"{r2.numerator}/{r2.denominator}",
                    "m": m,
                    "A": sorted(A),
                    "holes": sorted(set(range(m + 1)) - A),
                    "has_m_minus_1": (m - 1) in A,
                    "unique_ext": unique_ext,
                    "ext": ext,
                })
    # dedup by (r2, m, A)
    seen = set()
    uniq = []
    for r in half_rows:
        key = (r["r2"], r["m"], tuple(r["A"]))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)
    n_half = len(uniq)
    n_miss = sum(1 for r in uniq if not r["has_m_minus_1"])
    agree = sum(1 for r in uniq if r["unique_ext"] == r["has_m_minus_1"])
    out["B463_B465"] = {
        "n_half_circles": n_half,
        "n_missing_m_minus_1": n_miss,
        "unique_ext_agreement": agree,
        "rows": uniq[:25],
    }
    print("B463/465", n_miss, "/", n_half, "agree", agree, "/", n_half, flush=True)

    # ---- B464: rect vs square spectra on those circles ----
    extras = []
    for r in uniq[:40]:
        # reconstruct pts from r2/centre? we lost pts — recompute one centre
        pass
    # recompute properly
    ex_count = 0
    ex_rows = []
    for a in range(1, 16, 2):
        for b in range(1, 16, 2):
            r2 = Fraction(a * a + b * b, 4)
            P = count_points(Fraction(1, 2), Fraction(1, 2), r2)
            m = len(P)
            if m < 5:
                continue
            A_sq = window_spectrum(P)
            A_re = rect_spectrum(P)
            extra = sorted(A_re - A_sq)
            if extra:
                ex_count += 1
                if len(ex_rows) < 8:
                    ex_rows.append({
                        "r2": f"{r2.numerator}/{r2.denominator}",
                        "m": m,
                        "A_sq": sorted(A_sq),
                        "A_re": sorted(A_re),
                        "extra": extra,
                    })
    out["B464"] = {"n_with_extra": ex_count, "examples": ex_rows}
    print("B464 extras", ex_count, flush=True)

    # ---- integer-centre circles (q=1) for comparison ----
    int_rows = []
    for N in (5, 10, 13, 17, 25, 26, 29, 34, 50, 65):
        P = count_points(Fraction(0), Fraction(0), Fraction(N))
        m = len(P)
        if m < 5:
            continue
        A = window_spectrum(P)
        int_rows.append({
            "N": N, "m": m, "A": sorted(A),
            "holes": sorted(set(range(m + 1)) - A),
            "has_m_minus_1": (m - 1) in A,
            "ext": extremes(P),
        })
    out["int_centre_rows"] = int_rows
    print("int rows", [(r["N"], r["m"], r["has_m_minus_1"]) for r in int_rows], flush=True)

    prev = json.loads(OUT.read_text()) if OUT.exists() else {}
    prev.setdefault("sections", {})
    for k, v in out.items():
        prev["sections"][k] = v
    prev["sections"]["window_fast"] = out
    OUT.write_text(json.dumps(prev, indent=2, default=str))
    print("saved", flush=True)


if __name__ == "__main__":
    main()
