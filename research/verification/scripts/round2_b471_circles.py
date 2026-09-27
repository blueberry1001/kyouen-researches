#!/usr/bin/env python3
"""B474-B477: concyclic-quad circle spectrum and decomposition.

Integer / rational arithmetic only (fractions.Fraction).
  B474  C_n increment vs new circle types / max-point jump
  B475  fixed-point-count circles carry positive fraction of C_n
  B476  point-count weighted by 4-subset contribution diverges
  B477  unique standard-chord assignment (primitive chord type)
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
OUT = ROOT / "research" / "verification" / "round2_b471.json"
sys.path.insert(0, str(ROOT / "research" / "verification" / "scripts"))
from batch08_verify import KNOWN_F, collinear_c4  # noqa: E402


def det4(r0, r1, r2, r3) -> int:
    """Integer det of 4x4 rows [x^2+y^2, x, y, 1]."""

    def det3(m):
        return (
            m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
        )

    rows = [list(r) for r in (r0, r1, r2, r3)]
    return (
        rows[0][0] * det3([row[1:] for row in rows[1:]])
        - rows[0][1] * det3([[rows[i][0]] + rows[i][2:] for i in (1, 2, 3)])
        + rows[0][2] * det3([[rows[i][0], rows[i][1], rows[i][3]] for i in (1, 2, 3)])
        - rows[0][3] * det3([row[:3] for row in rows[1:]])
    )


def is_collinear(p, q, r) -> bool:
    return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]) == 0


def circle_key(p, q, r):
    """Canonical (D, E, F) of x^2+y^2 + D x + E y + F = 0 through 3 non-collinear pts."""
    if is_collinear(p, q, r):
        return None
    # Solve:
    # x_i D + y_i E + F = -(x_i^2+y_i^2)
    x1, y1 = p
    x2, y2 = q
    x3, y3 = r
    b1 = -(x1 * x1 + y1 * y1)
    b2 = -(x2 * x2 + y2 * y2)
    b3 = -(x3 * x3 + y3 * y3)
    # Cramer's rule on [[x1,y1,1],[x2,y2,1],[x3,y3,1]] * [D,E,F]^T = [b1,b2,b3]
    det = (
        x1 * (y2 - y3)
        - y1 * (x2 - x3)
        + 1 * (x2 * y3 - x3 * y2)
    )
    if det == 0:
        return None
    dD = (
        b1 * (y2 - y3)
        - y1 * (b2 - b3)
        + 1 * (b2 * y3 - b3 * y2)
    )
    dE = (
        x1 * (b2 - b3)
        - b1 * (x2 - x3)
        + 1 * (x2 * b3 - x3 * b2)
    )
    dF = (
        x1 * (y2 * b3 - y3 * b2)
        - y1 * (x2 * b3 - x3 * b2)
        + b1 * (x2 * y3 - x3 * y2)
    )
    D = Fraction(dD, det)
    E = Fraction(dE, det)
    F = Fraction(dF, det)
    # canonical sign: clear to integers with positive lcm-ish — keep as reduced Fractions
    return (D, E, F)


def on_circle(key, pt) -> bool:
    D, E, F = key
    x, y = pt
    return x * x + y * y + D * x + E * y + F == 0


def circle_spectrum(n: int) -> dict:
    """Return per-circle data and C_n decomposition by m = |board ∩ circle|."""
    pts = [(x, y) for y in range(n) for x in range(n)]
    # collect concyclic non-collinear 4-sets
    quads = []
    for comb in combinations(range(n * n), 4):
        ps = [pts[i] for i in comb]
        # skip collinear
        if is_collinear(ps[0], ps[1], ps[2]) and is_collinear(ps[0], ps[1], ps[3]):
            continue
        rows = [(x * x + y * y, x, y, 1) for x, y in ps]
        if det4(*rows) != 0:
            continue
        quads.append(comb)

    # group 4-sets by circle (use first 3 pts to define key; verify 4th)
    by_circle: dict = {}
    for comb in quads:
        ps = [pts[i] for i in comb]
        key = circle_key(ps[0], ps[1], ps[2])
        if key is None:
            key = circle_key(ps[0], ps[1], ps[3])
        if key is None:
            key = circle_key(ps[0], ps[2], ps[3])
        if key is None:
            continue
        # verify all 4 on this circle
        if not all(on_circle(key, p) for p in ps):
            # try other triples
            found = None
            for t in combinations(range(4), 3):
                k2 = circle_key(ps[t[0]], ps[t[1]], ps[t[2]])
                if k2 and all(on_circle(k2, p) for p in ps):
                    found = k2
                    break
            if found is None:
                continue
            key = found
        by_circle.setdefault(key, {"quads": [], "pts": None})
        by_circle[key]["quads"].append(comb)

    # m = number of board points on circle
    circle_rows = []
    for key, rec in by_circle.items():
        mpts = [pts[i] for i in range(n * n) if on_circle(key, pts[i])]
        rec["pts"] = mpts
        m = len(mpts)
        c4 = math.comb(m, 4)
        # each 4-subset of these m points is concyclic (and not collinear? a circle
        # cannot contain 4 collinear points unless degenerate; collinear quads live
        # on lines, not on proper circles).  So C(m,4) should equal len(quads) on it.
        circle_rows.append({
            "m": m,
            "n_quads": len(rec["quads"]),
            "C_m_4": c4,
            "D": str(key[0]),
            "E": str(key[1]),
            "F": str(key[2]),
        })

    # consistency: sum of n_quads should equal len(quads)
    total_quads = sum(r["n_quads"] for r in circle_rows)
    total_cm4 = sum(r["C_m_4"] for r in circle_rows)

    # spectrum by m
    by_m = defaultdict(lambda: {"circles": 0, "quads": 0, "cm4": 0})
    for r in circle_rows:
        e = by_m[r["m"]]
        e["circles"] += 1
        e["quads"] += r["n_quads"]
        e["cm4"] += r["C_m_4"]

    return {
        "n": n,
        "n_concyclic_quads": len(quads),
        "n_circles": len(circle_rows),
        "sum_quads_on_circles": total_quads,
        "sum_C_m_4": total_cm4,
        "by_m": {str(m): dict(v) for m, v in sorted(by_m.items())},
        "M_n": max((r["m"] for r in circle_rows), default=0),
        "circles": circle_rows,
    }


def center_denom(key) -> int:
    """Denominator of circle center ( -D/2, -E/2 ) when written in lowest terms."""
    D, E, _ = key
    cx = -D / 2
    cy = -E / 2
    return math.lcm(cx.denominator, cy.denominator)


def main() -> None:
    # load existing report if present
    try:
        report = json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        report = {}

    ns = [3, 4, 5, 6]
    spectra = {}
    for n in ns:
        spec = circle_spectrum(n)
        spectra[n] = spec
        print(f"n={n} conc={spec['n_concyclic_quads']} circles={spec['n_circles']} "
              f"M={spec['M_n']} by_m={spec['by_m']} "
              f"sum_quads={spec['sum_quads_on_circles']} sum_cm4={spec['sum_C_m_4']}", flush=True)

    # C_n from known F_n and D_n
    C_table = {}
    D_table = {}
    for n in range(2, 13):
        Dn, _ = collinear_c4(n)
        D_table[n] = Dn
        if n in KNOWN_F:
            C_table[n] = KNOWN_F[n] - Dn
    print("C_n table:", C_table, flush=True)

    # ---------- B475 / B476: contribution of small-m circles ----------
    # Using the exact spectrum at each n: fraction of C_n coming from m <= m0.
    b475_rows = []
    for n in ns:
        spec = spectra[n]
        Cn = C_table.get(n, spec["n_concyclic_quads"])
        by_m = spec["by_m"]
        cum = 0
        for m0 in [4, 5, 6, 8, 10]:
            frac = 0
            for m_str, e in by_m.items():
                if int(m_str) <= m0:
                    frac += e["quads"]
            b475_rows.append({
                "n": n,
                "m0": m0,
                "quads_from_m_le_m0": frac,
                "C_n": Cn,
                "frac": frac / Cn if Cn else None,
            })
        # weighted mean of m over 4-subsets (B476)
        num = 0
        den = 0
        for m_str, e in by_m.items():
            m = int(m_str)
            num += m * e["quads"]
            den += e["quads"]
        mean_m = num / den if den else None
        # P(m <= m0) under uniform 4-subset
        p_le = {}
        for m0 in [4, 5, 6, 8, 10, 16]:
            p_le[str(m0)] = sum(e["quads"] for m_str, e in by_m.items() if int(m_str) <= m0) / den if den else None
        b475_rows.append({
            "n": n,
            "weighted_mean_m": mean_m,
            "P_m_le": p_le,
            "max_m": spec["M_n"],
        })
        print(f"n={n} weighted mean m={mean_m} P(m<=4)={p_le.get('4')} P(m<=6)={p_le.get('6')} M={spec['M_n']}", flush=True)

    # ---------- B474: increment structure ----------
    # "new primitive circle types" — classify circles by (m, center_denom, radius2 num/den)
    # and count how many types first appear at n vs how many circles persist.
    def type_key(n, row):
        # reconstruct from D,E,F strings
        D = Fraction(row["D"])
        E = Fraction(row["E"])
        F = Fraction(row["F"])
        return (row["m"], center_denom((D, E, F)), str(F))

    type_sets = {}
    M_of_n = {}
    C_of_n = {}
    for n in ns:
        spec = spectra[n]
        types = set()
        for row in spec["circles"]:
            types.add(type_key(n, row))
        type_sets[n] = types
        M_of_n[n] = spec["M_n"]
        C_of_n[n] = C_table.get(n, spec["n_concyclic_quads"])

    b474_rows = []
    for n in ns:
        if n == ns[0]:
            new_types = len(type_sets[n])
            prev_types = 0
        else:
            new_types = len(type_sets[n] - type_sets[n - 1])
            prev_types = len(type_sets[n - 1])
        dC = C_of_n[n] - C_of_n.get(n - 1, 0) if (n - 1) in C_of_n else None
        dM = M_of_n[n] - M_of_n.get(n - 1, 0) if (n - 1) in M_of_n else None
        b474_rows.append({
            "n": n,
            "C_n": C_of_n[n],
            "dC": dC,
            "M_n": M_of_n[n],
            "dM": dM,
            "n_types": len(type_sets[n]),
            "new_types": new_types,
        })
        print(f"B474 n={n} dC={dC} dM={dM} new_types={new_types} n_types={len(type_sets[n])}", flush=True)

    # correlation of dC with new_types vs dM (only a few points — descriptive)
    # also extend C_n table with known F_n for n=7..12 (no circle spectra)
    C_series = [{"n": n, "F": KNOWN_F.get(n), "D": D_table[n], "C": C_table[n]} for n in sorted(C_table)]

    # ---------- B477: standard-chord uniqueness test ----------
    # Assign each concyclic 4-set the lexicographically smallest primitive chord
    # (pair difference reduced) among its 6 pairs; count collisions (two different
    # circles sharing the same standard chord) and leftover coverage.
    b477 = {}
    for n in ns:
        spec = spectra[n]
        pts = [(x, y) for y in range(n) for x in range(n)]
        chord_map = defaultdict(set)  # chord -> set of circle keys
        assigned = 0
        for row in spec["circles"]:
            D = Fraction(row["D"])
            E = Fraction(row["E"])
            F = Fraction(row["F"])
            key = (D, E, F)
            mpts = [p for p in pts if on_circle(key, p)]
            # use the actual 4-subsets recorded? we only have counts; recompute
            # chords from mpts' 4-subsets is expensive; use all pairs of mpts
            pairs = list(combinations(mpts, 2))
            # standard chord = smallest primitive direction + offset signature
            def chord_sig(a, b):
                dx, dy = b[0] - a[0], b[1] - a[1]
                g = math.gcd(abs(dx), abs(dy)) if (dx or dy) else 1
                pdx, pdy = dx // g, dy // g
                if pdx < 0 or (pdx == 0 and pdy < 0):
                    pdx, pdy = -pdx, -pdy
                    a, b = b, a
                # intercept-ish: value of (-pdy)*x + pdx*y
                c = -pdy * a[0] + pdx * a[1]
                return (pdx, pdy, c)

            sigs = sorted({chord_sig(a, b) for a, b in pairs})
            if sigs:
                std = sigs[0]
                chord_map[std].add(key)
                assigned += 1
        multi = {k: len(v) for k, v in chord_map.items() if len(v) > 1}
        b477[str(n)] = {
            "n_circles": spec["n_circles"],
            "n_std_chords": len(chord_map),
            "circles_with_std": assigned,
            "chords_shared_by_multiple_circles": len(multi),
            "max_circles_per_chord": max(multi.values()) if multi else 1,
            "collision_examples": [
                {"chord": str(k), "n_circles": v} for k, v in sorted(multi.items(), key=lambda kv: -kv[1])[:5]
            ],
        }
        print(f"B477 n={n} chords={len(chord_map)} collisions={len(multi)} "
              f"max_per_chord={b477[str(n)]['max_circles_per_chord']}", flush=True)

    report["B474"] = {
        "claim": "C_n increment tracks new primitive circle types more than M(n) jump",
        "rows": b474_rows,
        "C_series": C_series,
        "M_of_n": M_of_n,
        "note": "type = (m, center_denom, F-rational); descriptive only on n=3..6",
    }
    report["B475"] = {
        "claim": "fixed-m circles carry positive liminf fraction of C_n",
        "rows": b475_rows,
    }
    report["B476"] = {
        "claim": "weighted circle point-count diverges (conflicts B475)",
        "weighted_mean_m_by_n": {str(n): next((r["weighted_mean_m"] for r in b475_rows
                                               if r.get("n") == n and "weighted_mean_m" in r), None)
                                 for n in ns},
        "P_m_le_by_n": {str(n): next((r["P_m_le"] for r in b475_rows
                                      if r.get("n") == n and "P_m_le" in r), None)
                        for n in ns},
    }
    report["B477"] = {
        "claim": "unique standard-chord assignment gives low-overlap decomposition",
        "by_n": b477,
    }
    report["circle_spectra"] = {str(n): {k: v for k, v in spectra[n].items() if k != "circles"}
                                for n in ns}

    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
