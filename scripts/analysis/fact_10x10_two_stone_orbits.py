#!/usr/bin/env python3
"""10×10 二石 D4 軌道の完全幾何分類。

C(100,2) 全ペアを D4 正規化して軌道代表を列挙し、各代表について
- 相対ベクトル (dx,dy)
- 危険4点組への露出度 Σd = d(p)+d(q)
- 円・線に現れる回数の内訳
を計算する。勝敗 solve はしない（幾何のみ）。
"""
from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "exploration"
OUT.mkdir(parents=True, exist_ok=True)

N = 10
PTS = N * N


def pid(x: int, y: int) -> int:
    return y * N + x


def xy(p: int) -> tuple[int, int]:
    return (p % N, p // N)


# D4 on (x,y) with board 0..N-1
def d4_transforms(x: int, y: int):
    n = N - 1
    yield (x, y)
    yield (n - x, y)
    yield (x, n - y)
    yield (n - x, n - y)
    yield (y, x)
    yield (n - y, x)
    yield (y, n - x)
    yield (n - y, n - x)


def d4_canon_pair(p: int, q: int) -> int:
    """Return min bit-packed canonical of unordered pair under D4."""
    x1, y1 = xy(p)
    x2, y2 = xy(q)
    best = None
    for a in d4_transforms(x1, y1):
        for b in d4_transforms(x2, y2):
            ia, ib = pid(*a), pid(*b)
            if ia == ib:
                continue
            key = (min(ia, ib) << 8) | max(ia, ib)
            if best is None or key < best:
                best = key
    return best


def d4_canon_set(points: list[int]) -> tuple[int, ...]:
    """Canonical sorted tuple of up to 4 points under D4 (brute)."""
    n = N - 1
    # generate all images of the set
    coords = [xy(p) for p in points]
    images = []
    # 8 transforms
    def apply(mode, x, y):
        if mode == 0:
            return (x, y)
        if mode == 1:
            return (n - x, y)
        if mode == 2:
            return (x, n - y)
        if mode == 3:
            return (n - x, n - y)
        if mode == 4:
            return (y, x)
        if mode == 5:
            return (n - y, x)
        if mode == 6:
            return (y, n - x)
        return (n - y, n - x)

    for mode in range(8):
        img = tuple(sorted(pid(*apply(mode, x, y)) for x, y in coords))
        images.append(img)
    return min(images)


def det3(m0, m1, m2):
    return (
        m0[0] * (m1[1] * m2[2] - m1[2] * m2[1])
        - m0[1] * (m1[0] * m2[2] - m1[2] * m2[0])
        + m0[2] * (m1[0] * m2[1] - m1[1] * m2[0])
    )


def det4_quad(p, q, r, s):
    pts = [xy(p), xy(q), xy(r), xy(s)]
    A = [[x * x + y * y, x, y, 1] for x, y in pts]
    d = 0
    for j in range(4):
        minor = [[A[i][k] for k in range(4) if k != j] for i in range(1, 4)]
        sign = 1 if j % 2 == 0 else -1
        d += sign * A[0][j] * det3(minor[0], minor[1], minor[2])
    return d


def build_forbidden(n: int = N):
    """Return set of frozenset of 4 pids that are concyclic or collinear."""
    pts = [pid(x, y) for y in range(n) for x in range(n)]
    bad = []
    # vectorized-ish over combinations would be heavy in pure python for 10;
    # use nested loops with pruning via bounding — still C(100,4)=3.9e6 which is OK.
    m = len(pts)
    # Precompute coords
    coords = [xy(p) for p in pts]
    for i in range(m):
        xi, yi = coords[i]
        for j in range(i + 1, m):
            xj, yj = coords[j]
            for k in range(j + 1, m):
                xk, yk = coords[k]
                for l in range(k + 1, m):
                    xl, yl = coords[l]
                    # det |x^2+y^2 x y 1|
                    a00 = xi * xi + yi * yi
                    a10 = xj * xj + yj * yj
                    a20 = xk * xk + yk * yk
                    a30 = xl * xl + yl * yl
                    A = (
                        (a00, xi, yi, 1),
                        (a10, xj, yj, 1),
                        (a20, xk, yk, 1),
                        (a30, xl, yl, 1),
                    )
                    # expand
                    def d3(r0, r1, r2):
                        return (
                            r0[0] * (r1[1] * r2[2] - r1[2] * r2[1])
                            - r0[1] * (r1[0] * r2[2] - r1[2] * r2[0])
                            + r0[2] * (r1[0] * r2[1] - r1[1] * r2[0])
                        )

                    det = (
                        A[0][0] * d3(A[1][1:], A[2][1:], A[3][1:])
                        - A[0][1] * d3((A[1][0], A[1][2], A[1][3]), (A[2][0], A[2][2], A[2][3]), (A[3][0], A[3][2], A[3][3]))
                        + A[0][2] * d3((A[1][0], A[1][1], A[1][3]), (A[2][0], A[2][1], A[2][3]), (A[3][0], A[3][1], A[3][3]))
                        - A[0][3] * d3((A[1][0], A[1][1], A[1][2]), (A[2][0], A[2][1], A[2][2]), (A[3][0], A[3][1], A[3][2]))
                    )
                    if det == 0:
                        bad.append((pts[i], pts[j], pts[k], pts[l]))
    return bad


def classify_collinear(pts4, n=N):
    coords = [xy(p) for p in pts4]
    # all collinear?
    (x0, y0), (x1, y1) = coords[0], coords[1]
    for x, y in coords[2:]:
        if (x1 - x0) * (y - y0) != (y1 - y0) * (x - x0):
            return False, None
    dx, dy = x1 - x0, y1 - y0
    g = math.gcd(abs(dx), abs(dy)) or 1
    dx, dy = dx // g, dy // g
    if dx < 0 or (dx == 0 and dy < 0):
        dx, dy = -dx, -dy
    return True, (dx, dy)


def main():
    # Fast path: reuse known count 54441 by computing degrees with numpy chunks
    # Build forbidden quads more efficiently with numpy (like quadruple_stats)
    import itertools

    Nl = N
    pts = Nl * Nl
    combos = np.fromiter(
        itertools.chain.from_iterable(itertools.combinations(range(pts), 4)),
        dtype=np.int64,
        count=math.comb(pts, 4) * 4,
    ).reshape(-1, 4)
    print(f"combos={len(combos)}", flush=True)

    xs = combos % Nl
    ys = combos // Nl
    xx = xs.astype(np.int64)
    yy = ys.astype(np.int64)
    s = xx * xx + yy * yy

    def det4_chunk(sc, xc, yc):
        # 4x4 det via broadcasting cofactor on first row conceptually —
        # compute all 4x4 dets for array of shape (B,4,4)
        B = sc.shape[0]
        A = np.zeros((B, 4, 4), dtype=np.int64)
        A[:, :, 0] = sc
        A[:, :, 1] = xc
        A[:, :, 2] = yc
        A[:, :, 3] = 1
        # Leibniz is 24 terms — use expansion along row 0
        def d3(m):
            return (
                m[:, 0, 0] * (m[:, 1, 1] * m[:, 2, 2] - m[:, 1, 2] * m[:, 2, 1])
                - m[:, 0, 1] * (m[:, 1, 0] * m[:, 2, 2] - m[:, 1, 2] * m[:, 2, 0])
                + m[:, 0, 2] * (m[:, 1, 0] * m[:, 2, 1] - m[:, 1, 1] * m[:, 2, 0])
            )

        det = (
            A[:, 0, 0] * d3(A[:, 1:, 1:])
            - A[:, 0, 1] * d3(A[:, 1:][:, :, [0, 2, 3]])
            + A[:, 0, 2] * d3(A[:, 1:][:, :, [0, 1, 3]])
            - A[:, 0, 3] * d3(A[:, 1:, :3])
        )
        return det

    CHUNK = 200_000
    bad_rows = []
    for start in range(0, len(combos), CHUNK):
        c = combos[start : start + CHUNK]
        det = det4_chunk(s[start : start + CHUNK], xx[start : start + CHUNK], yy[start : start + CHUNK])
        hit = np.nonzero(det == 0)[0]
        if len(hit):
            bad_rows.append(c[hit])
        if start % 1_000_000 == 0:
            print(f"progress {start}/{len(combos)} bad_so_far={sum(len(b) for b in bad_rows)}", flush=True)

    bad = np.concatenate(bad_rows, axis=0) if bad_rows else np.zeros((0, 4), dtype=np.int64)
    print(f"forbidden_count={len(bad)}", flush=True)
    assert len(bad) == 54441, len(bad)

    # degree d(p)
    deg = np.zeros(pts, dtype=np.int64)
    for row in bad:
        for p in row:
            deg[p] += 1

    # pair exposure Σd and pair-in-forbidden counts
    pair_quad = Counter()  # how many forbidden quads contain this pair
    for row in bad:
        for i in range(4):
            for j in range(i + 1, 4):
                a, b = int(row[i]), int(row[j])
                key = (a, b) if a < b else (b, a)
                pair_quad[key] += 1

    # D4 orbits of pairs
    orbits = {}
    for p in range(pts):
        x1, y1 = xy(p)
        for q in range(p + 1, pts):
            key = d4_canon_pair(p, q)
            if key not in orbits:
                orbits[key] = {"canonical_key": key, "members": [], "representative": (p, q)}
            orbits[key]["members"].append((p, q))

    print(f"pair_orbits={len(orbits)}", flush=True)

    # For each orbit, geometric features from representative
    orbit_rows = []
    collinear_pair_dirs = Counter()
    for key, info in sorted(orbits.items(), key=lambda kv: kv[0]):
        p, q = info["representative"]
        x1, y1 = xy(p)
        x2, y2 = xy(q)
        dx, dy = x2 - x1, y2 - y1
        g = math.gcd(abs(dx), abs(dy)) or 1
        pdx, pdy = dx // g, dy // g
        if pdx < 0 or (pdx == 0 and pdy < 0):
            pdx, pdy = -pdx, -pdy
        # normalization of relative vector under D4: take min of 8 images of (dx,dy)
        def vec_images(dx, dy):
            yield (dx, dy)
            yield (-dx, dy)
            yield (dx, -dy)
            yield (-dx, -dy)
            yield (dy, dx)
            yield (-dy, dx)
            yield (dy, -dx)
            yield (-dy, -dx)

        rel_canon = min(vec_images(dx, dy))
        # midline parity: whether midpoint is half-integer in both coords
        mid_half = ((x1 + x2) % 2 == 1) and ((y1 + y2) % 2 == 1)
        mid_int = ((x1 + x2) % 2 == 0) and ((y1 + y2) % 2 == 0)
        sd = int(deg[p] + deg[q])
        pq = (p, q) if p < q else (q, p)
        n_quads = int(pair_quad.get(pq, 0))
        orbit_rows.append(
            {
                "orbit_key": int(key),
                "rep": [p, q],
                "rep_xy": [[x1, y1], [x2, y2]],
                "n_members": len(info["members"]),
                "dx_dy": [dx, dy],
                "primitive_dir": [pdx, pdy],
                "rel_canon": list(rel_canon),
                "chebyshev": max(abs(dx), abs(dy)),
                "euclidean2": dx * dx + dy * dy,
                "sum_d": sd,
                "d_p": int(deg[p]),
                "d_q": int(deg[q]),
                "quads_containing_pair": n_quads,
                "mid_half_integer": mid_half,
                "mid_integer": mid_int,
            }
        )

    # circle size spectrum of forbidden quads: group by concyclic circle if not collinear
    # Classify each forbidden quad
    n_collinear = 0
    n_concyclic = 0
    dir_counter = Counter()
    for row in bad:
        ok, direction = classify_collinear([int(row[i]) for i in range(4)])
        if ok:
            n_collinear += 1
            dir_counter[direction] += 1
        else:
            n_concyclic += 1

    # point degree stats
    deg_list = deg.tolist()
    summary = {
        "board": "10x10",
        "forbidden_total": int(len(bad)),
        "collinear_quads": n_collinear,
        "concyclic_quads": n_concyclic,
        "collinear_by_dir": {f"{a},{b}": int(c) for (a, b), c in sorted(dir_counter.items())},
        "pair_orbits": len(orbits),
        "point_degree_min": int(min(deg_list)),
        "point_degree_max": int(max(deg_list)),
        "point_degree_mean": float(np.mean(deg_list)),
        "point_degree_by_radius": {},
        "sum_d_orbit_min": min(r["sum_d"] for r in orbit_rows),
        "sum_d_orbit_max": max(r["sum_d"] for r in orbit_rows),
        "quads_per_pair_orbit_min": min(r["quads_containing_pair"] for r in orbit_rows),
        "quads_per_pair_orbit_max": max(r["quads_containing_pair"] for r in orbit_rows),
    }

    # degree vs distance from center
    for p in range(pts):
        x, y = xy(p)
        cx = (N - 1) / 2
        r2 = (x - cx) ** 2 + (y - cx) ** 2
        summary["point_degree_by_radius"].setdefault(str(round(r2, 1)), []).append(int(deg[p]))

    # collapse radius buckets
    rad = {}
    for k, vs in summary["point_degree_by_radius"].items():
        rad[k] = {"n": len(vs), "deg_mean": float(np.mean(vs)), "deg_min": int(min(vs)), "deg_max": int(max(vs))}
    summary["point_degree_by_radius"] = rad

    out_json = OUT / "fact_10x10_two_stone_orbits.json"
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "summary": summary,
                "orbits": orbit_rows,
                "point_degrees": deg_list,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    print(f"wrote {out_json}", flush=True)
    print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)

    # Also emit CSV of orbits
    import csv

    csv_path = OUT / "fact_10x10_two_stone_orbits.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=list(orbit_rows[0].keys()),
        )
        w.writeheader()
        for r in orbit_rows:
            row = dict(r)
            row["rep_xy"] = json.dumps(row["rep_xy"])
            row["rep"] = json.dumps(row["rep"])
            row["dx_dy"] = json.dumps(row["dx_dy"])
            row["primitive_dir"] = json.dumps(row["primitive_dir"])
            row["rel_canon"] = json.dumps(row["rel_canon"])
            w.writerow(row)
    print(f"wrote {csv_path}", flush=True)


if __name__ == "__main__":
    main()
