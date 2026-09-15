#!/usr/bin/env python3
"""Geometric characterization of the 64 8x8 5-stone LOSS children.

Reads frozen census outcomes + parent coordinates. Computes outcome-free
geometry of each unique (parent, move) child state and compares LOSS vs WIN.

No new solves. No primary-definition changes.
"""
from __future__ import annotations

import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
N = 8
V = 64
OUTCOMES = ROOT / "artifacts" / "8x8-o-census-outcomes.csv"
STRATA = ROOT / "artifacts" / "8x8-o-strata.csv"
OUT_JSON = ROOT / "artifacts" / "8x8-five-stone-loss-geometry.json"
OUT_CSV = ROOT / "artifacts" / "8x8-five-stone-loss-geometry.csv"


def xy(p: int) -> tuple[int, int]:
    return p % N, p // N


def det3(ax, ay, az, bx, by, bz, cx, cy, cz) -> int:
    return ax * (by * cz - bz * cy) - ay * (bx * cz - bz * cx) + az * (bx * cy - by * cx)


def is_forbidden4(a, b, c, d) -> bool:
    pts = [a, b, c, d]
    xs = [xy(p)[0] for p in pts]
    ys = [xy(p)[1] for p in pts]
    zs = [x * x + y * y for x, y in zip(xs, ys)]
    return det3(
        xs[1] - xs[0], ys[1] - ys[0], zs[1] - zs[0],
        xs[2] - xs[0], ys[2] - ys[0], zs[2] - zs[0],
        xs[3] - xs[0], ys[3] - ys[0], zs[3] - zs[0],
    ) == 0


# Precompute completion masks: for each triple, the set of points making a forbidden 4-set.
def build_completion() -> dict[tuple[int, int, int], int]:
    # For speed, iterate all 4-sets once.
    from itertools import combinations
    comp: dict[tuple[int, int, int], int] = defaultdict(int)
    for a, b, c, d in combinations(range(V), 4):
        if not is_forbidden4(a, b, c, d):
            continue
        for tri in (
            (a, b, c), (a, b, d), (a, c, d), (b, c, d),
        ):
            t = tuple(sorted(tri))
            fourth = {a, b, c, d} - set(tri)
            assert len(fourth) == 1
            w = next(iter(fourth))
            comp[t] |= 1 << w
    return comp


def popcount(x: int) -> int:
    return bin(x).count("1")


def geometry(parent4: list[int], move: int) -> dict:
    stones = parent4 + [move]
    occ = 0
    for p in stones:
        occ |= 1 << p
    xs = [xy(p)[0] for p in stones]
    ys = [xy(p)[1] for p in stones]
    span_x = max(xs) - min(xs)
    span_y = max(ys) - min(ys)
    # pairwise distances
    dists = []
    for i in range(5):
        for j in range(i + 1, 5):
            dx, dy = xs[i] - xs[j], ys[i] - ys[j]
            dists.append(dx * dx + dy * dy)
    # collinear triples among the 5 stones
    col_triples = 0
    for i in range(5):
        for j in range(i + 1, 5):
            for k in range(j + 1, 5):
                x1, y1 = xs[i], ys[i]
                x2, y2 = xs[j], ys[j]
                x3, y3 = xs[k], ys[k]
                if (x2 - x1) * (y3 - y1) == (x3 - x1) * (y2 - y1):
                    col_triples += 1
    # existing forbidden completions from any triple of the 5 (points that would
    # complete a forbidden 4-set with three of our stones) — mobility blockers
    existing = 0
    stones_s = sorted(stones)
    for i in range(5):
        for j in range(i + 1, 5):
            for k in range(j + 1, 5):
                existing |= COMP[(stones_s[i], stones_s[j], stones_s[k])]
    existing &= ~occ
    safe_moves = 0
    threat_T = []  # for each legal 6th stone, T = newly lost safe responses
    for v in range(V):
        if (occ >> v) & 1:
            continue
        if (existing >> v) & 1:
            continue  # placing v is immediately forbidden
        # count newly dangerous completions if we place v
        raw = 0
        uni = 0
        for i in range(5):
            for j in range(i + 1, 5):
                a, b = stones_s[i], stones_s[j]
                m = COMP.get((a, b, v), 0)
                raw += popcount(m)
                uni |= m
        T = popcount(uni & ~existing & ~occ & ~(1 << v))
        # legal 6th move
        safe_moves += 1
        threat_T.append(T)
    return {
        "span_x": span_x,
        "span_y": span_y,
        "span_max": max(span_x, span_y),
        "bbox_area": (span_x + 1) * (span_y + 1),
        "min_pair_d2": min(dists) if dists else None,
        "max_pair_d2": max(dists) if dists else None,
        "mean_pair_d2": statistics.mean(dists) if dists else None,
        "collinear_triples": col_triples,
        "blocked_by_existing": popcount(existing),
        "safe_child_mobility": safe_moves,
        "mean_T_if_extend": statistics.mean(threat_T) if threat_T else None,
        "max_T_if_extend": max(threat_T) if threat_T else None,
        "centroid_x": statistics.mean(xs),
        "centroid_y": statistics.mean(ys),
        "centroid_dist_from_center": math.hypot(
            statistics.mean(xs) - (N - 1) / 2, statistics.mean(ys) - (N - 1) / 2
        ),
    }


def load(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def summarize(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    return {
        "n": len(vals),
        "mean": statistics.mean(vals),
        "median": statistics.median(vals),
        "min": min(vals),
        "max": max(vals),
    }


def main():
    global COMP
    print("building completion table...")
    COMP = build_completion()
    print(f"completion triples: {len(COMP)}")

    outcomes = load(OUTCOMES)
    strata = {r["canonical_parent"]: r["stratum"] for r in load(STRATA)}

    rows = []
    for r in outcomes:
        parent = [int(x) for x in r["canonical_parent"].split(",")]
        move = int(r["move"])
        g = geometry(parent, move)
        g.update(
            {
                "canonical_parent": r["canonical_parent"],
                "move": move,
                "child_outcome": r["child_outcome"],
                "stratum": strata.get(r["canonical_parent"], "?"),
                "visited": int(r["visited"]),
            }
        )
        rows.append(g)

    # unique by child state
    seen = {}
    for g in rows:
        key = (tuple(sorted([int(x) for x in g["canonical_parent"].split(",")] + [g["move"]])), )
        # key by sorted 5-set
        s5 = tuple(sorted([int(x) for x in g["canonical_parent"].split(",")] + [g["move"]]))
        if s5 not in seen:
            seen[s5] = g
    uniq = list(seen.values())

    loss = [g for g in uniq if g["child_outcome"] == "LOSS"]
    win = [g for g in uniq if g["child_outcome"] == "WIN"]

    features = [
        "span_x", "span_y", "span_max", "bbox_area",
        "min_pair_d2", "max_pair_d2", "mean_pair_d2",
        "collinear_triples", "blocked_by_existing",
        "safe_child_mobility", "mean_T_if_extend", "max_T_if_extend",
        "centroid_dist_from_center", "visited",
    ]
    stats = {}
    for f in features:
        stats[f] = {
            "LOSS": summarize([g[f] for g in loss]),
            "WIN": summarize([g[f] for g in win]),
        }

    # threshold tests: does low mobility separate LOSS?
    def rate_below(thresh, key="safe_child_mobility"):
        L = sum(1 for g in loss if g[key] is not None and g[key] <= thresh)
        W = sum(1 for g in win if g[key] is not None and g[key] <= thresh)
        return {
            "threshold": thresh,
            "LOSS_n_below": L,
            "LOSS_frac": L / max(1, len(loss)),
            "WIN_n_below": W,
            "WIN_frac": W / max(1, len(win)),
        }

    mobility_curve = [rate_below(t) for t in (10, 15, 20, 25, 30, 35, 40, 45, 50)]

    report = {
        "unique_children": len(uniq),
        "LOSS_n": len(loss),
        "WIN_n": len(win),
        "LOSS_rate": len(loss) / len(uniq),
        "feature_stats": stats,
        "mobility_threshold_curve": mobility_curve,
        "loss_stratum_counts": dict(Counter(g["stratum"] for g in loss)),
        "win_stratum_counts": dict(Counter(g["stratum"] for g in win)),
        "loss_collinear_triple_hist": dict(Counter(g["collinear_triples"] for g in loss)),
        "win_collinear_triple_hist": dict(Counter(g["collinear_triples"] for g in win)),
        "notes": (
            "LOSS 5-stone positions on 8x8 are rare (n≈64). "
            "Compare mobility and threat geometry vs WIN to see if LOSS is "
            "predictable from outcome-free structure."
        ),
    }
    OUT_JSON.write_text(json.dumps(report, indent=2) + "\n")

    fields = list(uniq[0].keys()) if uniq else []
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for g in sorted(uniq, key=lambda x: (x["child_outcome"], -x["visited"])):
            w.writerow(g)

    # print compact summary
    print(json.dumps({
        "unique": len(uniq),
        "LOSS": len(loss),
        "WIN": len(win),
        "mobility": {
            "LOSS": stats["safe_child_mobility"]["LOSS"],
            "WIN": stats["safe_child_mobility"]["WIN"],
        },
        "collinear": {
            "LOSS": stats["collinear_triples"]["LOSS"],
            "WIN": stats["collinear_triples"]["WIN"],
        },
        "blocked": {
            "LOSS": stats["blocked_by_existing"]["LOSS"],
            "WIN": stats["blocked_by_existing"]["WIN"],
        },
        "span_max": {
            "LOSS": stats["span_max"]["LOSS"],
            "WIN": stats["span_max"]["WIN"],
        },
        "mobility_curve_frac_loss": [
            (m["threshold"], round(m["LOSS_frac"], 3), round(m["WIN_frac"], 3))
            for m in mobility_curve
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
