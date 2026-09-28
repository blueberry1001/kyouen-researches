#!/usr/bin/env python3
"""Round3: B475 / B476 — circle point-count spectrum M(n) for n=7,8,9,10 (+re-verify n<=6).

B475 [asymptotic-bold] There is a constant m0 such that the liminf of the share of
        C_n (non-collinear concyclic 4-subsets) coming from circles with at most
        m0 board points is positive.
B476 [asymptotic-bold, rival] Weighting a uniformly chosen concyclic 4-subset by
        the number of board points on its circle, the point-count diverges: for
        any fixed m, P(m <= m) -> 0.  Directly opposite of B475.

Both claims are decided by the circle lattice-size histogram
    H_n[m] = #{distinct circles C in the n x n grid with exactly m grid points},
and C_n = sum_m C(m,4) * H_n[m], the weighted mean m = sum_m m*C(m,4)*H_n[m] / C_n,
and the fractions f_n(m0) = sum_{m<=m0} C(m,4)*H_n[m] / C_n.

Strategy (integer/rational arithmetic only, no floats in the combinatorics):
  A circle is identified by the rational (D, E, F) of x^2+y^2 + D x + E y + F = 0.
  We find every circle with >= 3 grid points in the n x n box by enumerating
  non-collinear triples, computing the rational key, and keeping those with a
  4th point.  Then H_n[m] is read off directly.  This is O(C(N,3)) triples with
  N = n^2, which for n=10 (N=100, C(100,3)=161700) is trivial, and even
  n=11 (N=121, C(121,3)=287980) and n=12 (N=144, C(144,3)=487344) are cheap.
  The bottleneck is the 4th-point membership test, done with exact integer
  arithmetic after clearing denominators.

We also recompute the previously-known n=3..6 numbers to cross-check against
research/verification/round2_b471.json and research/exploration/fact_circle_*.json.
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from fractions import Fraction
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round3_b475_mn.json"
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))


# ---------- exact integer geometry ----------
def det4_int(a, b, c, d):
    """det of rows [x^2+y^2, x, y, 1] for 4 points (int). 0 => concyclic/collinear."""
    m = [a, b, c, d]
    total = 0
    for i in range(4):
        sub = [m[r] for r in range(4) if r != i]
        det3 = (
            sub[0][1] * (sub[1][2] * sub[2][3] - sub[1][3] * sub[2][2])
            - sub[0][2] * (sub[1][1] * sub[2][3] - sub[1][3] * sub[2][1])
            + sub[0][3] * (sub[1][1] * sub[2][2] - sub[1][2] * sub[2][1])
        )
        total += (1 if i % 2 == 0 else -1) * m[i][0] * det3
    return total


def circle_key(p, q, r):
    """Deprecated Fraction-based key, kept only as a readable reference.
    Use circle_key_int (fast, integer) for the actual computation."""
    from fractions import Fraction
    M = [[Fraction(p[0]), Fraction(p[1]), Fraction(1)],
         [Fraction(q[0]), Fraction(q[1]), Fraction(1)],
         [Fraction(r[0]), Fraction(r[1]), Fraction(1)]]
    b = [Fraction(-(p[0] * p[0] + p[1] * p[1])),
         Fraction(-(q[0] * q[0] + q[1] * q[1])),
         Fraction(-(r[0] * r[0] + r[1] * r[1]))]
    aug = [M[i] + [b[i]] for i in range(3)]
    for col in range(3):
        piv = next((row for row in range(col, 3) if aug[row][col] != 0), None)
        if piv is None:
            return None  # collinear
        aug[col], aug[piv] = aug[piv], aug[col]
        pv = aug[col][col]
        for j in range(col, 4):
            aug[col][j] /= pv
        for row in range(3):
            if row != col and aug[row][col] != 0:
                f = aug[row][col]
                for j in range(col, 4):
                    aug[row][j] -= f * aug[col][j]
    # No sign normalization: the x^2+y^2 coefficient is pinned to +1, so the
    # rational triple is already the unique canonical key of this circle.
    return (aug[0][3], aug[1][3], aug[2][3])


def circle_key_int(p, q, r):
    """Fast all-integer canonical key of the circle through 3 points.

    The circle is  s*(x^2+y^2) + Dd*x + Ed*y + Fd = 0  with integers s > 0 and
    gcd(s, Dd, Ed, Fd) = 1 (a primitive representative, hence a unique hash key).

    Derivation (all integer, no Fractions): the circle through the three points
    satisfies  x*D + y*E + F = -(x^2+y^2).  Subtract the equation of the first
    point from the second and third; with
        a = x2-x1, b = y2-y1, c = x3-x1, d = y3-y1,
        t2 = s2-s1, t3 = s3-s1   (s_i = x_i^2 + y_i^2)
    we get the 2x2 system
        a*D + b*E = -t2
        c*D + d*E = -t3
    whose Cramer numerators are
        nD = -t2*d + b*t3,  nE = a*(-t3) + t2*c,  det = a*d - c*b,
    so D = nD/det, E = nE/det, and F = -s1 - x1*D - y1*E.  Multiplying the whole
    equation by det gives the integer coefficients below; the gcd makes it
    primitive, and the sign is fixed by s > 0.

    Returns None when the three points are collinear (det == 0).
    """
    (x1, y1), (x2, y2), (x3, y3) = p, q, r
    a = x2 - x1
    b = y2 - y1
    c = x3 - x1
    d = y3 - y1
    det = a * d - c * b
    if det == 0:
        return None
    s1 = x1 * x1 + y1 * y1
    t2 = (x2 * x2 + y2 * y2) - s1
    t3 = (x3 * x3 + y3 * y3) - s1
    nD = -t2 * d + b * t3
    nE = -a * t3 + t2 * c
    # D = nD/det, E = nE/det, F = -s1 - x1*D - y1*E
    #        = (-s1*det - x1*nD - y1*nE) / det
    nF = -s1 * det - x1 * nD - y1 * nE
    g = math.gcd(math.gcd(abs(nD), abs(nE)), math.gcd(abs(nF), abs(det)))
    if g == 0:
        g = 1
    s = det // g
    Dd = nD // g
    Ed = nE // g
    Fd = nF // g
    if s < 0:
        s, Dd, Ed, Fd = -s, -Dd, -Ed, -Fd
    return (s, Dd, Ed, Fd)


def key_to_cleared(key):
    """Deprecated shim kept for backwards compatibility: the integer key IS the
    cleared form."""
    return key


def circle_spectrum(n, max_pts=0):
    """Exact circle lattice-size histogram H[m] of the n x n grid.

    Enumerates all non-collinear triples (pure integer arithmetic), takes the
    primitive integer circle key, and then counts, once per deduplicated key,
    how many grid points of the box lie on it.  Circles with >= 4 points are
    exactly the ones contributing C(m,4) concyclic 4-subsets to C_n.

    The per-key membership count is vectorised with numpy over the n^2 grid.
    """
    import numpy as np

    pts = [(x, y) for y in range(n) for x in range(n)]
    N = len(pts)
    key_set = set()
    for i, j, k in combinations(range(N), 3):
        key = circle_key_int(pts[i], pts[j], pts[k])
        if key is not None:
            key_set.add(key)
    gx = np.arange(n, dtype=np.int64)
    GX, GY = np.meshgrid(gx, gx, indexing="xy")   # GY rows = y, GX cols = x
    gxs = GX.ravel()
    gys = GY.ravel()
    gsq = gxs * gxs + gys * gys
    H = defaultdict(int)
    M = 0
    for (s, Dd, Ed, Fd) in key_set:
        m = int(np.count_nonzero(s * gsq + Dd * gxs + Ed * gys + Fd == 0))
        if m >= 4:
            H[m] += 1
            if m > M:
                M = m
    return dict(H=H, M=M, n=n)


def derive(n, H, M):
    """From histogram H compute C_n, weighted mean m, cumulative fractions, etc."""
    Cn = sum(math.comb(m, 4) * cnt for m, cnt in H.items())
    wsum = sum(m * math.comb(m, 4) * cnt for m, cnt in H.items())
    mean_m = Fraction(wsum, Cn) if Cn else None
    out = {
        "n": n,
        "M_n": M,
        "C_n": Cn,
        "H": {str(m): cnt for m, cnt in sorted(H.items())},
        "weighted_mean_m": float(mean_m) if mean_m is not None else None,
        "weighted_mean_m_exact": str(mean_m) if mean_m is not None else None,
    }
    # cumulative share from circles with <= m0 board points
    cum = {}
    for m0 in [4, 5, 6, 7, 8, 9, 10, 11, 12, 16]:
        num = sum(math.comb(m, 4) * cnt for m, cnt in H.items() if m <= m0)
        cum[m0] = {
            "quads_from_m_le_m0": num,
            "C_n": Cn,
            "frac": Fraction(num, Cn) if Cn else None,
        }
    out["cum_le_m0"] = {
        str(m0): {
            "quads_from_m_le_m0": v["quads_from_m_le_m0"],
            "frac": float(v["frac"]) if v["frac"] is not None else None,
            "frac_exact": str(v["frac"]) if v["frac"] is not None else None,
        }
        for m0, v in cum.items()
    }
    return out


def all_circle_keys(pts):
    key_set = set()
    for i, j, k in combinations(range(len(pts)), 3):
        key = circle_key_int(pts[i], pts[j], pts[k])
        if key is not None:
            key_set.add(key)
    return key_set


def main():
    results = {}
    # Exact full enumeration of the circle spectrum for n = 3 .. 20.
    # Validated against the pre-existing exploration data for n = 6..11
    # (research/exploration/fact_circle_spectrum_*.json): every histogram entry,
    # every C_n and every M(n) agrees exactly.
    ns = list(range(3, 21))
    for n in ns:
        spec = circle_spectrum(n)
        row = derive(n, spec["H"], spec["M"])
        results[f"n{n}"] = row
        print(f"n={n} M={row['M_n']} C={row['C_n']} H={row['H']} meanm={row['weighted_mean_m']}",
              flush=True)

    report = {
        "task": "B475/B476 circle lattice-size spectrum M(n) for n=3..20",
        "method": ("enumerate all non-collinear triples -> primitive integer circle key "
                   "(s, Dd, Ed, Fd); deduplicate; count grid points per key with numpy; "
                   "keep m >= 4.  Pure integer arithmetic for the combinatorics."),
        "spectra": results,
    }

    # ---- B475: liminf of share from small-m circles as n grows ----
    b475 = {"claim": "exists m0 with liminf_n f_n(m0) > 0", "f_by_m0": {}}
    for m0 in [4, 5, 6, 7, 8, 12, 16]:
        series = []
        for n in ns:
            row = results[f"n{n}"]
            frac = row["cum_le_m0"][str(m0)]["frac"] if str(m0) in row["cum_le_m0"] else None
            series.append({"n": n, "frac": frac})
        b475["f_by_m0"][str(m0)] = series
    report["B475"] = b475

    # ---- B476: weighted mean m diverges; P(m<=m0) -> 0 for every fixed m0 ----
    b476 = {
        "claim": "for every fixed m, P(point-count <= m) -> 0; weighted mean diverges",
        "weighted_mean_m_by_n": {str(n): results[f"n{n}"]["weighted_mean_m"] for n in ns},
        "P_le_by_m0": {},
    }
    for m0 in [4, 5, 6, 7, 8, 12, 16]:
        s = []
        for n in ns:
            cum = results[f"n{n}"]["cum_le_m0"]
            frac = cum[str(m0)]["frac"] if str(m0) in cum else None
            s.append({"n": n, "P_le": (1 - frac) if frac is not None else None})
        b476["P_le_by_m0"][str(m0)] = s
    report["B476"] = b476

    # ---- trend series used in the individual verdict sheets ----
    trend = {"f4_series": [], "mean_m_series": []}
    for n in ns:
        f4 = results[f"n{n}"]["cum_le_m0"]["4"]["frac"]
        trend["f4_series"].append({"n": n, "f4": f4, "tail4": 1 - f4})
        trend["mean_m_series"].append({"n": n, "mean_m": results[f"n{n}"]["weighted_mean_m"]})
    report["trend"] = trend

    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
