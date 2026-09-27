#!/usr/bin/env python3
"""Batch08 follow-up: extended D_n, rectangles, parity, pair spreads."""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict

sys.path.insert(0, r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\scripts")
from batch08_verify import (
    KNOWN_F,
    collinear_c4,
    degree_stats,
    forbidden_quads,
    is_collinear,
    parity_pattern,
    center_denom_hist,
    rectangle_count,
)

OUT = r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\batch08_results2.json"
report = {}

print("=== D_n extended ===", flush=True)
dn = {}
for n in range(2, 41):
    t, _ = collinear_c4(n)
    dn[n] = t
rows = []
for n in range(4, 41):
    t = dn[n]
    rows.append({
        "n": n, "D": t,
        "D_over_n5": t / n ** 5,
        "D_over_n5logn": t / (n ** 5 * math.log(n)),
        "D_over_n6": t / n ** 6,
    })
    print(f"  n={n:2d} D={t:7d} D/n5={t/n**5:.5f} D/(n5 log n)={t/(n**5*math.log(n)):.5f} D/n6={t/n**6:.5f}", flush=True)
report["D_n_ext"] = rows

print("\n=== rectangles extended ===", flush=True)
rects = {}
for n in range(2, 13):
    r = rectangle_count(n)
    rects[n] = r
    print(f"  n={n}: tot={r['rectangles_total']} axis={r['axis_aligned']} rot={r['rotated']} "
          f"R/n4={r['rectangles_total']/n**4:.4f} R/n5={r['rectangles_total']/n**5:.4f}", flush=True)
report["rectangles_ext"] = rects

print("\n=== parity & center denom (concyclic) ===", flush=True)
parity = {}
for n in range(3, 8):
    quads = forbidden_quads(n)
    pts = [(i % n, i // n) for i in range(n * n)]
    conc = [q for q in quads if not (is_collinear(pts[q[0]], pts[q[1]], pts[q[2]])
                                     and is_collinear(pts[q[0]], pts[q[1]], pts[q[3]]))]
    xy, sm = parity_pattern(conc, pts)
    cen = center_denom_hist(n, conc, pts)
    parity[n] = {"n_conc": len(conc), "parity_xy": xy, "parity_sum": sm, "center_denom": cen}
    print(f"  n={n} conc={len(conc)} center={cen}", flush=True)
    print(f"    sum-parity: {sm}", flush=True)
report["parity"] = parity

print("\n=== pair-degree spreads (B155) ===", flush=True)
spreads = {}
for n in range(4, 8):
    quads = forbidden_quads(n)
    pts = [(i % n, i // n) for i in range(n * n)]
    deg, pair = degree_stats(n, quads)
    same_L2 = defaultdict(list)
    same_L2g = defaultdict(list)
    same_slope = defaultdict(list)
    for (i, j), d in pair.items():
        x1, y1 = pts[i]
        x2, y2 = pts[j]
        dx, dy = x2 - x1, y2 - y1
        g = math.gcd(abs(dx), abs(dy)) if (dx or dy) else 1
        L2 = dx * dx + dy * dy
        pdx, pdy = dx // g, dy // g
        # canonical slope sign
        if pdx < 0 or (pdx == 0 and pdy < 0):
            pdx, pdy = -pdx, -pdy
        same_L2[L2].append(d)
        same_L2g[(L2, g)].append(d)
        same_slope[(pdx, pdy)].append(d)

    def spread(dmap, top=6):
        outv = []
        for k, vs in dmap.items():
            if len(vs) >= 2:
                outv.append({"key": str(k), "min": min(vs), "max": max(vs),
                             "spread": max(vs) - min(vs), "count": len(vs)})
        return sorted(outv, key=lambda t: -t["spread"])[:top]

    spreads[n] = {
        "by_L2": spread(same_L2),
        "by_L2_g": spread(same_L2g),
        "by_slope": spread(same_slope),
        "pair_deg_range": [min(pair.values()), max(pair.values())],
    }
    print(f"  n={n} pair range {spreads[n]['pair_deg_range']} top L2 spreads {[(x['key'],x['spread']) for x in spreads[n]['by_L2'][:3]]}", flush=True)
report["pair_spreads"] = spreads

# B151/B152 detail: which points attain min/max degree
print("\n=== degree extreme locations ===", flush=True)
extrema = {}
for n in range(3, 8):
    quads = forbidden_quads(n)
    pts = [(i % n, i // n) for i in range(n * n)]
    deg, _ = degree_stats(n, quads)
    mn, mx = min(deg), max(deg)
    min_pts = [pts[i] for i, d in enumerate(deg) if d == mn]
    max_pts = [pts[i] for i, d in enumerate(deg) if d == mx]
    center = pts[(n // 2) * n + (n // 2)]
    extrema[n] = {
        "deg_min": mn, "deg_max": mx,
        "min_pts": min_pts, "max_pts": max_pts,
        "deg_center": deg[(n // 2) * n + (n // 2)],
        "deg_corners": [deg[0], deg[n - 1], deg[(n - 1) * n], deg[n * n - 1]],
        "min_is_only_corners": set(min_pts) == {(0, 0), (n - 1, 0), (0, n - 1), (n - 1, n - 1)} if n > 2 else None,
    }
    print(f"  n={n}: min={mn} at {min_pts[:6]}  max={mx} at {max_pts[:6]}  center={extrema[n]['deg_center']}", flush=True)
report["deg_extrema"] = extrema

# B146/B147 ratio table using known C_n
print("\n=== R_n / C_n ===", flush=True)
ratios = {}
for n in range(3, 13):
    F = KNOWN_F.get(n)
    D = dn.get(n)
    if F is None or D is None:
        continue
    C = F - D
    R = rects[n]["rectangles_total"]
    ratios[n] = {"R": R, "C": C, "R_over_C": R / C}
    print(f"  n={n}: R={R} C={C} R/C={R/C:.4f}", flush=True)
report["R_over_C"] = ratios

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False, default=str)
print(f"\nWrote {OUT}")
