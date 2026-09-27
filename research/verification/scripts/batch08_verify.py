#!/usr/bin/env python3
"""Batch 08 verification: B141-B180.

Computes:
  A) D_n collinear closed form (n=2..20), C_n = F_n - D_n for known F_n
  B) point degrees d(p) and pairwise d(p,q) for small n
  C) rectangle counts R_n (all orientations) for n<=8
  D) checkerboard / mod patterns of concyclic quads
  E) f-vector log-concavity from known depth profiles
"""
from __future__ import annotations

import itertools
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research" / "verification"


# ---------- A) collinear closed form ----------
def collinear_c4(n: int) -> tuple[int, dict]:
    """Sum over primitive directions of C(run_length, 4). Returns total and by-dir."""
    pts = [(x, y) for y in range(n) for x in range(n)]
    S = set(pts)
    by_dir = Counter()
    for dx in range(0, n):
        for dy in range(-n + 1, n):
            if dx == 0 and dy <= 0:
                continue
            if dx > 0 and math.gcd(dx, abs(dy)) != 1:
                continue
            if dx == 0 and dy != 1:
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
                    by_dir[(dx, dy)] += math.comb(L, 4)
    return sum(by_dir.values()), {f"{a},{b}": int(v) for (a, b), v in sorted(by_dir.items())}


def collinear_c4_dir(n: int, dx: int, dy: int) -> tuple[int, dict]:
    """Collinear 4-sets contributed by a single primitive direction (dx,dy)."""
    if dx < 0 or (dx == 0 and dy <= 0):
        # normalize to canonical primitive direction
        if dx < 0 or (dx == 0 and dy < 0):
            dx, dy = -dx, -dy
    if dx == 0 and dy != 1:
        return 0, {}
    if dx > 0 and math.gcd(dx, abs(dy)) != 1:
        return 0, {}
    pts = [(x, y) for y in range(n) for x in range(n)]
    S = set(pts)
    by_dir = Counter()
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
            by_dir[(dx, dy)] += math.comb(L, 4)
    return sum(by_dir.values()), {f"{a},{b}": int(v) for (a, b), v in by_dir.items()}


# ---------- forbidden enumeration ----------
def det4(p, q, r, s):
    """Integer det of rows [x^2+y^2, x, y, 1]."""
    pts = (p, q, r, s)
    A = [[x * x + y * y, x, y, 1] for x, y in pts]

    def det3(m):
        return (
            m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
        )

    return (
        A[0][0] * det3([row[1:] for row in A[1:]])
        - A[0][1] * det3([[A[i][0]] + A[i][2:] for i in (1, 2, 3)])
        + A[0][2] * det3([[A[i][0], A[i][1], A[i][3]] for i in (1, 2, 3)])
        - A[0][3] * det3([row[:3] for row in A[1:]])
    )


def is_collinear(p, q, r):
    return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]) == 0


def forbidden_quads(n: int):
    """Return list of 4-tuples (as point-id tuples) that are collinear or concyclic."""
    pts = [(i % n, i // n) for i in range(n * n)]
    out = []
    for comb in itertools.combinations(range(n * n), 4):
        p, q, r, s = [pts[i] for i in comb]
        if is_collinear(p, q, r) and is_collinear(p, q, s):
            out.append(comb)
            continue
        if det4(p, q, r, s) == 0:
            out.append(comb)
    return out


# ---------- B) degrees ----------
def degree_stats(n: int, quads):
    deg = [0] * (n * n)
    pair = defaultdict(int)
    for q in quads:
        for p in q:
            deg[p] += 1
        for i in range(4):
            for j in range(i + 1, 4):
                pair[(q[i], q[j])] += 1
    return deg, pair


# ---------- C) rectangles via centers ----------
def rectangle_count(n: int) -> dict:
    """Count rectangles with vertices on the n x n grid (any orientation).

    A rectangle is determined by its center m and two diameters of its
    circumcircle. For each half-integer center m inside/near the board and
    each squared-distance, collect lattice points; antipodal pairs are
    diameters; C(#diameters, 2) = rectangles at that radius.
    """
    pts = [(x, y) for y in range(n) for x in range(n)]
    total = 0
    axis_aligned = math.comb(n, 2) ** 2
    # centers (i2/2, j2/2) with i2,j2 covering board
    for i2 in range(-1, 2 * n):
        for j2 in range(-1, 2 * n):
            # group points by squared distance * 4
            dist_pts = defaultdict(list)
            for x, y in pts:
                d4 = (2 * x - i2) ** 2 + (2 * y - j2) ** 2
                if d4 == 0:
                    continue
                dist_pts[d4].append((x, y))
            for d4, on in dist_pts.items():
                # antipodal pairs: p and (i2-x, j2-y)  [both coords in 2x scale]
                # a diameter is {p, q} with q = (i2 - 2*x_of_p /2 ...]
                # p=(x,y), antipode = (i2/2 - (x - i2/2), ...) = (i2 - x, j2 - y)  (integers)
                onset = set(on)
                diam = 0
                used = set()
                for x, y in on:
                    if (x, y) in used:
                        continue
                    ax, ay = i2 - x, j2 - y
                    if (ax, ay) in onset and (ax, ay) != (x, y):
                        diam += 1
                        used.add((x, y))
                        used.add((ax, ay))
                    elif (ax, ay) == (x, y):
                        pass  # center is the point itself — impossible since d4>0
                total += math.comb(diam, 2)
    return {
        "n": n,
        "rectangles_total": total,
        "axis_aligned": axis_aligned,
        "rotated": total - axis_aligned,
        "rect_over_c4_estimate": None,
    }


# ---------- D) checkerboard patterns ----------
def parity_pattern(quads, pts):
    """Classify each quad by multiset of (x%2, y%2) types and (x+y)%2."""
    type_names = {(0, 0): "00", (0, 1): "01", (1, 0): "10", (1, 1): "11"}
    by_xy = Counter()
    by_sum = Counter()
    for q in quads:
        types = tuple(sorted(type_names[(pts[i][0] % 2, pts[i][1] % 2)] for i in q))
        by_xy[str(types)] += 1
        sums = tuple(sorted((pts[i][0] + pts[i][1]) % 2 for i in q))
        by_sum[str(sums)] += 1
    return dict(by_xy), dict(by_sum)


def center_denom_hist(n: int, quads, pts):
    """For concyclic quads, classify circle center denominator: integer / half-int / other."""
    hist = Counter()
    for q in quads:
        p0, p1, p2 = [pts[i] for i in q[:3]]
        ax, ay = p0
        bx, by = p1
        cx, cy = p2
        d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        if d == 0:
            hist["collinear"] += 1
            continue
        a2 = ax * ax + ay * ay
        b2 = bx * bx + by * by
        c2 = cx * cx + cy * cy
        ux = a2 * (by - cy) + b2 * (cy - ay) + c2 * (ay - by)
        uy = a2 * (cx - bx) + b2 * (ax - cx) + c2 * (bx - ax)
        # center = (ux/d, uy/d)
        g1 = math.gcd(ux, d) if d else 1
        g2 = math.gcd(uy, d) if d else 1
        # reduced denominators
        dd = abs(d)
        den_x = dd // math.gcd(abs(ux), dd) if dd else 1
        den_y = dd // math.gcd(abs(uy), dd) if dd else 1
        den = math.lcm(den_x, den_y)
        if den == 1:
            hist["integer"] += 1
        elif den == 2:
            hist["half"] += 1
        else:
            hist[f"den{den}"] += 1
    return dict(hist)


# ---------- E) f-vector checks ----------
FVEC = {
    2: [1, 4, 6, 4],
    3: [1, 9, 36, 84, 112, 56],
    4: [1, 16, 120, 560, 1626, 2360, 1064, 64],
    5: [1, 25, 300, 2300, 11824, 37272, 59192, 35208, 5172, 100],
}


def fvec_checks():
    out = {}
    for n, f in FVEC.items():
        uni = all(f[i] <= f[i + 1] for i in range(len(f) - 1) if f[i] > 0 and f[i + 1] > 0 and i < f.index(max(f)))
        # proper unimodal: one peak
        peak = f.index(max(f))
        unimodal = all(f[i] <= f[i + 1] for i in range(peak)) and all(f[i] >= f[i + 1] for i in range(peak, len(f) - 1))
        logc = []
        logc_ok = True
        for k in range(1, len(f) - 1):
            lhs = f[k] * f[k]
            rhs = f[k - 1] * f[k + 1]
            ok = lhs >= rhs
            logc.append({"k": k, "f_k2": lhs, "f_{k-1}f_{k+1}": rhs, "ok": ok})
            if not ok:
                logc_ok = False
        # safe probability a_k = f_k / C(n^2, k)
        N = n * n
        a = [f[k] / math.comb(N, k) for k in range(len(f))]
        a_logc = []
        a_ok = True
        for k in range(1, len(a) - 1):
            lhs = a[k] * a[k]
            rhs = a[k - 1] * a[k + 1]
            ok = lhs >= rhs - 1e-18
            a_logc.append({"k": k, "ratio": (lhs / rhs if rhs > 0 else None), "ok": ok})
            if not ok:
                a_ok = False
        out[n] = {
            "f": f,
            "peak_k": peak,
            "unimodal": unimodal,
            "log_concave": logc_ok,
            "log_concave_detail": logc,
            "prob_log_concave": a_ok,
            "prob_log_detail": a_logc,
        }
    return out


KNOWN_F = {
    2: 1, 3: 14, 4: 194, 5: 826, 6: 2491, 7: 6364,
    8: 14564, 9: 29152, 10: 54441, 11: 95670, 12: 158426,
}


def main():
    report = {}

    # ---- A) D_n growth ----
    print("=== A) collinear D_n closed form ===", flush=True)
    dn = {}
    for n in range(2, 21):
        t, by = collinear_c4(n)
        dn[n] = t
        fn = KNOWN_F.get(n)
        cn = (fn - t) if fn else None
        print(f"  n={n:2d} D={t:6d}  D/n^5={t/n**5:.5f}  D/n^6={t/n**6:.5f}"
              + (f"  F={fn} C={cn}  D/F={t/fn:.4f}" if fn else ""), flush=True)
    report["D_n"] = dn
    report["D_growth"] = {
        str(n): {
            "D": dn[n],
            "D_over_n5": dn[n] / n ** 5,
            "D_over_n6": dn[n] / n ** 6,
            "F": KNOWN_F.get(n),
            "C": (KNOWN_F[n] - dn[n]) if n in KNOWN_F else None,
            "D_over_F": (dn[n] / KNOWN_F[n]) if n in KNOWN_F else None,
            "C_over_n6": ((KNOWN_F[n] - dn[n]) / n ** 6) if n in KNOWN_F else None,
        }
        for n in range(2, 21)
    }

    # ---- B/C/D) small-n forbidden enumeration ----
    print("\n=== B) degrees / C) rectangles / D) parity ===", flush=True)
    small = {}
    for n in range(2, 8):
        print(f"  n={n} enumerating forbidden...", flush=True)
        quads = forbidden_quads(n)
        pts = [(i % n, i // n) for i in range(n * n)]
        deg, pair = degree_stats(n, quads)
        # classify collinear vs concyclic
        coll = [q for q in quads if all(is_collinear(pts[q[0]], pts[q[1]], pts[q[i]]) for i in (2, 3))]
        conc = [q for q in quads if q not in set(coll)]
        conc_set = [q for q in quads if not (is_collinear(pts[q[0]], pts[q[1]], pts[q[2]]) and is_collinear(pts[q[0]], pts[q[1]], pts[q[3]]))]
        # checkerboard
        xy_pat, sum_pat = parity_pattern(conc_set, pts)
        cen = center_denom_hist(n, conc_set, pts)
        # min/max degree locations
        mn, mx = min(deg), max(deg)
        min_pts = [i for i, d in enumerate(deg) if d == mn]
        max_pts = [i for i, d in enumerate(deg) if d == mx]
        corner00 = deg[0]  # (0,0)
        center_id = (n // 2) * n + (n // 2)
        # pair degree: sample interesting pairs
        pair_items = sorted(pair.items(), key=lambda kv: kv[1])
        small[n] = {
            "forbidden": len(quads),
            "published": KNOWN_F.get(n),
            "match": len(quads) == KNOWN_F.get(n),
            "n_collinear": len(coll),
            "n_concyclic": len(conc_set),
            "deg_min": mn,
            "deg_max": mx,
            "deg_mean": sum(deg) / len(deg),
            "deg_corner00": corner00,
            "deg_center": deg[center_id] if n >= 2 else None,
            "deg_min_is_corner": 0 in min_pts,
            "min_pts": min_pts[:12],
            "max_pts": max_pts[:12],
            "max_is_center": center_id in max_pts,
            "deg_by_xy": {
                f"({i%n},{i//n})": deg[i] for i in range(n * n)
            },
            "parity_xy_hist": xy_pat,
            "parity_sum_hist": sum_pat,
            "center_denom": cen,
            "pair_deg_min": pair_items[0][1] if pair_items else None,
            "pair_deg_max": pair_items[-1][1] if pair_items else None,
            "pair_deg_mean": (sum(v for _, v in pair_items) / len(pair_items)) if pair_items else None,
            "n_distinct_pair_deg": len(set(v for _, v in pair_items)),
        }
        # pair-degree sensitivity to primitive direction & gcd (B155)
        # bucket pairs by (length^2, gcd, slope-reduced)
        buckets = defaultdict(list)
        for (i, j), d in pair.items():
            x1, y1 = pts[i]
            x2, y2 = pts[j]
            dx, dy = x2 - x1, y2 - y1
            g = math.gcd(abs(dx), abs(dy)) if (dx or dy) else 1
            L2 = dx * dx + dy * dy
            # primitive direction
            pdx, pdy = (dx // g, dy // g) if g else (0, 0)
            buckets[(L2, g)].append(d)
            buckets[("slope", pdx, pdy)].append(d)
        # variance within same L2 vs explained by (L2,g)
        same_L2 = defaultdict(list)
        same_L2g = defaultdict(list)
        for (i, j), d in pair.items():
            x1, y1 = pts[i]
            x2, y2 = pts[j]
            dx, dy = x2 - x1, y2 - y1
            g = math.gcd(abs(dx), abs(dy)) if (dx or dy) else 1
            L2 = dx * dx + dy * dy
            same_L2[L2].append(d)
            same_L2g[(L2, g)].append(d)

        def spread(dmap):
            outv = []
            for k, vs in dmap.items():
                if len(vs) >= 2:
                    outv.append({"key": str(k), "min": min(vs), "max": max(vs),
                                 "spread": max(vs) - min(vs), "count": len(vs)})
            return sorted(outv, key=lambda t: -t["spread"])[:8]

        small[n]["pair_spread_by_L2"] = spread(same_L2)
        small[n]["pair_spread_by_L2_g"] = spread(same_L2g)

        # B156 formula check: d(p,q) == C(kline-2,2) + sum_circles C(|C|-2,2)
        # brute-force pair degrees already in `pair`; verify a few pairs via formula
        small[n]["pair_sample"] = [
            {"p": list(pts[a]), "q": list(pts[b]), "d_pq": v}
            for (a, b), v in sorted(pair.items(), key=lambda kv: -kv[1])[:6]
        ]
        small[n]["pair_sample_low"] = [
            {"p": list(pts[a]), "q": list(pts[b]), "d_pq": v}
            for (a, b), v in sorted(pair.items(), key=lambda kv: kv[1])[:6]
        ]
        print(f"    F={len(quads)} coll={len(coll)} conc={len(conc_set)} "
              f"deg [{mn},{mx}] corner={corner00} center={deg[center_id]} "
              f"min_at_corner={0 in min_pts} max_at_center={center_id in max_pts}", flush=True)

    report["small_boards"] = small

    # ---- C) rectangles ----
    print("\n=== C) rectangles ===", flush=True)
    rects = {}
    for n in range(2, 9):
        r = rectangle_count(n)
        rects[n] = r
        print(f"  n={n}: total={r['rectangles_total']} axis={r['axis_aligned']} rot={r['rotated']}", flush=True)
    report["rectangles"] = rects

    # ---- E) f-vector ----
    print("\n=== E) f-vector ===", flush=True)
    fv = fvec_checks()
    for n, v in fv.items():
        print(f"  n={n}: peak_k={v['peak_k']} unimodal={v['unimodal']} "
              f"logc={v['log_concave']} prob_logc={v['prob_log_concave']}", flush=True)
    report["f_vector"] = fv

    # ---- similarity-type compression (B149) quick probe ----
    # Represent each forbidden quad by its D4-normalized sorted edge-length multiset
    # (a crude similarity invariant). Count how many quads fall into top-10 types.
    print("\n=== B149 similarity-type compression probe ===", flush=True)
    sim = {}
    for n in range(2, 7):
        quads = forbidden_quads(n)
        pts = [(i % n, i // n) for i in range(n * n)]
        types = Counter()
        for q in quads:
            P = [pts[i] for i in q]
            # all pairwise squared distances
            ds = []
            for i in range(4):
                for j in range(i + 1, 4):
                    dx = P[i][0] - P[j][0]
                    dy = P[i][1] - P[j][1]
                    ds.append(dx * dx + dy * dy)
            # normalize by gcd of distances (scale-invariant similarity)
            g = 0
            for v in ds:
                g = math.gcd(g, v)
            if g:
                ds = tuple(sorted(v // g for v in ds))
            else:
                ds = tuple(sorted(ds))
            types[ds] += 1
        top = types.most_common(10)
        covered = sum(c for _, c in top)
        sim[n] = {
            "n_quads": len(quads),
            "n_types": len(types),
            "top10_covered": covered,
            "top10_frac": covered / len(quads),
            "top10": [{"profile": list(t), "count": c} for t, c in top],
        }
        print(f"  n={n}: {len(types)} types, top10 covers {covered}/{len(quads)} = {covered/len(quads):.3f}", flush=True)
    report["similarity_probe"] = sim

    # ---- direction series (B141/B145) ----
    print("\n=== Direction series: D(a,b;n)/n^5 for fixed primitive dirs ===", flush=True)
    dirs_fixed = [(1, 0), (0, 1), (1, 1), (1, -1), (1, 2), (2, 1), (1, -2), (2, -1),
                  (1, 3), (3, 1), (2, 3), (3, 2), (2, -3), (3, -2), (1, -3), (3, -1),
                  (3, 4), (4, 3), (1, 4), (4, 1), (2, 5), (5, 2)]
    dir_series = {}
    for a, b in dirs_fixed:
        row = {}
        for n in (16, 32, 64):
            t, _ = collinear_c4_dir(n, a, b)
            row[n] = {"D": t, "D_over_n5": t / n ** 5}
        # extrapolate: if D ~ c n^5, D/n^5 should stabilize
        dir_series[f"({a},{b})"] = row
        print(f"  ({a},{b}): " + "  ".join(f"n={n}: {row[n]['D_over_n5']:.6f}" for n in (16, 32, 64)), flush=True)
    report["dir_series"] = dir_series

    # ---- B156 formula: d(p,q) via line + circle pencil ----
    print("\n=== B156 pair-degree formula check (n=5) ===", flush=True)
    n = 5
    quads = forbidden_quads(n)
    pts = [(i % n, i // n) for i in range(n * n)]
    _, pair_bf = degree_stats(n, quads)
    # build line sizes and circle sizes containing each pair
    # circle through 3 points
    def circle_params(p, q, r):
        ax, ay = p; bx, by = q; cx, cy = r
        d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        if d == 0:
            return None
        a2 = ax * ax + ay * ay; b2 = bx * bx + by * by; c2 = cx * cx + cy * cy
        ux = a2 * (by - cy) + b2 * (cy - ay) + c2 * (ay - by)
        uy = a2 * (cx - bx) + b2 * (ax - cx) + c2 * (bx - ax)
        r2n = (ax * d - ux) ** 2 + (ay * d - uy) ** 2
        if d < 0:
            ux, uy, d = -ux, -uy, -d
        g = math.gcd(math.gcd(abs(ux), abs(uy)), abs(d))
        if g:
            ux, uy, d = ux // g, uy // g, d // g
            r2n //= g * g
        return (ux, uy, d, r2n)

    def on_circle(pt, params):
        ux, uy, d, r2n = params
        x, y = pt
        return (x * d - ux) ** 2 + (y * d - uy) ** 2 == r2n

    # precompute all circles with >=4 points and all lines with >=4 points
    circles = {}
    for i, j, k in itertools.combinations(range(n * n), 3):
        p, q, r = pts[i], pts[j], pts[k]
        if is_collinear(p, q, r):
            continue
        params = circle_params(p, q, r)
        if params is None or params in circles:
            continue
        on = frozenset(idx for idx in range(n * n) if on_circle(pts[idx], params))
        if len(on) >= 4:
            circles[params] = on
    lines = {}
    for i, j in itertools.combinations(range(n * n), 2):
        p, q = pts[i], pts[j]
        A = q[1] - p[1]; B = p[0] - q[0]; C = -(A * p[0] + B * p[1])
        g = math.gcd(math.gcd(abs(A), abs(B)), abs(C))
        if g:
            A, B, C = A // g, B // g, C // g
        if A < 0 or (A == 0 and B < 0):
            A, B, C = -A, -B, -C
        key = (A, B, C)
        if key not in lines:
            lines[key] = frozenset(idx for idx in range(n * n)
                                   if A * pts[idx][0] + B * pts[idx][1] + C == 0)
    lines = {k: v for k, v in lines.items() if len(v) >= 4}
    print(f"  circles>={4}: {len(circles)}  lines>={4}: {len(lines)}", flush=True)

    formula_ok = True
    mismatches = []
    for (i, j), dbf in pair_bf.items():
        df = 0
        for s in lines.values():
            if i in s and j in s:
                df += math.comb(len(s) - 2, 2)
        for s in circles.values():
            if i in s and j in s:
                df += math.comb(len(s) - 2, 2)
        if df != dbf:
            formula_ok = False
            mismatches.append({"pair": [i, j], "bf": dbf, "formula": df})
    report["b156_formula"] = {
        "n": n,
        "n_circles": len(circles),
        "n_lines": len(lines),
        "all_pairs_match": formula_ok,
        "n_mismatch": len(mismatches),
        "mismatch_sample": mismatches[:5],
    }
    print(f"  formula matches brute force for all {len(pair_bf)} pairs: {formula_ok}", flush=True)

    # ---- B148: translation counts of circle templates ----
    # For each circle lattice-set shape (size k), count distinct translates on larger boards.
    print("\n=== B148 circle-template translate counts ===", flush=True)
    b148 = {}
    for n in (6, 7):
        quads_n = forbidden_quads(n)
        pts_n = [(i % n, i // n) for i in range(n * n)]
        # build circles for this n
        circs = {}
        for i, j, k in itertools.combinations(range(n * n), 3):
            p, q, r = pts_n[i], pts_n[j], pts_n[k]
            if is_collinear(p, q, r):
                continue
            params = circle_params(p, q, r)
            if params is None or params in circs:
                continue
            on = frozenset(idx for idx in range(n * n) if on_circle(pts_n[idx], params))
            if len(on) >= 4:
                circs[params] = on
        # translate-count: for each circle, the bounding box of its points
        # number of integer translates that fit in n x n
        trans = Counter()
        for params, on in circs.items():
            xs = [pts_n[i][0] for i in on]
            ys = [pts_n[i][1] for i in on]
            w = max(xs) - min(xs)
            h = max(ys) - min(ys)
            ntrans = (n - w) * (n - h)
            trans[ntrans] += 1
        b148[n] = {
            "n_circles": len(circs),
            "translate_count_hist": {str(k): v for k, v in sorted(trans.items())},
            "mean_translates": (sum(k * v for k, v in trans.items()) / sum(trans.values())) if trans else 0,
        }
        print(f"  n={n}: {len(circs)} circles, mean translates={b148[n]['mean_translates']:.2f}", flush=True)
    report["b148_translates"] = b148

    out_path = OUT / "batch08_results.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
