#!/usr/bin/env python3
"""Round5 B142: circle-grouping count of C_n + degree analysis.

Methods:
  A) Circle grouping: enumerate unique circles with >=4 grid points, sum C(k,4),
     subtract collinear C(r,4) contributions to get non-collinear concyclic count.
  B) Closed-form D_n and KNOWN_F for cross-check.
  C) Ratio analysis: C/n^5, C/(n^5 log n), C/n^6 and local degree.
"""
from __future__ import annotations

import itertools
import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification"
JSON_OUT = OUT / "round5_b142_data.json"

KNOWN_F = {
    2: 1, 3: 14, 4: 194, 5: 826, 6: 2491, 7: 6364,
    8: 14564, 9: 29152, 10: 54441, 11: 95670, 12: 158426,
}


def det4(p, q, r, s):
    """Integer determinant det[[x^2+y^2, x, y, 1]] for 4 points. 0 iff concyclic/collinear."""
    def row(pt):
        x, y = pt
        return [x * x + y * y, x, y, 1]
    m = [row(p), row(q), row(r), row(s)]
    total = 0
    for i in range(4):
        mm = []
        for r2 in range(4):
            if r2 == i:
                continue
            mm.append(m[r2][1:])
        d3 = (mm[0][0] * (mm[1][1] * mm[2][2] - mm[1][2] * mm[2][1])
              - mm[0][1] * (mm[1][0] * mm[2][2] - mm[1][2] * mm[2][0])
              + mm[0][2] * (mm[1][0] * mm[2][1] - mm[1][1] * mm[2][0]))
        total += (1 if i % 2 == 0 else -1) * m[i][0] * d3
    return total


def is_collinear(p, q, r):
    return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]) == 0


def collinear_c4(n: int) -> int:
    """Sum over primitive directions of C(run_length, 4)."""
    pts = [(x, y) for y in range(n) for x in range(n)]
    S = set(pts)
    total = 0
    for dx in range(0, n):
        for dy in range(-n + 1, n):
            if dx == 0 and dy != 1:
                continue
            if dx > 0 and math.gcd(dx, abs(dy)) != 1:
                continue
            seen = set()
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


def circle_params(p, q, r):
    """Return integer circle key (A,B,C,D) for A(x^2+y^2)+Bx+Cy+D=0, or None if collinear."""
    ax, ay = p
    bx, by = q
    cx, cy = r
    # 2x the signed area
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if d == 0:
        return None
    a2 = ax * ax + ay * ay
    b2 = bx * bx + by * by
    c2 = cx * cx + cy * cy
    ux = a2 * (by - cy) + b2 * (cy - ay) + c2 * (ay - by)
    uy = a2 * (cx - bx) + b2 * (ax - cx) + c2 * (bx - ax)
    # Circle: (d*x - ux)^2 + (d*y - uy)^2 = (ux^2 + uy^2 - a2*d*? ...)
    # Simpler: use the determinant form. Circle through 3 pts:
    # A(x^2+y^2) + Bx + Cy + D = 0
    # where (A,B,C,D) = cofactors of the 4x4 matrix with rows [x^2+y^2, x, y, 1]
    # For 3 points, we get a 3x3 system. Let's use:
    # The circumcircle equation can be written as:
    # |x^2+y^2  x  y  1|
    # |p2       px py 1| = 0
    # |q2       qx qy 1|
    # |r2       rx ry 1|
    # Expanding along the first row gives A(x^2+y^2)+Bx+Cy+D=0 with (A,B,C,D) from cofactors.
    m = [
        [a2, ax, ay, 1],
        [b2, bx, by, 1],
        [c2, cx, cy, 1],
    ]
    # Cofactors of a 3x4... actually we need the 4x4 determinant's cofactors.
    # Build the 3x3 minors obtained by deleting column j from the 3x4 matrix [a2 ax ay 1; ...]
    # Wait, the standard approach: the circle is det([[x^2+y^2,x,y,1],[p],[q],[r]])=0
    # Expanding along first row: A(x^2+y^2) + B*x + C*y + D*1 = 0
    # where A = det([px py 1; qx qy 1; rx ry 1])  (delete col 0)
    #       B = -det([p2 py 1; q2 qy 1; r2 ry 1]) (delete col 1)
    #       C = det([p2 px 1; q2 qx 1; r2 rx 1])  (delete col 2)
    #       D = -det([p2 px py; q2 qx qy; r2 rx ry]) (delete col 3)
    def det3(r0, r1, r2):
        return (r0[0] * (r1[1] * r2[2] - r1[2] * r2[1])
                - r0[1] * (r1[0] * r2[2] - r1[2] * r2[0])
                + r0[2] * (r1[0] * r2[1] - r1[1] * r2[0]))

    A = det3([ax, ay, 1], [bx, by, 1], [cx, cy, 1])
    B = -det3([a2, ay, 1], [b2, by, 1], [c2, cy, 1])
    C = det3([a2, ax, 1], [b2, bx, 1], [c2, cx, 1])
    D = -det3([a2, ax, ay], [b2, bx, by], [c2, cx, cy])
    if A == 0 and B == 0 and C == 0:
        return None  # degenerate (collinear)
    # Normalize sign so first nonzero is positive
    vals = [A, B, C, D]
    for v in vals:
        if v != 0:
            if v < 0:
                A, B, C, D = -A, -B, -C, -D
            break
    # Reduce by gcd
    g = 0
    for v in (A, B, C, D):
        g = math.gcd(g, abs(v))
    if g > 1:
        A, B, C, D = A // g, B // g, C // g, D // g
    return (A, B, C, D)


def on_circle(pt, key):
    A, B, C, D = key
    x, y = pt
    return A * (x * x + y * y) + B * x + C * y + D == 0


def Cn_circle_grouping(n: int) -> dict:
    """Count non-collinear concyclic 4-sets via circle grouping."""
    pts = [(x, y) for y in range(n) for x in range(n)]
    V = n * n
    circs = {}
    for i, j, k in itertools.combinations(range(V), 3):
        p, q, r = pts[i], pts[j], pts[k]
        if is_collinear(p, q, r):
            continue
        key = circle_params(p, q, r)
        if key is None or key in circs:
            continue
        on = [idx for idx in range(V) if on_circle(pts[idx], key)]
        if len(on) >= 4:
            circs[key] = on
    total_conc = 0
    total_coll_in_circles = 0
    circle_sizes = Counter()
    for key, on in circs.items():
        k = len(on)
        circle_sizes[k] += 1
        total_conc += math.comb(k, 4)
        # Subtract collinear 4-sets that also lie on this "circle" (degenerate lines)
        # Actually our keys with A!=0 are true circles; A==0 would be lines.
        # We skipped collinear triples, so all keys should have A!=0.
        # But 4 collinear points also satisfy det=0; they lie on a "circle of infinite radius".
        # Since we only generated circles from non-collinear triples, collinear 4-sets
        # are NOT included in total_conc. Wait — actually 4 collinear points DO satisfy
        # the circle equation A(x^2+y^2)+Bx+Cy+D=0 with A=0 (a line). We skip A=0.
        # But can 4 collinear points also lie on a true circle? Only if the circle degenerates.
        # So total_conc should already be non-collinear concyclic. Let's verify.
    # Double-check: count collinear 4-sets that happen to be in some circle's on-list
    # (should be 0 if A!=0 circles don't contain 4 collinear pts — they can contain
    # at most 2 points of any line, since a line and circle intersect in <=2 pts).
    # So total_conc = C_n directly.
    return {
        "C_n": total_conc,
        "n_circles": len(circs),
        "circle_sizes": dict(circle_sizes),
    }


def Cn_direct(n: int) -> dict:
    """Direct 4-tuple enumeration (slow for n>8, use only for cross-check)."""
    pts = [(x, y) for y in range(n) for x in range(n)]
    V = n * n
    F = 0
    D = 0
    for comb in itertools.combinations(range(V), 4):
        p, q, r, s = [pts[i] for i in comb]
        if is_collinear(p, q, r) and is_collinear(p, q, s):
            D += 1
            F += 1
            continue
        if det4(p, q, r, s) == 0:
            F += 1
    return {"F_n": F, "D_n": D, "C_n": F - D}


def main():
    report = {"known_F": KNOWN_F}
    print("=== D_n closed form + KNOWN_F → C_n ===", flush=True)
    cn_from_known = {}
    for n in range(2, 13):
        dn = collinear_c4(n)
        fn = KNOWN_F.get(n)
        cn = (fn - dn) if fn else None
        cn_from_known[n] = cn
        if cn is not None:
            print(f"  n={n:2d}  D={dn:6d}  F={fn:6d}  C={cn:6d}", flush=True)
    report["cn_from_known"] = cn_from_known

    print("\n=== Circle-grouping C_n (independent method) ===", flush=True)
    cn_circles = {}
    for n in range(3, 11):
        res = Cn_circle_grouping(n)
        cn_circles[n] = res
        match = cn_from_known.get(n)
        flag = ""
        if match is not None:
            flag = " OK" if res["C_n"] == match else f" MISMATCH (known={match})"
        print(f"  n={n:2d}  C_circ={res['C_n']:6d}  n_circles={res['n_circles']:4d}  sizes={res['circle_sizes']}{flag}", flush=True)
    report["cn_circles"] = cn_circles

    print("\n=== Direct det4 (small n cross-check) ===", flush=True)
    cn_direct = {}
    for n in range(3, 8):
        res = Cn_direct(n)
        cn_direct[n] = res
        match = cn_from_known.get(n)
        flag = ""
        if match is not None:
            flag = " OK" if res["C_n"] == match else f" MISMATCH (known={match})"
        print(f"  n={n:2d}  F={res['F_n']:6d}  D={res['D_n']:6d}  C={res['C_n']:6d}{flag}", flush=True)
    report["cn_direct"] = cn_direct

    # Ratio analysis
    print("\n=== Ratio analysis (using best C_n) ===", flush=True)
    best_cn = {}
    for n in range(2, 13):
        if n in cn_circles and n >= 3:
            best_cn[n] = cn_circles[n]["C_n"]
        elif n in cn_from_known and cn_from_known[n] is not None:
            best_cn[n] = cn_from_known[n]
    rows = []
    print(f"  {'n':>3} {'C_n':>8} {'C/n5':>10} {'C/(n5ln)':>10} {'C/n6':>10} {'local_deg':>10}", flush=True)
    for n in sorted(best_cn):
        c = best_cn[n]
        n5 = n ** 5
        n5log = n5 * math.log(n)
        n6 = n ** 6
        ld = None
        if n > 2 and (n - 1) in best_cn and best_cn[n - 1] > 0:
            ld = math.log(c / best_cn[n - 1]) / math.log(n / (n - 1))
        row = {
            "n": n, "C": c,
            "C_over_n5": c / n5,
            "C_over_n5logn": c / n5log,
            "C_over_n6": c / n6,
            "local_degree": ld,
        }
        rows.append(row)
        ld_s = f"{ld:.4f}" if ld is not None else "     —"
        print(f"  {n:3d} {c:8d} {c/n5:10.6f} {c/n5log:10.6f} {c/n6:10.6f} {ld_s:>10}", flush=True)
    report["ratio_rows"] = rows

    # Fit degree on n=6..12
    ns = [r["n"] for r in rows if r["n"] >= 6]
    cs = [r["C"] for r in rows if r["n"] >= 6]
    if len(ns) >= 3:
        # log-log linear regression: log C = alpha * log n + beta
        import statistics
        xs = [math.log(n) for n in ns]
        ys = [math.log(c) for c in cs]
        npts = len(xs)
        sx = sum(xs); sy = sum(ys)
        sxx = sum(x * x for x in xs); sxy = sum(x * y for x, y in zip(xs, ys))
        alpha = (npts * sxy - sx * sy) / (npts * sxx - sx * sx)
        print(f"\n  log-log fit n=6..12: degree ≈ {alpha:.4f}", flush=True)
        report["loglog_degree_n6_12"] = alpha

        # Also fit n=4..12
        ns2 = [r["n"] for r in rows]
        cs2 = [r["C"] for r in rows]
        xs2 = [math.log(n) for n in ns2]
        ys2 = [math.log(c) for c in cs2]
        npts2 = len(xs2)
        sx2 = sum(xs2); sy2 = sum(ys2)
        sxx2 = sum(x * x for x in xs2); sxy2 = sum(x * y for x, y in zip(xs2, ys2))
        alpha2 = (npts2 * sxy2 - sx2 * sy2) / (npts2 * sxx2 - sx2 * sx2)
        print(f"  log-log fit n=4..12: degree ≈ {alpha2:.4f}", flush=True)
        report["loglog_degree_n4_12"] = alpha2

    JSON_OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nWrote {JSON_OUT}", flush=True)


if __name__ == "__main__":
    main()
