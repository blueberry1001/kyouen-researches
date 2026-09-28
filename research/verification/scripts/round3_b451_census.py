#!/usr/bin/env python3
"""Round3 B451-B457 step 1: fast lattice-circle census (pure Python + numpy).

Integers only (int64 everywhere); no floating point is used in any decision.

Algorithm
---------
1.  All triples (i<j<k) of the n^2 grid points are generated vectorised.
2.  Every non-collinear triple yields the circumcircle written as the PRIMITIVE
    integer quadruple (A, D, E, F) of

        A (x^2 + y^2) = D x + E y + F ,   A > 0, gcd(A,D,E,F) = 1.

    That quadruple is a unique key for the circle (if two primitive
    quadruples with A>0 describe the same circle they are equal).
3.  Unique keys are de-duplicated with one lexsort.
4.  For every unique key the grid points on the circle are found by a chunked
    numpy scan   A*s - D*x - E*y - F == 0  over the whole grid.
5.  Circles with m = |P(C) cap grid| >= 4 are exactly the circles that carry a
    forbidden concyclic quad; each of them carries C(m,4) of them.

Cost: O(C(n^2,3)) triples + O(#unique_circles * n^2) membership tests.
n=12: 487,344 triples -> a few seconds.

Outputs research/verification/round3_b451_census.json
"""
from __future__ import annotations

import json
import math
import time
from fractions import Fraction
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification" / "round3_b451_census.json"
EXPL = ROOT / "research" / "exploration"

KNOWN_F = {2: 1, 3: 14, 4: 194, 5: 826, 6: 2491, 7: 6364,
           8: 14564, 9: 29152, 10: 54441, 11: 95670, 12: 158426}


# ---------------------------------------------------------------- utilities
def collinear_c4(n: int) -> int:
    """Number of collinear 4-subsets of the n x n grid (closed form over lines)."""
    pts = [(x, y) for y in range(n) for x in range(n)]
    S = set(pts)
    total = 0
    for dx in range(0, n):
        for dy in range(-n + 1, n):
            if dx == 0 and dy <= 0:
                continue
            if dx > 0 and math.gcd(dx, abs(dy)) != 1:
                continue
            if dx == 0 and dy != 1:
                continue
            seen = set()          # must be per-direction
            for x, y in pts:
                if (x, y) in seen:
                    continue
                sx, sy = x, y
                while (sx - dx, sy - dy) in S:
                    sx, sy = sx - dx, sy - dy
                L = 0
                cx, cy = sx, sy
                while (cx, cy) in S:
                    seen.add((cx, cy))
                    L += 1
                    cx, cy = cx + dx, cy + dy
                if L >= 4:
                    total += math.comb(L, 4)
    return total


def triple_indices(N: int):
    """All (i<j<k) index triples as three int64 arrays of length C(N,3)."""
    I, J = np.triu_indices(N, k=1)
    cnt = (N - 1 - J).astype(np.int64)          # k in [J+1, N-1]
    total = int(cnt.sum())
    assert total == N * (N - 1) * (N - 2) // 6, (total, N)
    offs = np.zeros(len(cnt), dtype=np.int64)
    np.cumsum(cnt[:-1], out=offs[1:])
    rep = np.repeat(np.arange(len(cnt), dtype=np.int64), cnt)
    pos = np.arange(total, dtype=np.int64) - offs[rep]
    return I[rep], J[rep], J[rep] + 1 + pos


def circle_keys(X, Y, S, I, J, K):
    """Primitive (A,D,E,F) of A(x^2+y^2)=Dx+Ey+F for every non-degenerate triple."""
    x1, y1, s1 = X[I], Y[I], S[I]
    x2, y2, s2 = X[J], Y[J], S[J]
    x3, y3, s3 = X[K], Y[K], S[K]
    det = x1 * (y2 - y3) - y1 * (x2 - x3) + (x2 * y3 - x3 * y2)
    nz = det != 0
    det, x1, y1, x2, y2, x3, y3, s1, s2, s3 = (
        a[nz] for a in (det, x1, y1, x2, y2, x3, y3, s1, s2, s3))
    b1, b2, b3 = -s1, -s2, -s3
    nD = b1 * (y2 - y3) - y1 * (b2 - b3) + (b2 * y3 - b3 * y2)
    nE = x1 * (b2 - b3) - b1 * (x2 - x3) + (x2 * b3 - x3 * b2)
    nF = (x1 * (y2 * b3 - y3 * b2) - y1 * (x2 * b3 - x3 * b2)
          + b1 * (x2 * y3 - x3 * y2))
    sgn = np.where(det < 0, -1, 1)
    A = det * sgn
    Dp = -nD * sgn          # A(x^2+y^2) = Dp x + Ep y + Fp
    Ep = -nE * sgn
    Fp = -nF * sgn
    g = np.gcd(A, np.abs(Dp))
    g = np.gcd(g, np.abs(Ep))
    g = np.gcd(g, np.abs(Fp))
    g = np.where(g == 0, 1, g)
    return A // g, Dp // g, Ep // g, Fp // g


def uniq_keys(A, Dp, Ep, Fp):
    order = np.lexsort((Fp, Ep, Dp, A))
    A, Dp, Ep, Fp = A[order], Dp[order], Ep[order], Fp[order]
    new = np.ones(len(A), dtype=bool)
    new[1:] = ((A[1:] != A[:-1]) | (Dp[1:] != Dp[:-1])
               | (Ep[1:] != Ep[:-1]) | (Fp[1:] != Fp[:-1]))
    idx = np.flatnonzero(new)
    return A[idx], Dp[idx], Ep[idx], Fp[idx]


# ------------------------------------------------------------ circle record
def circle_geom(A: int, D: int, E: int, F: int):
    """centre (as Fraction), q = centre denominator, r2 = squared radius.

    The circle is stored as  A (x^2+y^2) = D x + E y + F ,  A > 0.
    centre = (D/(2A), E/(2A));  r^2 = (D^2 + E^2 + 4 A F) / (4 A^2).
    Also returns the canonical residue data used by round3_b451_analysis.py:
        g = gcd(2A, D, E),  q = 2A // g,  d = D // g,  e = E // g,
        M = (D^2 + E^2 + 4 A F) // g^2 = q^2 * r^2
    so that the lattice points are exactly the (u,v) with
        u^2 + v^2 = M,  u == -d (mod q),  v == -e (mod q)
    and  x = (u - alpha) / q,  y = (v - beta) / q  with (alpha,beta) = (-d,-e) mod q.
    """
    cx = Fraction(D, 2 * A)
    cy = Fraction(E, 2 * A)
    q = cx.denominator * cy.denominator // math.gcd(cx.denominator, cy.denominator)
    N = D * D + E * E + 4 * A * F
    r2 = Fraction(N, 4 * A * A)
    g = math.gcd(math.gcd(2 * A, abs(D)), abs(E))
    assert q == 2 * A // g, (q, A, D, E, g)
    assert N % (g * g) == 0
    return cx, cy, q, r2, g, N // (g * g)


def q_class(q: int) -> str:
    if q == 1:
        return "q1"
    if q == 2:
        return "q2"
    if q == 4:
        return "q4"
    if q % 2 == 0:
        return "q_even_other"
    if q == 3:
        return "q3"
    return "q_odd_ge5"


def factor_type(q: int) -> dict:
    v2 = 0
    t = q
    while t % 2 == 0:
        t //= 2
        v2 += 1
    p1, p3 = [], []
    p = 3
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


def extremes(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    return {
        "nL": sum(1 for x, y in pts if x == xmin),
        "nR": sum(1 for x, y in pts if x == xmax),
        "nB": sum(1 for x, y in pts if y == ymin),
        "nT": sum(1 for x, y in pts if y == ymax),
        "w": xmax - xmin + 1,
        "h": ymax - ymin + 1,
    }


def d4_orbit_size(pts):
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


# ------------------------------------------------------------------ census
def census(n: int, full_from: int = 5, chunk: int = 20000):
    t0 = time.time()
    N = n * n
    X = np.repeat(np.arange(n, dtype=np.int64), n)
    Y = np.tile(np.arange(n, dtype=np.int64), n)
    S = X * X + Y * Y
    I, J, K = triple_indices(N)
    t_tri = time.time() - t0

    t1 = time.time()
    A, D, E, F = circle_keys(X, Y, S, I, J, K)
    t_key = time.time() - t1
    A, D, E, F = uniq_keys(A, D, E, F)
    t_uniq = time.time() - t1 - t_key
    n_circles3 = len(A)

    t2 = time.time()
    rows = []
    idx_grid = np.arange(N, dtype=np.int64)
    for s in range(0, n_circles3, chunk):
        e = min(s + chunk, n_circles3)
        M = (A[s:e, None] * S[None, :]
             - D[s:e, None] * X[None, :]
             - E[s:e, None] * Y[None, :]
             - F[s:e, None]) == 0
        m = M.sum(axis=1)
        for t in np.flatnonzero(m >= 4):
            pts = [(int(X[i]), int(Y[i])) for i in idx_grid[M[t]]]
            rows.append((int(A[s + t]), int(D[s + t]), int(E[s + t]), int(F[s + t]), pts))
    t_scan = time.time() - t2

    recs = []
    for (a, d, e_, f, pts) in rows:
        cx, cy, q, r2, g, M = circle_geom(a, d, e_, f)
        ex = extremes(pts)
        recs.append({
            "A": a, "D": d, "E": e_, "F": f,
            "g": g, "M": M,
            "d_res": (-d) % q, "e_res": (-e_) % q,
            "m": len(pts), "q": q, "qclass": q_class(q),
            "cx": f"{cx.numerator}/{cx.denominator}",
            "cy": f"{cy.numerator}/{cy.denominator}",
            "r2": f"{r2.numerator}/{r2.denominator}",
            "bbox": [ex["w"], ex["h"]],
            "side": max(ex["w"], ex["h"]),
            "ext": [ex["nL"], ex["nR"], ex["nB"], ex["nT"]],
            "d4_orbit": d4_orbit_size(pts),
            "pts": [list(p) for p in pts],
        })
    recs.sort(key=lambda r: (-r["m"], r["side"], r["q"]))

    hist = {}
    for r in recs:
        hist[str(r["m"])] = hist.get(str(r["m"]), 0) + 1
    n_conc = sum(math.comb(r["m"], 4) for r in recs)

    dcol = collinear_c4(n)
    tot_forb = n_conc + dcol

    return {
        "n": n,
        "triples": int(len(I)),
        "n_circles_ge3": int(n_circles3),
        "n_circles_ge4": len(recs),
        "n_concyclic_quads": n_conc,
        "n_collinear_quads": dcol,
        "forbidden_total": tot_forb,
        "known_F_n": KNOWN_F.get(n),
        "F_match": (tot_forb == KNOWN_F[n]) if n in KNOWN_F else None,
        "m_hist": {k: hist[k] for k in sorted(hist, key=int)},
        "sum_check_C_m_4": n_conc,
        "M_n": max((r["m"] for r in recs), default=0),
        "records": recs,
        "timing_s": {"triples": t_tri, "keys": t_key, "uniq": t_uniq,
                     "membership_scan": t_scan, "total": time.time() - t0},
    }


def summarise(rec: dict, keep_from: int = 5):
    """Strip the heavy per-point data down to what goes into the JSON."""
    recs = rec["records"]
    out = {
        "n": rec["n"],
        "timing_s": rec["timing_s"],
        "triples": rec["triples"],
        "n_circles_ge3": rec["n_circles_ge3"],
        "n_circles_ge4": rec["n_circles_ge4"],
        "n_concyclic_quads": rec["n_concyclic_quads"],
        "n_collinear_quads": rec["n_collinear_quads"],
        "forbidden_total": rec["forbidden_total"],
        "known_F_n": rec["known_F_n"],
        "F_match": rec["F_match"],
        "m_hist": rec["m_hist"],
        "M_n": rec["M_n"],
    }
    by_q, quads_by_q = {}, {}
    by_mq, quads_by_mq = {}, {}
    for r in recs:
        w = math.comb(r["m"], 4)
        by_q[r["q"]] = by_q.get(r["q"], 0) + 1
        quads_by_q[r["q"]] = quads_by_q.get(r["q"], 0) + w
        by_mq.setdefault(r["q"], {})
        by_mq[r["q"]][str(r["m"])] = by_mq[r["q"]].get(str(r["m"]), 0) + 1
        quads_by_mq.setdefault(r["m"], {})
        quads_by_mq[r["m"]][str(r["q"])] = quads_by_mq[r["m"]].get(str(r["q"]), 0) + w
    out["circles_by_q"] = {str(k): by_q[k] for k in sorted(by_q)}
    out["quads_by_q"] = {str(k): quads_by_q[k] for k in sorted(quads_by_q)}
    out["circles_by_m_q"] = {str(q): {k: v for k, v in sorted(by_mq[q].items(), key=lambda kv: int(kv[0]))}
                             for q in sorted(by_mq)}
    out["quads_by_m_q"] = {str(m): {k: v for k, v in sorted(quads_by_mq[m].items())}
                           for m in sorted(quads_by_mq)}
    # distinct shapes among circles with m >= keep_from
    shapes = {}
    for r in recs:
        if r["m"] < keep_from:
            continue
        key = (r["m"], tuple(map(tuple, r["pts"])))
        if key not in shapes:
            shapes[key] = r
    out["n_shapes_m_ge%d" % keep_from] = len(shapes)
    out["rows_m_ge%d" % keep_from] = [
        {k: v for k, v in r.items()} for r in recs if r["m"] >= keep_from]
    # all q>=3 circles (these are the rare ones the B451-B457 batch is about)
    out["rows_q_ge3"] = [r for r in recs if r["q"] >= 3]
    out["n_rows_q_ge3"] = len(out["rows_q_ge3"])
    # best (largest) circle per (m, q-class)
    best = {}
    for r in recs:
        k = (r["m"], r["qclass"])
        if k not in best or r["side"] < best[k]["side"]:
            best[k] = r
    out["best_per_m_qclass"] = sorted(
        ({"m": k[0], "qclass": k[1], "q": v["q"], "side": v["side"],
          "bbox": v["bbox"], "r2": v["r2"], "cx": v["cx"], "cy": v["cy"],
          "d4": v["d4_orbit"], "ext": v["ext"]} for k, v in best.items()),
        key=lambda r: (r["qclass"], r["m"]))
    return out


def brute_force_circles(n: int):
    """Independent, deliberately naive census: C(n^2,4) 4-subsets, det test,
    group by the circumcircle of the lexicographically first triple."""
    import itertools
    pts = [(x, y) for y in range(n) for x in range(n)]
    N = n * n
    rows = [(x * x + y * y, x, y, 1) for x, y in pts]

    def det4(r):
        def det3(m):
            return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
                    - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
                    + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
        R = [list(t) for t in r]
        return (R[0][0] * det3([t[1:] for t in R[1:]])
                - R[0][1] * det3([[R[i][0]] + R[i][2:] for i in (1, 2, 3)])
                + R[0][2] * det3([[R[i][0], R[i][1], R[i][3]] for i in (1, 2, 3)])
                - R[0][3] * det3([t[:3] for t in R[1:]]))

    def key(i, j, k):
        s1, x1, y1, _u1 = rows[i]
        s2, x2, y2, _u2 = rows[j]
        s3, x3, y3, _u3 = rows[k]
        det = x1 * (y2 - y3) - y1 * (x2 - x3) + (x2 * y3 - x3 * y2)
        if det == 0:
            return None
        b1, b2, b3 = -s1, -s2, -s3
        nD = b1 * (y2 - y3) - y1 * (b2 - b3) + (b2 * y3 - b3 * y2)
        nE = x1 * (b2 - b3) - b1 * (x2 - x3) + (x2 * b3 - x3 * b2)
        nF = (x1 * (y2 * b3 - y3 * b2) - y1 * (x2 * b3 - x3 * b2)
              + b1 * (x2 * y3 - x3 * y2))
        sg = 1 if det > 0 else -1
        a, dd, ee, ff = det * sg, -nD * sg, -nE * sg, -nF * sg
        g = math.gcd(math.gcd(math.gcd(a, abs(dd)), abs(ee)), abs(ff))
        return (a // g, dd // g, ee // g, ff // g)

    circles = {}
    for q4 in itertools.combinations(range(N), 4):
        r = [rows[t] for t in q4]
        if det4(r) != 0:
            continue
        kk = None
        for tri in itertools.combinations(q4, 3):
            kk = key(*tri)
            if kk is not None:
                break
        if kk is None:
            continue
        circles.setdefault(kk, set()).update(q4)
    return circles


def main():
    out = {"generated": "round3_b451_census", "boards": {}, "validation": {}}
    t0 = time.time()
    for n in (4, 5, 6, 7, 8, 9, 10, 11, 12):
        rec = census(n)
        out["boards"][str(n)] = summarise(rec)
        b = out["boards"][str(n)]
        print(f"n={n:2d} triples={b['triples']:>9d} circ>=3={b['n_circles_ge3']:>8d} "
              f"circ>=4={b['n_circles_ge4']:>7d} conc={b['n_concyclic_quads']:>7d} "
              f"coll={b['n_collinear_quads']:>6d} F={b['forbidden_total']:>7d} "
              f"match={b['F_match']} M={b['M_n']} q>=3={b['n_rows_q_ge3']:>4d} "
              f"t={b['timing_s']['total']:.1f}s", flush=True)

    # ---- validation against the pre-existing exploration facts ----
    for fn in ("fact_circle_spectrum_n6_n7_n11.json",
               "fact_circle_spectrum_n8_n9_n10.json",
               "fact_circle_families_k10_k12.json"):
        p = EXPL / fn
        if not p.exists():
            continue
        ref = json.loads(p.read_text(encoding="utf-8"))
        for row in ref:
            if "board" in row:
                n = int(row["board"].split("x")[0])
                b = out["boards"].get(str(n))
                if not b:
                    continue
                got_hist = b["m_hist"]
                out["validation"][f"{fn}:{row['board']}:m_hist"] = {
                    "reference": row["circle_lattice_size_hist"],
                    "computed": got_hist,
                    "match": {str(k): int(v) for k, v in row["circle_lattice_size_hist"].items()}
                            == {str(k): int(v) for k, v in got_hist.items()},
                }
                out["validation"][f"{fn}:{row['board']}:counts"] = {
                    "unique_circles_ref": row["unique_circles"],
                    "unique_circles_got": b["n_circles_ge4"],
                    "concyclic_ref": row["concyclic_quads"],
                    "concyclic_got": b["n_concyclic_quads"],
                    "collinear_ref": row["collinear_quads"],
                    "collinear_got": b["n_collinear_quads"],
                    "match": (row["unique_circles"] == b["n_circles_ge4"]
                              and row["concyclic_quads"] == b["n_concyclic_quads"]
                              and row["collinear_quads"] == b["n_collinear_quads"]),
                }
            else:
                n, k = row["n"], row["k"]
                b = out["boards"].get(str(n))
                if not b:
                    continue
                got = [r for r in b["rows_m_ge%d" % 5] if r["m"] == k]
                got_hist = {}
                for r in b["rows_m_ge%d" % 5]:
                    if r["m"] == k:
                        got_hist[r["r2"]] = got_hist.get(r["r2"], 0) + 1
                out["validation"][f"{fn}:n{n}k{k}"] = {
                    "reference_count": row["count"],
                    "reference_r2_hist": row["r2_hist"],
                    "computed_count": len(got),
                    "computed_r2_hist": got_hist,
                    "match": len(got) == row["count"],
                }

    # ---- independent cross-check: naive C(n^2,4) brute force for n = 4..9 ----
    for n in (4, 5, 6, 7, 8, 9):
        tbf = time.time()
        bf = brute_force_circles(n)
        b = out["boards"].get(str(n))
        if b is None:
            continue
        bf_hist = {}
        for pts in bf.values():
            k = str(len(pts))
            bf_hist[k] = bf_hist.get(k, 0) + 1
        bf_hist = {k: bf_hist[k] for k in sorted(bf_hist, key=int)}
        fast_hist = b["m_hist"]
        out["validation"][f"bruteforce_n{n}"] = {
            "n_circles_bruteforce": len(bf),
            "m_hist_bruteforce": bf_hist,
            "n_circles_fast": b["n_circles_ge4"],
            "m_hist_fast": b["m_hist"],
            "seconds": round(time.time() - tbf, 2),
            "match": len(bf) == b["n_circles_ge4"] and bf_hist == b["m_hist"],
        }
        print(f"  brute-force n={n}: {len(bf)} circles, {bf_hist} "
              f"match={out['validation'][f'bruteforce_n{n}']['match']} "
              f"({round(time.time() - tbf, 1)}s)", flush=True)

    out["total_runtime_s"] = time.time() - t0
    bad = [k for k, v in out["validation"].items() if isinstance(v, dict) and v.get("match") is False]
    out["all_validations_pass"] = not bad
    out["failed_validations"] = bad
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print("validation failures:", bad)
    print("total runtime", round(out["total_runtime_s"], 1), "s ->", OUT)


if __name__ == "__main__":
    main()
