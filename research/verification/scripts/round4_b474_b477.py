#!/usr/bin/env python3
"""Round4: B474 (C_n increment vs new primitive circle types) and
B477 (chord-type decomposition, uniqueness/overlap of the assignment).

Integer / rational arithmetic only. No floating point is used for any decision;
decimals appear only as `num/den` exact fractions.

B474:  enumerate every lattice circle carrying >=4 points of the n x n board,
       take its TRUE primitive coefficients (A,D,E,F) with gcd=1, and ask
       how many such types FIRST appear at size n, versus the increment of
       C_n (non-collinear concyclic 4-sets) and the jump of M(n).
B477:  assign to each 4-subset-of-a-circle (i.e. each concyclic 4-set) a
       "standard chord" -- the primitive direction of a pair, canonically
       signed -- under several assignment rules, and count collisions
       (how many distinct 4-sets share the same chord signature).
       The hypothesis asks for a decomposition with LESS duplication.
"""
from __future__ import annotations
import itertools
import json
import sys
from fractions import Fraction
from math import gcd
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "round4_b474_b477.json"

# Exact F_n = number of forbidden 4-sets (concyclic OR collinear) on the n x n board.
# Source: research/verification/PROTOCOL.md line 20 (README), n=2..9.
# C_n (non-collinear concyclic 4-sets) is then C_n = F_n - D_n, D_n from
# collinear_c4() below (itself validated in round4-collinear-asymptotic.md §8).
KNOWN_F = {
    2: 1, 3: 14, 4: 194, 5: 826, 6: 2491, 7: 6364, 8: 14564, 9: 29152,
}


def det3(a, b, c):
    return (a[0] * (b[1] * c[2] - b[2] * c[1])
            - a[1] * (b[0] * c[2] - b[2] * c[0])
            + a[2] * (b[0] * c[1] - b[1] * c[0]))


def circumcircle(p, q, r):
    """(cx, cy, r2) as exact Fractions, or None if the three points are collinear.

    Solves the linear system
        2*dx_i*cx + 2*dy_i*cy = s_i - s_1        (i = 2, 3),
    where (dx_i, dy_i) = P_i - P_1 and s = x^2 + y^2, by Cramer's rule.
    det = 4*(dx2*dy3 - dy2*dx3) is 0 exactly on collinear triples.
    """
    (x1, y1), (x2, y2), (x3, y3) = p, q, r
    dx2, dy2 = x2 - x1, y2 - y1
    dx3, dy3 = x3 - x1, y3 - y1
    s1 = x1 * x1 + y1 * y1
    ds2 = (x2 * x2 + y2 * y2) - s1
    ds3 = (x3 * x3 + y3 * y3) - s1
    det = 4 * (dx2 * dy3 - dy2 * dx3)
    if det == 0:
        return None
    cx = Fraction(2 * (ds2 * dy3 - dy2 * ds3), det)
    cy = Fraction(2 * (dx2 * ds3 - ds2 * dx3), det)
    r2 = (cx - x1) ** 2 + (cy - y1) ** 2
    return (cx, cy, r2)


def centre_denom(cx: Fraction, cy: Fraction) -> int:
    from math import lcm
    return lcm(Fraction(2 * cx).denominator, Fraction(2 * cy).denominator)


def primitive_coeffs(cx: Fraction, cy: Fraction, r2: Fraction):
    """A(x^2+y^2) + Dx + Ey + F = 0, A>0, gcd(A,D,E,F)=1 -- the TRUE type."""
    from math import lcm
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


def collinear_c4(n):
    """Exact D_n via the primitive-direction formula of round4-collinear-asymptotic.md:
       D_n = 2*sum_H phi(H) * sum_{t>=3} C(t-1,2) (n-Ht)(2n-Ht).
       Return (D_n, F_n) with F_n the all-4-set total; None when F unknown."""
    D = 0
    for H in range(1, max(1, n)):
        q = (n - 1) // H
        if q < 3:
            continue
        ph = totient(H)
        inner = 0
        for t in range(3, q + 1):
            c = (t - 1) * (t - 2) // 2
            inner += c * (n - H * t) * (2 * n - H * t)
        D += 2 * ph * inner
    return D, KNOWN_F.get(n)


def totient(m):
    r = m
    p = 2
    x = m
    while p * p <= x:
        if x % p == 0:
            while x % p == 0:
                x //= p
            r -= r // p
        p += 1
    if x > 1:
        r -= r // x
    return r


def circle_points(cx: Fraction, cy: Fraction, r2: Fraction, n):
    """All integer (x,y) in {0..n-1}^2 on the circle (cx,cy,r2).

    Exact integer arithmetic. q = lcm(den(cx), den(cy)) makes px=q*cx and
    py=q*cy integers; the circle equation becomes
        (q*x - px)^2 + (q*y - py)^2 = q^2 * r2,
    whose left side is an integer, so a non-integral q^2*r2 means no lattice
    point at all.
    """
    from math import lcm
    q = lcm(lcm(cx.denominator, cy.denominator), r2.denominator)
    px = cx.numerator * (q // cx.denominator)     # = q*cx
    py = cy.numerator * (q // cy.denominator)     # = q*cy
    num, den = r2.numerator, r2.denominator
    if (q * q * num) % den != 0:
        return []
    R2 = (q * q * num) // den
    out = []
    for x in range(n):
        dx = q * x - px
        s = R2 - dx * dx
        if s < 0:
            continue
        v = isqrt(s)
        if v * v != s:
            continue
        for cand in (v, -v):
            t = py + cand
            if t % q == 0:
                y = t // q
                if 0 <= y < n:
                    out.append((x, y))
    return sorted(set(out))


def isqrt(n):
    if n < 0:
        raise ValueError
    if n < 2:
        return n
    x = int(n ** 0.5)
    while x * x > n:
        x -= 1
    while (x + 1) * (x + 1) <= n:
        x += 1
    return x


def all_circles(n):
    """dict (cx,cy,r2) -> sorted tuple of board points, for circles with >=4 points."""
    pts = [(x, y) for x in range(n) for y in range(n)]
    circs = {}
    for tri in itertools.combinations(pts, 3):
        c = circumcircle(*tri)
        if c is None:
            continue
        P = circle_points(*c, n)
        if len(P) >= 4:
            circs[c] = tuple(P)
    return circs


# ---------------------------------------------------------------- B477 modes
def chord_sig(a, b):
    """Canonical primitive chord direction + line intercept, for a pair a != b."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    g = gcd(abs(dx), abs(dy))
    pdx, pdy = dx // g, dy // g
    if pdx < 0 or (pdx == 0 and pdy < 0):
        pdx, pdy = -pdx, -pdy
        a, b = b, a
    c = -pdy * a[0] + pdx * a[1]
    return (pdx, pdy, c)


def chord_modes(P):
    """Return {mode_name: signature} for the 4 points P."""
    pairs = list(itertools.combinations(P, 2))

    def glen(pr):
        return gcd(abs(pr[1][0] - pr[0][0]), abs(pr[1][1] - pr[0][1]))

    sigs = sorted(set(chord_sig(a, b) for a, b in pairs))
    out = {
        "lexmin": sigs[0],
        "lexmax": sigs[-1],
        "longest": chord_sig(*max(pairs, key=glen)),
        "shortest": chord_sig(*min(pairs, key=glen)),
    }
    # smallest primitive direction norm, then smallest |intercept|
    out["shortdir"] = min(
        (chord_sig(a, b) for a, b in pairs),
        key=lambda s: (s[0] * s[0] + s[1] * s[1], abs(s[2])))
    return out


def main():
    report = {"KNOWN_F": KNOWN_F}

    # ---------------- B474 ----------------
    ns = [3, 4, 5, 6, 7, 8, 9]

    # ---- SELF-CHECK: sum over circles of C(m,4) must equal C_n = F_n - D_n ----
    selfcheck = []
    for n in ns:
        circs = all_circles(n)
        Dn, F = collinear_c4(n)
        tot = sum(len(P) * (len(P) - 1) * (len(P) - 2) * (len(P) - 3) // 24
                  for P in circs.values())
        C_n = (F - Dn) if F is not None else None
        ok = (C_n is None) or (tot == C_n)
        selfcheck.append({"n": n, "sum_C_m4": tot, "C_n": C_n, "match": ok})
        print(f"SELFCHECK n={n} sum_C(m,4)={tot} C_n={C_n} match={ok}", flush=True)
        if not ok:
            raise SystemExit(f"SELF-CHECK FAILED at n={n}")

    report["selfcheck_sum_C_m4_equals_C_n"] = selfcheck

    typesets = {}
    M = {}
    n_circs = {}
    for n in ns:
        circs = all_circles(n)
        n_circs[n] = len(circs)
        M[n] = max(len(P) for P in circs.values())
        ts = set(primitive_coeffs(*c) for c in circs)
        typesets[n] = ts
        print(f"n={n} circles={len(circs)} M(n)={M[n]} distinct_primitive_types={len(ts)}",
              flush=True)

    Cn = {}
    for n in ns:
        Dn, F = collinear_c4(n)
        if F is not None:
            Cn[n] = F - Dn

    rows = []
    for i, n in enumerate(ns):
        prev = ns[i - 1] if i else None
        new = len(typesets[n] - typesets[prev]) if prev is not None else len(typesets[n])
        rows.append({
            "n": n,
            "C_n": Cn.get(n),
            "dC": (Cn[n] - Cn[n - 1]) if (n in Cn and (n - 1) in Cn) else None,
            "M": M[n],
            "dM": (M[n] - M[n - 1]) if n - 1 in M else None,
            "n_circles": n_circs[n],
            "n_types_cum": len(typesets[n]),
            "new_types": new,
        })
        print("B474", json.dumps(rows[-1]), flush=True)

    def pearson_num(xs, ys):
        """Return (Sxy, Sxx, Syy) as exact Fractions."""
        k = len(xs)
        if k < 3:
            return None
        mx = Fraction(sum(xs), k)
        my = Fraction(sum(ys), k)
        sxy = sum((Fraction(x) - mx) * (Fraction(y) - my) for x, y in zip(xs, ys))
        sxx = sum((Fraction(x) - mx) ** 2 for x in xs)
        syy = sum((Fraction(y) - my) ** 2 for y in ys)
        return sxy, sxx, syy

    good = [r for r in rows if r["dC"] is not None and r["new_types"] is not None]
    r_new = None
    got = pearson_num([r["dC"] for r in good], [r["new_types"] for r in good])
    if got and got[1] > 0 and got[2] > 0:
        sxy, sxx, syy = got
        r_new = {
            "sum_xy": str(sxy), "sum_xx": str(sxx), "sum_yy": str(syy),
            "approx": float(sxy) / ((float(sxx) * float(syy)) ** 0.5),
        }

    # Spearman-style rank correlation of dC vs new_types (more robust, n=7 points)
    def spearman(pairs):
        if len(pairs) < 3:
            return None
        def ranks(vals):
            order = sorted(range(len(vals)), key=lambda i: vals[i])
            r = [0] * len(vals)
            i = 0
            while i < len(order):
                j = i
                while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
                    j += 1
                avg = Fraction(i + j + 2, 2)
                for k2 in range(i, j + 1):
                    r[order[k2]] = avg
                i = j + 1
            return r
        rx = ranks([p[0] for p in pairs])
        ry = ranks([p[1] for p in pairs])
        k = len(rx)
        mx = sum(rx) / k
        my = sum(ry) / k
        sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
        sxx = sum((a - mx) ** 2 for a in rx)
        syy = sum((b - my) ** 2 for b in ry)
        if sxx == 0 or syy == 0:
            return None
        return sxy / (sxx * syy) ** 0.5

    sp_new = spearman([(r["dC"], r["new_types"]) for r in good]) if len(good) >= 3 else None
    pairs_M = [(r["dC"], r["dM"]) for r in good if r["dM"] is not None]
    sp_M = spearman(pairs_M) if len(pairs_M) >= 3 else None

    report["B474"] = {
        "claim": "the n->n+1 increment of C_n is better explained by the number of "
                 "NEWLY appearing primitive circle types (A,D,E,F) than by the jump "
                 "of the max point count M(n)",
        "rows": rows,
        "C_series": {str(n): Cn[n] for n in sorted(Cn)},
        "pearson_dC_vs_new_types": r_new,
        "spearman_dC_vs_new_types": sp_new,
        "spearman_dC_vs_dM": sp_M,
        "n_points_corr": len(good),
        "note": "circle TYPES are the true primitive (A,D,E,F) with gcd=1, not the "
                "ad-hoc (m,q,F) used in round2; the earlier count was an artefact.",
    }

    # ---------------- B477 ----------------
    b477 = {}
    for n in ns:
        circs = all_circles(n)
        stats = {}
        for mode in ("lexmin", "lexmax", "longest", "shortest", "shortdir"):
            chord_map = {}
            n_quads = 0
            for c, P in circs.items():
                for quad in itertools.combinations(P, 4):
                    n_quads += 1
                    s = chord_modes(quad)[mode]
                    chord_map.setdefault(s, set()).add(c)
            n_chords = len(chord_map)
            # duplication = how many distinct circles share one chord
            multi = {s: len(v) for s, v in chord_map.items() if len(v) > 1}
            counts = sorted(multi.values(), reverse=True)
            stats[mode] = {
                "n_quads": n_quads,
                "n_chords": n_chords,
                "n_collisions": len(multi),
                "max_circles_per_chord": counts[0] if counts else 1,
                "median_circles_per_chord": counts[len(counts) // 2] if counts else 1,
                "quads_per_chord_num": n_quads,
                "quads_per_chord_den": n_chords,
            }
        b477[str(n)] = {"n_circles": len(circs), "modes": stats}
        print(f"B477 n={n} " + json.dumps(
            {k: (v["n_chords"], v["n_collisions"], v["max_circles_per_chord"])
             for k, v in stats.items()}), flush=True)

    report["B477"] = {
        "claim": "decomposing circles by the primitive type of a chord gives a "
                 "formula with LESS duplication than decomposing by radius",
        "by_n": b477,
        "note": "a chord signature is the canonical primitive direction (pdx,pdy) "
                "of a pair plus the line intercept c. A collision = two different "
                "circles carrying the same standard chord, i.e. the decomposition "
                "is not a unique labelling.",
    }

    OUT.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str),
                   encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
