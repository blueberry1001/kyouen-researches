#!/usr/bin/env python3
"""Batch 06 verification: B101-B110 max-config shape / rigidity / mandatory points.

Loads COMPLETE max-safe enumerations:
  night-research/maxsafe_n6_K11.bin  (464 sets, K=11)
  night-research/maxsafe_n7_K14.bin  (16 sets,  K=14)
via night-research/cycle8_lib.py. Integer arithmetic only.

Outputs research/verification/batch06_shape_rigidity.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "night-research"))

from cycle8_lib import (  # noqa: E402
    apply_perm,
    board_str,
    canon,
    cell_orbit_key,
    d4_perms,
    is_safe,
    load_n6,
    load_n7,
    mask_from,
    occupancy_vector,
    stones,
    xy,
)

OUT = ROOT / "research" / "verification" / "batch06_shape_rigidity.json"


def row_col_occupancy(mask: int, n: int):
    rows = [0] * n
    cols = [0] * n
    for p in range(n * n):
        if (mask >> p) & 1:
            x, y = xy(p, n)
            cols[x] += 1
            rows[y] += 1
    return rows, cols


def edges_touched(mask: int, n: int) -> dict:
    """Touches top(y=0), bottom(y=n-1), left(x=0), right(x=n-1)."""
    t = b = l = r = False
    for p in range(n * n):
        if (mask >> p) & 1:
            x, y = xy(p, n)
            if y == 0:
                t = True
            if y == n - 1:
                b = True
            if x == 0:
                l = True
            if x == n - 1:
                r = True
    return {"top": t, "bottom": b, "left": l, "right": r, "all_four": t and b and l and r}


def min_det_size(masks: list[int], perms: list[list[int]], max_c: int = 4) -> dict:
    """Smallest |C| such that some C is contained in exactly one max set.

    Also report min |C| that is contained in exactly one set for *every* set
    (i.e. max over S of min_c |C_S|).  Here max_c bounds the search.
    """
    # For each pair of sets, intersection size; min_det >= 1 + max pairwise? No:
    # min_det(S) = min |C| s.t. C ⊆ S and no other T contains C.
    # For small families brute force subsets of each S.
    n_sets = len(masks)
    best_for_S = []
    for i, S in enumerate(masks):
        S_pts = stones(S, S.bit_length() + 1)
        best = 99
        for c in range(1, min(max_c, len(S_pts)) + 1):
            found = False
            for comb in combinations(S_pts, c):
                cm = mask_from(comb)
                hits = sum(1 for T in masks if (T & cm) == cm)
                if hits == 1:
                    best = c
                    found = True
                    break
            if found:
                break
        best_for_S.append(best)
    return {
        "per_set_min_det": best_for_S,
        "min_over_all": min(best_for_S),
        "max_over_all": max(best_for_S),
        "hist": dict(Counter(best_for_S)),
    }


def pair_intersections(masks: list[int]) -> dict:
    dists = []
    for a, b in combinations(range(len(masks)), 2):
        inter = (masks[a] & masks[b]).bit_count()
        dists.append(inter)
    return {
        "n_pairs": len(dists),
        "min_inter": min(dists) if dists else None,
        "max_inter": max(dists) if dists else None,
        "hist": dict(Counter(dists)),
    }


def exchange_edges(masks: list[int], quads) -> list[tuple[int, int, int, int]]:
    """1-swap edges: (i,j,remove,add) with masks[i] - r + a = masks[j] safe."""
    edges = []
    index = {m: i for i, m in enumerate(masks)}
    for i, S in enumerate(masks):
        pts = stones(S, 49 if S < (1 << 49) else 36)
        v = 49 if S < (1 << 49) else 36
        for r in pts:
            base = S & ~(1 << r)
            for a in range(v):
                if (base >> a) & 1:
                    continue
                T = base | (1 << a)
                if T in index and index[T] != i:
                    if is_safe(T, quads):
                        edges.append((i, index[T], r, a))
    return edges


def occupancy_class_stats(masks: list[int], n: int) -> dict:
    """Group max sets by D4-orbit occupancy vector; report per-class info."""
    members = defaultdict(list)
    for y in range(n):
        for x in range(n):
            members[cell_orbit_key(n, x, y)].append(y * n + x)
    class_map = {}
    for i, m in enumerate(masks):
        occ = occupancy_vector(m, n)
        key = tuple(sorted((f"{k[0]},{k[1]}", v) for k, v in occ.items()))
        class_map.setdefault(key, []).append(i)
    return {
        "n_classes": len(class_map),
        "class_sizes": [len(v) for v in class_map.values()],
        "classes": [
            {"occ": dict(k), "set_ids": v} for k, v in class_map.items()
        ],
    }


def row_occupancy_hist(masks: list[int], n: int) -> dict:
    row_hist = Counter()
    col_hist = Counter()
    empty_rows_per_set = []
    empty_cols_per_set = []
    per_set_row_profiles = []
    for m in masks:
        rows, cols = row_col_occupancy(m, n)
        row_hist.update(rows)
        col_hist.update(cols)
        empty_rows_per_set.append(sum(1 for r in rows if r == 0))
        empty_cols_per_set.append(sum(1 for c in cols if c == 0))
        per_set_row_profiles.append(tuple(rows))
    return {
        "row_hist_global": dict(sorted(row_hist.items())),
        "col_hist_global": dict(sorted(col_hist.items())),
        "empty_rows_per_set": dict(Counter(empty_rows_per_set)),
        "empty_cols_per_set": dict(Counter(empty_cols_per_set)),
        "n_distinct_row_profiles": len(set(per_set_row_profiles)),
        "row_profile_hist": {
            str(list(k)): v for k, v in Counter(per_set_row_profiles).items()
        },
        "fraction_rows_eq_2": row_hist.get(2, 0) / max(1, sum(row_hist.values())),
        "fraction_rows_in_013": (
            row_hist.get(0, 0) + row_hist.get(1, 0) + row_hist.get(3, 0)
        )
        / max(1, sum(row_hist.values())),
    }


def point_frequency(masks: list[int], n: int) -> dict:
    freq = [0] * (n * n)
    for m in masks:
        for p in stones(m, n * n):
            freq[p] += 1
    return {
        "freq": freq,
        "never_used": [p for p in range(n * n) if freq[p] == 0],
        "always_used": [p for p in range(n * n) if freq[p] == len(masks)],
        "hist": dict(Counter(freq)),
    }


def forced_point_capacity_loss(n: int, quads, known_K: int, sample_points=None) -> dict:
    """For selected points p, estimate max safe size with p forced.

    Full search is expensive; we run a bounded DFS for small n or sample.
    Here we do a cheap necessary-condition probe: among the *known* max sets,
    how many contain p?  Combined with capacity literature (CYCLE15) where
    available.  A true capacity drop requires a solver; we only record whether
    every max set already contains p (then p is mandatory and capacity is
    unchanged) or none does (p unused at max) or mixed.
    """
    # loaded outside; this function receives masks via closure-free args
    return {}


def analyze_board(name: str, masks: list[int], n: int, known_K: int, quads) -> dict:
    perms = d4_perms(n)
    edges = [edges_touched(m, n) for m in masks]
    all_four = sum(1 for e in edges if e["all_four"])
    freq = point_frequency(masks, n)
    rows_stats = row_occupancy_hist(masks, n)
    occ_cls = occupancy_class_stats(masks, n)
    inter = pair_intersections(masks)
    # min_det: n=7 has 16 sets -> cheap; n=6 has 464 -> pair-inter lower bound first
    if len(masks) <= 32:
        md = min_det_size(masks, perms, max_c=3)
    else:
        # lower bound: 1 + (max over pairs? no). Use: min_det >= 1 iff some unique point.
        # Exact min_det for large family via unique-point then 2-subset counts is O(n^2 * |M|).
        # We do c=1 and c=2 fully, c=3 only lower bound via intersections.
        best_for_S = []
        for i, S in enumerate(masks):
            S_pts = stones(S, n * n)
            best = 99
            # c=1
            for p in S_pts:
                hits = sum(1 for T in masks if (T >> p) & 1)
                if hits == 1:
                    best = 1
                    break
            if best > 1:
                for a, b in combinations(S_pts, 2):
                    cm = (1 << a) | (1 << b)
                    hits = sum(1 for T in masks if (T & cm) == cm)
                    if hits == 1:
                        best = 2
                        break
            if best > 2:
                # c=3 partial: stop after first success; else leave 3 as ">=3 or 3"
                for comb in combinations(S_pts, 3):
                    cm = mask_from(comb)
                    hits = sum(1 for T in masks if (T & cm) == cm)
                    if hits == 1:
                        best = 3
                        break
                if best > 3:
                    best = 3  # we only searched up to 3; record as <=3 if found else ">2 unconfirmed"
                    # distinguish: if never found, mark 99-> keep as None-ish
            best_for_S.append(best)
        md = {
            "per_set_min_det_capped3": best_for_S,
            "min_over_all": min(best_for_S),
            "max_over_all": max(best_for_S),
            "hist": dict(Counter(best_for_S)),
            "note": "searched c=1,2 fully; c=3 until first hit per set",
        }

    # occupancy vector uniqueness vs exchange structure (B109)
    # For n=7: 2 occ classes. For n=6: 22 occ classes (FINAL_SELECTION table).
    # Within each class, compute 1-swap degree distribution.
    # Building 1-swap graph for 464 sets is fine (464*11*25 ≈ 127k checks).
    v = n * n
    index = {m: i for i, m in enumerate(masks)}
    swap_deg = [0] * len(masks)
    swap_nbrs = defaultdict(set)
    for i, S in enumerate(masks):
        pts = stones(S, v)
        for r in pts:
            base = S & ~(1 << r)
            for a in range(v):
                if (base >> a) & 1:
                    continue
                T = base | (1 << a)
                j = index.get(T)
                if j is not None and j != i:
                    # T is in the COMPLETE safe census, so the edge is valid
                    swap_deg[i] += 1
                    swap_nbrs[i].add(j)
    # class-wise degree stats
    class_deg = {}
    for cls in occ_cls["classes"]:
        ids = cls["set_ids"]
        degs = [swap_deg[i] for i in ids]
        class_deg[str(cls["occ"])] = {
            "size": len(ids),
            "deg_hist": dict(Counter(degs)),
            "min_deg": min(degs),
            "max_deg": max(degs),
        }

    # B108: common intersection
    inter_all = masks[0]
    for m in masks[1:]:
        inter_all &= m
    common = stones(inter_all, v)

    # B101 edge-touch failures
    edge_failures = [i for i, e in enumerate(edges) if not e["all_four"]]

    return {
        "name": name,
        "n": n,
        "K": known_K,
        "n_sets": len(masks),
        "B101_edges": {
            "n_touch_all_four": all_four,
            "n_failures": len(edge_failures),
            "failure_ids": edge_failures[:10],
            "per_edge": {
                "top": sum(1 for e in edges if e["top"]),
                "bottom": sum(1 for e in edges if e["bottom"]),
                "left": sum(1 for e in edges if e["left"]),
                "right": sum(1 for e in edges if e["right"]),
            },
        },
        "B102_B103_rows": rows_stats,
        "B104_point_freq": {
            "never_used": freq["never_used"],
            "always_used": freq["always_used"],
            "hist": freq["hist"],
            "never_used_by_orbit": sorted(
                {cell_orbit_key(n, *xy(p, n)) for p in freq["never_used"]}
            ),
            "always_used_by_orbit": sorted(
                {cell_orbit_key(n, *xy(p, n)) for p in freq["always_used"]}
            ),
        },
        "B106_B107_min_det": md,
        "B108_common_intersection": common,
        "B109_occ_classes": {
            "n_classes": occ_cls["n_classes"],
            "class_sizes": occ_cls["class_sizes"],
            "class_deg_stats": class_deg,
        },
        "pair_intersections": inter,
    }


def main():
    from cycle8_lib import forbidden_quads

    n7 = load_n7()
    n6 = load_n6()
    print(f"loaded n7={len(n7)} n6={len(n6)}", flush=True)

    # quads needed only for safety of swap edges; reuse cached if possible
    cache_q = ROOT / "research" / "verification" / "batch06_quads_cache.json"
    if cache_q.exists():
        data = json.loads(cache_q.read_text())
        quads6 = [tuple(q) for q in data["n6"]]
        quads7 = [tuple(q) for q in data["n7"]]
    else:
        print("building forbidden quads...", flush=True)
        quads6 = forbidden_quads(6)
        quads7 = forbidden_quads(7)
        cache_q.write_text(json.dumps({"n6": quads6, "n7": quads7}))
        print(f"quads n6={len(quads6)} n7={len(quads7)}", flush=True)

    r7 = analyze_board("n7_K14", n7, 7, 14, quads7)
    print("n7 done", flush=True)
    r6 = analyze_board("n6_K11", n6, 6, 11, quads6)
    print("n6 done", flush=True)

    OUT.write_text(json.dumps({"n6": r6, "n7": r7}, indent=2, default=str))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
