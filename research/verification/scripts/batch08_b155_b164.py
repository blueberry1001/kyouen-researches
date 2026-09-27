#!/usr/bin/env python3
"""Batch08: pair-degree (L2,g) spreads, xy-parity, max-set residue occupancy."""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict

sys.path.insert(0, r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\scripts")
from batch08_verify import degree_stats, forbidden_quads, is_collinear, parity_pattern

OUT = r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\batch08_results3.json"
report = {}

# ---- B155: spreads by (L2, g) vs by L2 alone ----
print("=== B155 pair-degree spreads ===", flush=True)
b155 = {}
for n in (4, 5, 6, 7):
    quads = forbidden_quads(n)
    pts = [(i % n, i // n) for i in range(n * n)]
    _, pair = degree_stats(n, quads)
    by_L2 = defaultdict(list)
    by_L2g = defaultdict(list)
    by_L2g_slope = defaultdict(list)
    by_offset = defaultdict(list)
    for (i, j), d in pair.items():
        x1, y1 = pts[i]
        x2, y2 = pts[j]
        dx, dy = x2 - x1, y2 - y1
        g = math.gcd(abs(dx), abs(dy)) if (dx or dy) else 1
        L2 = dx * dx + dy * dy
        pdx, pdy = dx // g, dy // g
        if pdx < 0 or (pdx == 0 and pdy < 0):
            pdx, pdy = -pdx, -pdy
        by_L2[L2].append(d)
        by_L2g[(L2, g)].append(d)
        by_L2g_slope[(L2, g, pdx, pdy)].append(d)
        by_offset[(dx, dy)].append(d)

    def stats(dmap):
        """mean of within-group spreads and max spread."""
        spreads = [(k, min(v), max(v), max(v) - min(v), len(v)) for k, v in dmap.items() if len(v) >= 2]
        if not spreads:
            return {"groups": 0, "mean_spread": 0, "max_spread": 0, "total_range": 0}
        return {
            "groups": len(spreads),
            "mean_spread": sum(s[3] for s in spreads) / len(spreads),
            "max_spread": max(s[3] for s in spreads),
            "worst": [{"key": str(s[0]), "min": s[1], "max": s[2], "spread": s[3], "n": s[4]}
                      for s in sorted(spreads, key=lambda t: -t[3])[:5]],
        }

    allv = list(pair.values())
    b155[n] = {
        "total_range": max(allv) - min(allv),
        "by_L2": stats(by_L2),
        "by_L2_g": stats(by_L2g),
        "by_L2_g_slope": stats(by_L2g_slope),
        "by_offset": stats(by_offset),
    }
    print(f"  n={n} range={b155[n]['total_range']} "
          f"mean_spread L2={b155[n]['by_L2']['mean_spread']:.1f} "
          f"L2g={b155[n]['by_L2_g']['mean_spread']:.1f} "
          f"L2g_slope={b155[n]['by_L2_g_slope']['mean_spread']:.1f} "
          f"offset={b155[n]['by_offset']['mean_spread']:.1f}", flush=True)
report["b155"] = b155

# ---- B161: full xy parity pattern histogram of concyclic quads ----
print("\n=== B161 xy-parity of concyclic quads ===", flush=True)
b161 = {}
for n in range(3, 8):
    quads = forbidden_quads(n)
    pts = [(i % n, i // n) for i in range(n * n)]
    conc = [q for q in quads if not (is_collinear(pts[q[0]], pts[q[1]], pts[q[2]])
                                     and is_collinear(pts[q[0]], pts[q[1]], pts[q[3]]))]
    coll = [q for q in quads if (is_collinear(pts[q[0]], pts[q[1]], pts[q[2]])
                                 and is_collinear(pts[q[0]], pts[q[1]], pts[q[3]]))]
    xy_c, sum_c = parity_pattern(conc, pts)
    xy_l, sum_l = parity_pattern(coll, pts)
    # enumerate ALL possible sorted multiset patterns of (x%2,y%2) for 4 points
    type_names = {(0, 0): "00", (0, 1): "01", (1, 0): "10", (1, 1): "11"}
    all_patterns = set()
    keys = ["00", "01", "10", "11"]
    from itertools import combinations_with_replacement
    for combo in combinations_with_replacement(keys, 4):
        all_patterns.add(str(tuple(sorted(combo))))
    observed = set(xy_c.keys()) | set(xy_l.keys())
    missing = all_patterns - observed
    b161[n] = {
        "n_conc": len(conc),
        "n_coll": len(coll),
        "xy_conc": xy_c,
        "xy_coll": xy_l if coll else {},
        "sum_conc": sum_c,
        "missing_xy_patterns": sorted(missing),
        "n_observed_xy": len(observed),
    }
    print(f"  n={n}: conc={len(conc)} observed_xy={len(observed)} missing={sorted(missing)[:8]}", flush=True)
    print(f"    sum_conc={sum_c}", flush=True)
report["b161"] = b161

# ---- B163/B164: n=5 max safe sets residue occupancy ----
print("\n=== B163/B164 n=5 max-set residue occupancy ===", flush=True)
n = 5
N = n * n
quads = forbidden_quads(n)
pts = [(i % n, i // n) for i in range(N)]
# forbidden lookup by bitmask
forbid_masks = []
for q in quads:
    m = 0
    for i in q:
        m |= 1 << i
    forbid_masks.append(m)

# enumerate all safe sets of size 9 (K_5=9) by DFS
max_sets = []

def is_safe(mask):
    for fm in forbid_masks:
        if (mask & fm) == fm:
            return False
    return True

def dfs(start, mask, k):
    if k == 9:
        if is_safe(mask):
            max_sets.append(mask)
        return
    # prune: remaining points
    for i in range(start, N):
        if mask & (1 << i):
            continue
        dfs(i + 1, mask | (1 << i), k + 1)

dfs(0, 0, 0)
print(f"  found {len(max_sets)} size-9 safe sets", flush=True)

# residue occupancy mod 2 (x%2,y%2) and mod 2 (x+y)%2 and mod 3, mod 5 of id
occ = {m: [] for m in (2, 3, 5)}
xy_occ = Counter()
sum_occ = Counter()
for mask in max_sets:
    counts = {2: Counter(), 3: Counter(), 5: Counter()}
    xyc = Counter()
    sumc = Counter()
    for i in range(N):
        if mask & (1 << i):
            x, y = pts[i]
            counts[2][(x % 2, y % 2)] += 1
            counts[3][(x % 3, y % 3)] += 1
            counts[5][(x % 5, y % 5)] += 1
            xyc[(x % 2, y % 2)] += 1
            sumc[(x + y) % 2] += 1
    for m in (2, 3, 5):
        occ[m].append(dict(counts[m]))
    xy_occ[tuple(sorted((str(k), v) for k, v in xyc.items()))] += 1
    sum_occ[tuple(sorted((str(k), v) for k, v in sumc.items()))] += 1

def residue_summary(occ_list, modulus):
    """per class, mean/min/max occupancy across max sets."""
    keys = set()
    for o in occ_list:
        keys.update(o.keys())
    out = {}
    for k in sorted(keys, key=str):
        vals = [o.get(k, 0) for o in occ_list]
        out[str(k)] = {"mean": sum(vals) / len(vals), "min": min(vals), "max": max(vals)}
    return out

b164 = {
    "n_max_sets": len(max_sets),
    "mod2_xy": residue_summary(occ[2], 2),
    "mod3": residue_summary(occ[3], 3),
    "mod5": residue_summary(occ[5], 5),
    "sum_parity_hist": {str(k): v for k, v in sum_occ.most_common(10)},
    "xy_occupancy_patterns": len(xy_occ),
}
report["b164"] = b164
print(f"  mod2 xy occupancy (mean/min/max):", flush=True)
for k, v in b164["mod2_xy"].items():
    print(f"    {k}: mean={v['mean']:.2f} min={v['min']} max={v['max']}", flush=True)
print(f"  sum-parity patterns across max sets: {len(sum_occ)} distinct", flush=True)
for k, v in b164["sum_parity_hist"].items():
    print(f"    {k}: {v}", flush=True)

# B163: max safe set avoiding a class vs forcing one point in class
# For mod2 xy classes: max size avoiding class A entirely
print("\n=== B163 capacity with/without a residue class (n=5) ===", flush=True)
# Compute max safe set size within points of a subset
def max_safe_in_subset(allowed_ids):
    best = 0
    allowed_mask = 0
    for i in allowed_ids:
        allowed_mask |= 1 << i

    def dfs2(start, mask, k):
        nonlocal best
        if k > best:
            best = k
        for i in range(start, len(allowed_ids)):
            bit = 1 << allowed_ids[i]
            if mask & bit:
                continue
            if is_safe(mask | bit):
                dfs2(i + 1, mask | bit, k + 1)

    dfs2(0, 0, 0)
    return best

b163 = {"avoid": {}, "force": {}}
# classes mod2 xy
for cls_name, pred in [
    ("xy00", lambda x, y: x % 2 == 0 and y % 2 == 0),
    ("xy01", lambda x, y: x % 2 == 0 and y % 2 == 1),
    ("xy10", lambda x, y: x % 2 == 1 and y % 2 == 0),
    ("xy11", lambda x, y: x % 2 == 1 and y % 2 == 1),
    ("sum_even", lambda x, y: (x + y) % 2 == 0),
    ("sum_odd", lambda x, y: (x + y) % 2 == 1),
]:
    in_cls = [i for i in range(N) if pred(*pts[i])]
    out_cls = [i for i in range(N) if not pred(*pts[i])]
    # max avoiding the class entirely
    avoid = max_safe_in_subset(out_cls)
    # max using at least one point of the class = max over p in class of max safe set containing p
    best_force = 0
    for p in in_cls:
        rest = [i for i in range(N) if i != p]
        box = [1]  # best_local as list to avoid nonlocal-in-loop issue

        def dfs3(start, mask, k, rest=rest, box=box):
            if k > box[0]:
                box[0] = k
            for i in range(start, len(rest)):
                bit = 1 << rest[i]
                if mask & bit:
                    continue
                if is_safe(mask | bit):
                    dfs3(i + 1, mask | bit, k + 1)

        dfs3(0, 1 << p, 1)
        if box[0] > best_force:
            best_force = box[0]
    b163["avoid"][cls_name] = avoid
    b163["force"][cls_name] = best_force
    print(f"  {cls_name}: avoid-class max={avoid} force≥1 max={best_force}  loss={avoid - best_force}", flush=True)
report["b163"] = b163

# ---- B169: same residue, different outcome (one-stone on n=5) ----
# Winning first moves on n=5: checkerboard minus corners = {(x,y): x+y even} \\ corners
print("\n=== B169 one-stone same-mod2 different outcome (n=5) ===", flush=True)
corners = {(0, 0), (4, 0), (0, 4), (4, 4)}
W5 = {(x, y) for y in range(5) for x in range(5) if (x + y) % 2 == 0 and (x, y) not in corners}
# group one-stone positions by (x mod m, y mod m)
b169 = {}
for m in (2, 3, 4, 5):
    groups = defaultdict(list)
    for i in range(N):
        x, y = pts[i]
        outcome = "WIN" if (x, y) in W5 else "LOSS"
        groups[(x % m, y % m)].append((x, y, outcome))
    mixed = {str(k): v for k, v in groups.items() if len(set(o for _, _, o in v)) > 1}
    b169[m] = {"n_groups": len(groups), "mixed_groups": len(mixed), "sample": list(mixed.items())[:3]}
    print(f"  m={m}: {len(mixed)} groups with mixed WIN/LOSS out of {len(groups)}", flush=True)
report["b169"] = b169

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False, default=str)
print(f"\nWrote {OUT}")
