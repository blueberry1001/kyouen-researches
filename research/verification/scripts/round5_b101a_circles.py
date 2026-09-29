#!/usr/bin/env python3
"""round5_b101a_circles — B131/B132/B133/B136/B138 の円構造を n<=6 で深掘り。

- 円の完全列挙（≥3点）を n<=6 で実行し、中心分母・点数・欠落を精密集計
- 既存 circle_b131_b138.json (n<=8) と突き合わせ
- 出力: research/verification/round5_b101a_circles.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # repo root
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, det4, square_points  # noqa: E402

OUT = ROOT / "research" / "verification" / "round5_b101a_circles.json"
DATA = ROOT / "research" / "verification" / "data"


def normalize_circle_from_3pts(p, q, r):
    """Return (qden, bx_num, by_num, r2_num) for circle through 3 non-collinear pts.

    Center = (bx_num/qden, by_num/qden) in lowest terms of the denominator qden.
    r2_num = qden^2 * r^2  (integer).
    Returns None if collinear.
    """
    (x1, y1), (x2, y2), (x3, y3) = p, q, r
    # 2 * det of [x,y,1] matrix = 2*(x1(y2-y3)+x2(y3-y1)+x3(y1-y2))
    D = 2 * (
        x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2)
    )
    if D == 0:
        return None
    # circumcenter
    # Ux = ((x1^2+y1^2)(y2-y3) + (x2^2+y2^2)(y3-y1) + (x3^2+y3^2)(y1-y2)) / D
    s1, s2, s3 = x1 * x1 + y1 * y1, x2 * x2 + y2 * y2, x3 * x3 + y3 * y3
    Ux = s1 * (y2 - y3) + s2 * (y3 - y1) + s3 * (y1 - y2)
    Uy = s1 * (x3 - x2) + s2 * (x1 - x3) + s3 * (x2 - x1)
    # center = (Ux/D, Uy/D)
    from math import gcd
    g = gcd(gcd(abs(Ux), abs(Uy)), abs(D))
    Ux, Uy, D = Ux // g, Uy // g, D // g
    if D < 0:
        Ux, Uy, D = -Ux, -Uy, -D
    # r^2 = (x1-Ux/D)^2 + (y1-Uy/D)^2 = ((D*x1-Ux)^2 + (D*y1-Uy)^2) / D^2
    r2_num = (D * x1 - Ux) ** 2 + (D * y1 - Uy) ** 2
    # rho = (qden, bx_num, by_num, r2_num) with center=(bx_num/qden, by_num/qden)
    # Here qden=D, bx_num=Ux, by_num=Uy
    return (D, Ux, Uy, r2_num)


def circle_key(rho):
    """Canonical key for a circle: same geometric circle regardless of which 3 pts."""
    q, bx, by, r2 = rho
    # center=(bx/q, by/q), r^2=r2/q^2
    # Scale so that r2 is integer with common q: already true.
    return (q, bx, by, r2)


def circles_on_board(n: int):
    """All circles through >=3 lattice points of the n x n board.

    Returns list of dicts: {rho, pts, npts}.
    """
    pts = square_points(n)
    V = n * n
    # For each triple, compute the circle and collect points on it.
    # Use a dict keyed by circle_key -> set of point indices.
    # To avoid O(V^3) being too heavy for n=6 (C(36,3)=7140, fine), n<=6 is ok.
    acc: dict[tuple, set[int]] = defaultdict(set)
    # We only need each circle once: iterate combinations of 3 points
    from itertools import combinations

    for i, j, k in combinations(range(V), 3):
        rho = normalize_circle_from_3pts(pts[i], pts[j], pts[k])
        if rho is None:
            continue
        key = circle_key(rho)
        s = acc[key]
        s.add(i)
        s.add(j)
        s.add(k)
    # Filter to those with >=3 points (all should have at least 3 by construction)
    out = []
    for key, idxset in acc.items():
        if len(idxset) < 3:
            continue
        q, bx, by, r2 = key
        out.append(
            {
                "qden": q,
                "bx": bx,
                "by": by,
                "r2_num": r2,
                "npts": len(idxset),
                "pts": sorted((pts[i][0], pts[i][1]) for i in idxset),
            }
        )
    return out


def analyze_n(n: int) -> dict:
    circs = circles_on_board(n)
    hist = Counter(c["npts"] for c in circs)
    # by qden: max points, count
    by_q = defaultdict(list)
    for c in circs:
        by_q[c["qden"]].append(c["npts"])
    by_q_max = {q: max(v) for q, v in by_q.items()}
    by_q_count = {q: len(v) for q, v in by_q.items()}
    # max over all
    max_pts = max((c["npts"] for c in circs), default=0)
    max_circs = [c for c in circs if c["npts"] == max_pts]
    # B138: among top-tier circles (points >= max_pts-2 or top 10%), how many distinct centers?
    thresh = max(max_pts - 2, int(max_pts * 0.8))
    top = [c for c in circs if c["npts"] >= thresh]
    top_centers = {
        (c["bx"] // c["qden"], c["by"] // c["qden"], c["qden"]) for c in top
    }
    # actually store center as reduced (bx/q, by/q)
    top_centers_reduced = {(c["bx"], c["by"], c["qden"]) for c in top}
    # B136: which point counts are missing in [3, max_pts]?
    present = set(hist)
    missing = [k for k in range(3, max_pts + 1) if k not in present]
    # For B131: is max achieved at qden in {1,2}?
    max_qdens = sorted({c["qden"] for c in max_circs})
    max_at_half_int = all(q in (1, 2) for q in max_qdens)
    # witnesses for max
    max_witnesses = [
        {"qden": c["qden"], "bx": c["bx"], "by": c["by"], "r2_num": c["r2_num"], "pts": c["pts"]}
        for c in max_circs
    ]
    # complete-circle analysis: group by (r2_num/qden^2) geometric radius
    # and by the "underlying complete circle" — lattice points on the circle of
    # that center/radius that lie in Z^2 (may extend outside the board).
    return {
        "n": n,
        "n_circles_ge3": len(circs),
        "hist_points": dict(sorted(hist.items())),
        "max_pts": max_pts,
        "max_qdens": max_qdens,
        "max_at_half_int": max_at_half_int,
        "by_q_max": {str(q): v for q, v in sorted(by_q_max.items())},
        "by_q_count": {str(q): v for q, v in sorted(by_q_count.items())},
        "n_top_tier": len(top),
        "n_top_tier_distinct_centers": len(top_centers_reduced),
        "top_center_share_ratio": (len(top) / len(top_centers_reduced)) if top_centers_reduced else None,
        "missing_sizes_3_to_max": missing,
        "max_witnesses": max_witnesses[:8],
    }


def main():
    results = {}
    for n in range(3, 7):
        print(f"n={n} ...", flush=True)
        results[str(n)] = analyze_n(n)
        print(
            f"  circles={results[str(n)]['n_circles_ge3']} "
            f"max={results[str(n)]['max_pts']} "
            f"missing={results[str(n)]['missing_sizes_3_to_max']} "
            f"max_qdens={results[str(n)]['max_qdens']}",
            flush=True,
        )
    # also load existing circle_b131_b138.json for n=7,8 comparison
    existing = json.loads((DATA / "circle_b131_b138.json").read_text())
    # B133 hierarchy: first n where each qden reaches its eventual max
    hierarchy = {}
    for q_str, row in {q: [] for q in set().union(*[
        set(results[str(n)]["by_q_max"]) for n in range(3, 7)
    ])}.items():
        pass
    all_q = sorted(
        set().union(*[set(results[str(n)]["by_q_max"].keys()) for n in range(3, 7)]),
        key=lambda s: int(s),
    )
    for q in all_q:
        row = {str(n): results[str(n)]["by_q_max"].get(q, 0) for n in range(3, 7)}
        # also from existing n=8
        ex8 = existing["per_n"]["8"].get("by_q_max", {})
        row["8"] = ex8.get(q, 0)
        hierarchy[q] = row

    out = {
        "per_n": results,
        "b133_hierarchy_by_q": hierarchy,
        "existing_hist_n7": existing["per_n"]["7"]["hist_points"],
        "existing_hist_n8": existing["per_n"]["8"]["hist_points"],
        "existing_mz_jumps": existing["mz_jumps"],
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
