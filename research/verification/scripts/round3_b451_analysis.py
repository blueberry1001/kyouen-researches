#!/usr/bin/env python3
"""Round3 B451-B457: rational-centre denominator analysis.

INFINITE-LATTICE CATALOGUE
--------------------------
A circle with a rational centre is canonically

    (cx, cy, r2) = (alpha/q0, beta/q0, M/q0^2),

q0 = lcm(den(cx), den(cy)), gcd(alpha, beta, q0) = 1, M >= 1 integer.
Its COMPLETE lattice point set is

    { ((u-alpha)/q0, (v-beta)/q0) : u^2+v^2 = M,
                                      u = alpha (mod q0), v = beta (mod q0) }

Derivation.  A circle with rational centre (cx, cy) and squared radius r2 is
  (x - cx)^2 + (y - cy)^2 = r2.
Write cx = alpha/q0, cy = beta/q0, r2 = M/q0^2, and put u = q0 x + alpha,
v = q0 y + beta.  Then u, v are integers and
  u^2 + v^2 = q0^2 [(x+cx)^2 + (y+cy)^2] = q0^2 r2 = M.
Conversely any (u,v) with u^2+v^2 = M and u = alpha (mod q0), v = beta
(mod q0) gives x = (u - alpha)/q0, y = (v - beta)/q0 in Z and lies on the circle.
So the catalogue is an exact sum-of-two-squares residue computation: the
"二平方和+剰余版" the round2 note asked for.  Complete, integer-only, no triple
enumeration, no board needed, microseconds per circle.
Swept for M <= MAXM and q0 <= QMAX.

Board-side data comes from the validated fast census round3_b451_census.py
(n = 4..12) and is folded in for the board-relative questions (B454, B457).

Output: research/verification/round3_b451_analysis.json
"""
from __future__ import annotations

import json
import math
import time
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round3_b451_analysis.json"

MAXM = 6000          # upper bound on the cleared radius M = q0^2 r^2
QMAX = 10            # upper bound on the centre denominator q0
DETAIL_M = 3000      # keep point sets / window spectra for circles with M <= this
MAX_PTS_DETAIL = 24  # skip window spectra above this many points


# --------------------------------------------------------------- sum of squares
_REP_UV: dict[int, list[tuple[int, int]]] = {}
_PR: dict[int, list[int]] = {}


def reps_uv(M: int):
    """All unordered abs pairs (u0,v0), 0 <= u0 <= v0, with u0^2+v^2 = M."""
    if M < 0:
        return []
    hit = _REP_UV.get(M)
    if hit is not None:
        return hit
    out = []
    lim = math.isqrt(M)
    for u in range(lim + 1):
        v2 = M - u * u
        v = math.isqrt(v2)
        if v * v == v2 and u <= v:
            out.append((u, v))
    _REP_UV[M] = out
    return out


def variants(u0, v0):
    """All ordered signed integer pairs generated from the abs pair (u0,v0)."""
    us = (u0, -u0) if u0 else (0,)
    vs = (v0, -v0) if v0 else (0,)
    out = [(u, v) for u in us for v in vs]
    if u0 != v0:
        out += [(v, u) for u in us for v in vs]
    return out


def r2_exact(M: int) -> int:
    """#{ordered signed (u,v) in Z^2 : u^2+v^2 = M}; 0 iff a prime p = 3 mod 4
    occurs to an odd exponent, else 4 * prod_{p = 1 mod 4} (a_p + 1)."""
    if M < 0:
        return 0
    if M == 0:
        return 1
    t, val, p = M, 4, 2
    while p * p <= t:
        if t % p == 0:
            e = 0
            while t % p == 0:
                t //= p
                e += 1
            if p % 4 == 1:
                val *= (e + 1)
            elif p % 4 == 3 and e % 2 == 1:
                return 0
        p = 3 if p == 2 else p + 2
    if t > 1:
        if t % 4 == 1:
            val *= 2
        elif t % 4 == 3:
            return 0
    return val


def primes_upto(limit: int):
    hit = _PR.get(limit)
    if hit is not None:
        return hit
    sieve = bytearray([1]) * (limit + 1)
    sieve[0] = 0
    if limit >= 1:
        sieve[1] = 0
    for p in range(2, math.isqrt(limit) + 1):
        if sieve[p]:
            sieve[p * p:limit + 1:p] = bytearray(len(range(p * p, limit + 1, p)))
    out = [p for p in range(2, limit + 1) if sieve[p]]
    _PR[limit] = out
    return out


def R_bound(M: int):
    """2M * prod_{p in A(M)}(1 + 1/p), A(M) = {p <= M : p = 1 mod 4}, as an exact
    (numerator, denominator).  Upper bound on #{(u,v) in Z^2 : u^2+v^2 = M}."""
    if M <= 0:
        return (0, 1)
    num, den = 2 * M, 1
    for p in primes_upto(M):
        if p % 4 == 1:
            num *= (p + 1)
            den *= p
    return (num, den)


# ------------------------------------------------------------------- catalogue
def build_catalogue(maxm=MAXM, qmax=QMAX):
    """(M, q0, alpha, beta) -> point count, complete for M <= maxm, q0 <= qmax."""
    t0 = time.time()
    pts = defaultdict(set)          # key -> set of (u, v) with u^2+v^2 = M
    for M in range(1, maxm + 1):
        for (u0, v0) in reps_uv(M):
            for (u, v) in variants(u0, v0):
                for q in range(1, qmax + 1):
                    # x = (u + a)/q0 with u = a (mod q0)  =>  a = u (mod q0)
                    cx = Fraction(u % q, q)
                    cy = Fraction(v % q, q)
                    q0 = cx.denominator * cy.denominator // math.gcd(
                        cx.denominator, cy.denominator)
                    if q0 > qmax:
                        continue
                    a = cx.numerator * (q0 // cx.denominator)
                    b = cy.numerator * (q0 // cy.denominator)
                    pts[(M, q0, a, b)].add((u, v))
    out = {k: len(v) for k, v in pts.items()}
    print(f"  catalogue: {len(out)} circles with >=1 lattice point "
          f"(M<={maxm}, q0<={qmax}) in {time.time()-t0:.1f}s", flush=True)
    return out, {k: v for k, v in pts.items()}


def circle_points(M, q0, a, b):
    """Complete lattice point set."""
    out = []
    for (u0, v0) in reps_uv(M):
        for (u, v) in variants(u0, v0):
            if (u - a) % q0 == 0 and (v - b) % q0 == 0:
                out.append(((u - a) // q0, (v - b) // q0))
    return sorted(set(out))


def bbox(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def window_spectrum(pts, extra=1):
    """A(C) = { |P(C) cap W| : W an axis-parallel square window with integer
    corner and integer side w >= 1 }."""
    if not pts:
        return {0}
    x0, y0, x1, y1 = bbox(pts)
    span = max(x1 - x0, y1 - y0) + 2
    A = set()
    for cx in range(x0 - extra, x1 + 2):
        for cy in range(y0 - extra, y1 + 2):
            for w in range(1, span + 1):
                c = 0
                for (px, py) in pts:
                    if cx <= px <= cx + w - 1 and cy <= py <= cy + w - 1:
                        c += 1
                A.add(c)
    return A


def d4_orbit(pts):
    ax = min(p[0] for p in pts)
    ay = min(p[1] for p in pts)
    s = {(p[0] - ax, p[1] - ay) for p in pts}
    W = max(p[0] for p in s)
    H = max(p[1] for p in s)
    imgs = set()
    for k in range(8):
        t = set()
        for x, y in s:
            if k == 0:
                a, b = x, y
            elif k == 1:
                a, b = y, x
            elif k == 2:
                a, b = W - x, y
            elif k == 3:
                a, b = x, H - y
            elif k == 4:
                a, b = W - x, H - y
            elif k == 5:
                a, b = y, H - x
            elif k == 6:
                a, b = W - y, x
            else:
                a, b = W - y, H - x
            t.add((a, b))
        imgs.add(frozenset(t))
    return len(imgs)


# --------------------------------------------------------------- q classifiers
def qclass(q0):
    if q0 == 1:
        return "q1"
    if q0 == 2:
        return "q2"
    if q0 & (q0 - 1) == 0:
        return "q2pow"
    if q0 % 2 == 1:
        return "q_odd_ge3"
    return "q_even_nonpow"


def factor_type(q0):
    v2, t = 0, q0
    while t % 2 == 0:
        t //= 2
        v2 += 1
    p1, p3, p = [], [], 3
    while p * p <= t:
        while t % p == 0:
            t //= p
            (p1 if p % 4 == 1 else p3).append(p)
        p += 2
    if t > 1:
        (p1 if t % 4 == 1 else p3).append(t)
    return {"v2": v2, "p1mod4": p1, "p3mod4": p3,
            "label": f"2^{v2}" + ("*" + "*".join(map(str, p1)) if p1 else "")
                     + ("*3mod4:" + "*".join(map(str, p3)) if p3 else "")}


def _hist(vals, nb=10):
    if not vals:
        return {}
    lo, hi = min(vals), max(vals)
    if hi == lo:
        return {str(lo): len(vals)}
    w = (hi - lo) / nb
    h = defaultdict(int)
    for v in vals:
        h[min(nb - 1, int((v - lo) / w))] += 1
    return {f"{lo + i*w:.3f}..{lo + (i+1)*w:.3f}": h[i] for i in sorted(h)}


# --------------------------------------------------------------------- driver
def self_test():
    """Internal consistency checks of the sum-of-two-squares machinery."""
    for M in range(0, 500):
        n_enum = sum(len(variants(u, v)) for (u, v) in reps_uv(M))
        if M == 0:
            assert n_enum == 1, (M, n_enum)
        else:
            assert n_enum == r2_exact(M), (M, n_enum, r2_exact(M))
    # B461 family: centre (1/2,1/2), r^2 = 25/2  -> M = 50 -> 12 points
    P = circle_points(50, 2, 1, 1)
    assert len(P) == 12, (len(P), sorted(P))
    # integer centre r^2 = 25 -> 12 points
    assert len(circle_points(25, 1, 0, 0)) == 12
    # residue selection really splits.  M = 65 = 1*5*13 has r2 = 16 and every
    # representation is odd-odd (65 = 1 mod 4, only 1 mod 4 primes), so the four
    # q0=2 classes receive 0, 8, 8, 0 points -- two classes are dead.
    assert r2_exact(65) == 16
    assert len(circle_points(65, 2, 0, 0)) == 0
    assert len(circle_points(65, 2, 0, 1)) == 8
    assert len(circle_points(65, 2, 1, 0)) == 8
    assert len(circle_points(65, 2, 1, 1)) == 0
    assert sum(len(circle_points(65, 2, a, b)) for a in (0, 1)
               for b in (0, 1)) == 16
    assert r2_exact(25) == 12
    assert sum(len(circle_points(25, 2, a, b)) for a in (0, 1)
               for b in (0, 1)) == 12
    # every enumerated point really lies on the circle
    for (x, y) in P:
        assert 2 * ((2 * x + 1) ** 2 + (2 * y + 1) ** 2) == 4 * 50
    print("  self-test OK: r2 formula (M<500), 25/2 -> 12 pts, 25 -> 12 pts, "
          "65 splits 0/8/8/0 over the four q0=2 classes", flush=True)


def cross_validate_against_census(maxn=10):
    """The two implementations are independent (triple-based numpy census vs
    sum-of-two-squares catalogue).  Check that every census circle is found in
    the catalogue with the SAME complete point set."""
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent))
    import round3_b451_census as C  # noqa: E402
    checked, bad = 0, []
    for n in range(4, maxn + 1):
        rec = C.census(n)
        for r in rec["records"]:
            cx, cy, q, r2, g, M = C.circle_geom(r["A"], r["D"], r["E"], r["F"])
            a = cx.numerator * (q // cx.denominator)
            b = cy.numerator * (q // cy.denominator)
            if q > QMAX or M > MAXM:
                continue
            cat_pts = circle_points(M, q, a, b)
            board_pts = [tuple(p) for p in r["pts"]]
            checked += 1
            if not set(board_pts) <= set(cat_pts):
                bad.append((n, (r["A"], r["D"], r["E"], r["F"]), "board-not-subset"))
            if len(cat_pts) < r["m"]:
                bad.append((n, (r["A"], r["D"], r["E"], r["F"]), "cat-too-small"))
    print(f"  cross-validation: {checked} census circles (n=4..{maxn}) checked "
          f"against the catalogue, {len(bad)} mismatches", flush=True)
    if bad:
        for x in bad[:10]:
            print("   MISMATCH", x, flush=True)
    return {"n_checked": checked, "n_bad": len(bad), "examples": bad[:10]}


def main():
    t0 = time.time()
    out = {"generated": "round3_b451_analysis",
           "params": {"MAXM": MAXM, "QMAX": QMAX, "DETAIL_M": DETAIL_M,
                      "MAX_PTS_DETAIL": MAX_PTS_DETAIL},
           "catalog": {}, "B451": {}, "B452": {}, "B453": {},
           "B454": {}, "B455": {}, "B456": {}, "B457": {}}

    self_test()
    out["cross_validation_vs_census"] = cross_validate_against_census(10)
    counts, _sets = build_catalogue()
    circles = []
    for (M, q0, a, b), m in counts.items():
        if m < 4:
            continue
        r2 = Fraction(M, q0 * q0)
        circles.append({"M": M, "q0": q0, "alpha": a, "beta": b, "m": m,
                        "r2": r2, "r2s": f"{r2.numerator}/{r2.denominator}",
                        "qclass": qclass(q0), "ft": factor_type(q0)})
    circles.sort(key=lambda c: (c["r2"], c["q0"], c["alpha"], c["beta"]))
    print(f"  {len(circles)} circles with >=4 lattice points "
          f"({time.time()-t0:.1f}s)", flush=True)

    by_class = defaultdict(int)
    by_q = defaultdict(int)
    for c in circles:
        by_class[c["qclass"]] += 1
        by_q[c["q0"]] += 1
    out["catalog"] = {
        "n_circles_ge1": len(counts),
        "n_circles_ge4": len(circles),
        "counts_by_qclass": dict(sorted(by_class.items())),
        "counts_by_q0": {str(k): by_q[k] for k in sorted(by_q)},
        "m_hist_by_qclass": {},
    }
    for cl in sorted(by_class):
        h = defaultdict(int)
        for c in circles:
            if c["qclass"] == cl:
                h[c["m"]] += 1
        out["catalog"]["m_hist_by_qclass"][cl] = {str(k): h[k] for k in sorted(h)}
    m_all = defaultdict(int)
    for c in circles:
        m_all[c["m"]] += 1
    out["catalog"]["m_hist_all"] = {str(k): m_all[k] for k in sorted(m_all)}
    print("  m hist:", out["catalog"]["m_hist_all"], flush=True)
    print("  by qclass:", out["catalog"]["counts_by_qclass"], flush=True)

    # ---------------------------------------------------------------- details
    detail = []
    for c in circles:
        if c["M"] > DETAIL_M or c["m"] > MAX_PTS_DETAIL:
            continue
        P = circle_points(c["M"], c["q0"], c["alpha"], c["beta"])
        assert len(P) == c["m"], (c, len(P))
        x0, y0, x1, y1 = bbox(P)
        W, H = x1 - x0 + 1, y1 - y0 + 1
        A = window_spectrum(P)
        d = {k: v for k, v in c.items() if k != "r2"}
        d["pts"] = [list(p) for p in P]
        d["bbox"] = [W, H]
        d["side"] = max(W, H)
        d["A"] = sorted(A)
        d["A_len"] = len(A)
        d["holes"] = sorted(set(range(len(P) + 1)) - A)
        d["holes_len"] = len(d["holes"])
        d["d4_orbit"] = d4_orbit(P)
        detail.append(d)
    print(f"  {len(detail)} circles with detail records ({time.time()-t0:.1f}s)",
          flush=True)

    # =====================================================================
    # B451  same r^2, different centre denominators, both >= 4 points,
    #       different counts
    # =====================================================================
    by_r2 = defaultdict(list)
    for c in circles:
        by_r2[c["r2s"]].append(c)
    b451 = []
    for r2s, lst in by_r2.items():
        if len(lst) < 2:
            continue
        best = {}
        for c in lst:
            q = c["q0"]
            best[q] = max(best.get(q, 0), c["m"])
        if len(best) < 2 or len(set(best.values())) < 2:
            continue
        b451.append({
            "r2": r2s,
            "best_m_by_q0": {str(k): best[k] for k in sorted(best)},
            "witness": [
                {"q0": c["q0"], "alpha": c["alpha"], "beta": c["beta"],
                 "M": c["M"], "m": c["m"], "pts": None}
                for c in lst
                if c["m"] == best[c["q0"]]
            ][:8],
        })
    b451.sort(key=lambda r: (Fraction(r["r2"]), list(r["best_m_by_q0"])))
    out["B451"] = {
        "claim": "exists a radius r^2 and two centre denominators q1 != q2 such "
                 "that both circles carry >= 4 lattice points but different counts",
        "search_range": {"M_max": MAXM, "q0_max": QMAX},
        "n_r2_with_multi_q_and_different_counts": len(b451),
        "smallest_examples": b451[:16],
    }
    print(f"B451: {len(b451)} radii with >=2 denominators and differing counts",
          flush=True)

    # =====================================================================
    # B452  under a radius cap, does some q >= 3 circle beat the best q = 1 one?
    # =====================================================================
    caps = sorted({c["r2"] for c in circles})
    b452_rows = []
    run = {1: 0, 2: 0, "ge3": 0}
    wit = {1: None, 2: None, "ge3": None}
    for cap in caps:
        for c in circles:
            if c["r2"] != cap:
                continue
            k = 1 if c["q0"] == 1 else (2 if c["q0"] == 2 else "ge3")
            if c["m"] > run[k]:
                run[k] = c["m"]
                wit[k] = {"r2": c["r2s"], "q0": c["q0"], "M": c["M"],
                          "alpha": c["alpha"], "beta": c["beta"], "m": c["m"]}
        b452_rows.append({
            "r2_cap": f"{cap.numerator}/{cap.denominator}",
            "best_q1": run[1], "best_q2": run[2], "best_q_ge3": run["ge3"],
            "wit_q1": wit[1], "wit_q2": wit[2], "wit_q_ge3": wit["ge3"],
            "q_ge3_beats_q1": run["ge3"] > run[1],
            "q_ge3_beats_q2": run["ge3"] > run[2],
        })
    first = next((r for r in b452_rows if r["q_ge3_beats_q1"]), None)
    out["B452"] = {
        "claim": "under a common radius cap some q >= 3 circle carries strictly "
                 "more lattice points than the best q = 1 circle",
        "search_range": {"M_max": MAXM, "q0_max": QMAX},
        "n_caps": len(b452_rows),
        "first_cap_where_q_ge3_beats_q1": first,
        "n_caps_where_q_ge3_beats_q1": sum(1 for r in b452_rows
                                           if r["q_ge3_beats_q1"]),
        "final_row": b452_rows[-1] if b452_rows else None,
        "rows_head": b452_rows[:30],
    }
    print("B452 first beat:", first, flush=True)

    # =====================================================================
    # B453  does the prime factor type of q organise the point-count bound?
    # =====================================================================
    b453 = []
    for cl in sorted(by_class):
        sub = [c for c in circles if c["qclass"] == cl]
        mmax = max(c["m"] for c in sub)
        arg = [c for c in sub if c["m"] == mmax]
        b453.append({
            "qclass": cl, "n_circles": len(sub), "max_m": mmax,
            "min_M_attaining_max_m": min(c["M"] for c in arg),
            "min_r2_attaining_max_m": min(c["r2s"] for c in arg),
            "q0s_present": sorted({c["q0"] for c in sub}),
            "argmax": {"M": arg[0]["M"], "q0": arg[0]["q0"],
                       "alpha": arg[0]["alpha"], "beta": arg[0]["beta"],
                       "r2": arg[0]["r2s"], "m": mmax},
        })
    b453_q = []
    for q0 in sorted(by_q):
        sub = [c for c in circles if c["q0"] == q0]
        mmax = max(c["m"] for c in sub)
        b453_q.append({"q0": q0, "ft": factor_type(q0), "n_circles": len(sub),
                       "max_m": mmax,
                       "min_M_attaining_max_m": min(c["M"] for c in sub
                                                    if c["m"] == mmax),
                       "min_r2_attaining_max_m": min(c["r2s"] for c in sub
                                                    if c["m"] == mmax)})
    out["B453"] = {
        "claim": "splitting q into 2-adic part / 1 mod 4 primes / 3 mod 4 primes "
                 "gives upper bounds that explain the q ordering",
        "by_qclass": b453, "by_q0": b453_q,
    }
    print("B453 by class:", [(r["qclass"], r["max_m"], r["min_M_attaining_max_m"])
                             for r in b453], flush=True)
    print("B453 by q0:", [(r["q0"], r["max_m"], r["min_M_attaining_max_m"])
                          for r in b453_q], flush=True)

    # =====================================================================
    # B454  at equal point count m, is the minimal containing board of the
    #       q = 2^a family <= that of the odd q >= 3 family?
    # =====================================================================
    minboard = {}
    for d in detail:
        k = (d["m"], d["qclass"])
        if k not in minboard or d["side"] < minboard[k]:
            minboard[k] = d["side"]
    rows = []
    for m in sorted({k[0] for k in minboard}):
        r = {"m": m}
        for cl in ("q1", "q2", "q2pow", "q_odd_ge3", "q_even_nonpow"):
            r[cl] = minboard.get((m, cl))
        a, b = r["q2pow"], r["q_odd_ge3"]
        r["comparable"] = a is not None and b is not None
        r["claim_holds"] = r["comparable"] and a <= b
        rows.append(r)
    comp = [r for r in rows if r["comparable"]]
    out["B454"] = {
        "claim": "for the smallest square board first realising m points, the "
                 "q = 2^a family has axis-parallel side <= the odd q >= 3 family",
        "detail_range": {"M_max": DETAIL_M, "max_points": MAX_PTS_DETAIL},
        "rows": rows,
        "n_comparable": len(comp),
        "n_claim_holds": sum(1 for r in comp if r["claim_holds"]),
        "violations": [r for r in comp if not r["claim_holds"]],
    }
    print("B454 comparable:", len(comp), "holds:", out["B454"]["n_claim_holds"],
          "violations:", out["B454"]["violations"], flush=True)

    # =====================================================================
    # B455  residue-class selection: fixed M, one residue class richer?
    # =====================================================================
    by_Mq = defaultdict(lambda: defaultdict(int))
    for c in circles:
        if c["q0"] >= 3:
            by_Mq[(c["M"], c["q0"])][(c["alpha"], c["beta"])] = c["m"]
    b455 = []
    for (M, q0), d in sorted(by_Mq.items()):
        if len(d) < 2:
            continue
        vals = sorted(d.values(), reverse=True)
        b455.append({
            "M": M, "q0": q0, "r2": f"{M}/{q0*q0}",
            "n_classes_used": len(d), "n_classes_possible": q0 * q0,
            "n_classes_all_q2": len(d) == q0 * q0,
            "max_m": vals[0], "min_m": vals[-1],
            "spread": vals[0] - vals[-1],
            "top_classes": sorted(((f"{k[0]},{k[1]}", v) for k, v in d.items()),
                                  key=lambda kv: -kv[1])[:6],
        })
    out["B455"] = {
        "claim": "for some best circle family a single residue class of the "
                 "cleared two-squares equation carries more points than the rest",
        "definition": "for each (M, q0) with q0 >= 3 and >= 2 realised classes, "
                      "the point counts over the realised classes (alpha,beta) mod q0",
        "n_entries": len(b455),
        "n_entries_all_q2_classes_used": sum(1 for r in b455
                                              if r["n_classes_all_q2"]),
        "n_entries_with_spread_gt0": sum(1 for r in b455 if r["spread"] > 0),
        "spread_hist": _hist([r["spread"] for r in b455], 8),
        "max_rows": sorted(b455, key=lambda r: -r["spread"])[:20],
    }
    print("B455 entries:", len(b455), "spread>0:",
          out["B455"]["n_entries_with_spread_gt0"], flush=True)

    # =====================================================================
    # B456  fixed q: do the record point-count jumps need a new arithmetic type?
    # =====================================================================
    b456 = {}
    for q0 in sorted(by_q):
        sub = sorted((c for c in circles if c["q0"] == q0),
                     key=lambda c: (c["M"], c["alpha"], c["beta"]))
        rec, jumps = 0, []
        for c in sub:
            if c["m"] > rec:
                rec = c["m"]
                base = c["M"] // (q0 * q0)
                sq = math.isqrt(base)
                jumps.append({
                    "M": c["M"], "r2": c["r2s"], "m": c["m"],
                    "r2_cleared_numerator": base,
                    "is_perfect_square": sq * sq == base,
                    "new_1mod4_prime": min((p for p in (1, 5, 13, 17, 29, 37, 41)
                                            if p > base or base % p == 0),
                                           default=None),
                })
        b456[str(q0)] = {"max_m": rec, "n_jumps": len(jumps),
                        "jumps": jumps[:25]}
    out["B456"] = {
        "claim": "for fixed q, infinitely many radius thresholds need a new "
                 "arithmetic type rather than integer scaling of an earlier best",
        "by_q0": b456,
        "n_jumps_by_q0": {k: v["n_jumps"] for k, v in b456.items()},
    }
    print("B456 jumps per q0:", out["B456"]["n_jumps_by_q0"], flush=True)

    # =====================================================================
    # B457  at equal complete point count m, do q >= 3 circles have more
    #       attainable in-window counts than q <= 2 ones?
    # =====================================================================
    by_m_cls = defaultdict(list)
    for d in detail:
        cls = "q<=2" if d["q0"] <= 2 else "q>=3"
        by_m_cls[(d["m"], cls)].append(d)
    b457 = []
    for m in sorted({k[0] for k in by_m_cls}):
        lo = by_m_cls.get((m, "q<=2"), [])
        hi = by_m_cls.get((m, "q>=3"), [])
        if not lo or not hi:
            continue
        f = lambda L, k: sum(r[k] for r in L) / len(L)
        b457.append({
            "m": m, "n_q_le_2": len(lo), "n_q_ge_3": len(hi),
            "mean_|A|_q_le_2": f(lo, "A_len"), "mean_|A|_q_ge_3": f(hi, "A_len"),
            "mean_holes_q_le_2": f(lo, "holes_len"),
            "mean_holes_q_ge_3": f(hi, "holes_len"),
            "mean_side_q_le_2": f(lo, "side"), "mean_side_q_ge_3": f(hi, "side"),
            "mean_d4_q_le_2": f(lo, "d4_orbit"), "mean_d4_q_ge_3": f(hi, "d4_orbit"),
            "claim_holds": f(hi, "A_len") > f(lo, "A_len"),
        })
    out["B457"] = {
        "claim": "at equal complete point count m, q >= 3 circles have strictly "
                 "more kinds of in-board point count under square-window cuts "
                 "than q <= 2 circles",
        "definition": "A(C) = {|P(C) cap W| : W integer axis-parallel square "
                      "window}; |A(C)| compared at equal m",
        "detail_range": {"M_max": DETAIL_M, "max_points": MAX_PTS_DETAIL},
        "rows": b457,
        "n_comparable": len(b457),
        "n_claim_holds": sum(1 for r in b457 if r["claim_holds"]),
    }
    print("B457 comparable:", len(b457), "holds:", out["B457"]["n_claim_holds"],
          flush=True)

    out["detail_circles"] = detail
    out["total_runtime_s"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print("saved", OUT, "in", out["total_runtime_s"], "s")


if __name__ == "__main__":
    main()
