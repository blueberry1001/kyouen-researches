#!/usr/bin/env python3
"""round5_b101a_b149 — B149: 禁止四点組を相似型で圧縮できるか（n<=6）。

- 各禁止四点組を辺長ベクトル（昇順、gcd 正規化）で相似型に写像
- 整数拡大・平行移動・D4 像での生成被覆率を測る
- 出力: research/verification/round5_b101a_b149.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from itertools import combinations
from math import gcd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, square_points, is_forbidden_quad  # noqa: E402

OUT = ROOT / "research" / "verification" / "round5_b101a_b149.json"


def edge_lengths(pts):
    """Squared edge lengths of the complete graph on 4 points, sorted, gcd-reduced."""
    d2 = []
    for a, b in combinations(pts, 2):
        dx = a[0] - b[0]
        dy = a[1] - b[1]
        d2.append(dx * dx + dy * dy)
    d2 = sorted(d2)
    g = 0
    for v in d2:
        g = gcd(g, v)
    if g == 0:
        return (0,) * 6
    return tuple(v // g for v in d2)


def classify(quad_pts):
    """Return a hashable similarity type key for a 4-point set."""
    return edge_lengths(quad_pts)


def d4_image(pts):
    """All 8 dihedral images of a point list."""
    out = []
    for k in range(8):
        img = []
        for x, y in pts:
            if k & 1:
                x, y = y, x
            if k & 2:
                x = -x
            if k & 4:
                y = -y
            img.append((x, y))
        out.append(tuple(img))
    return out


def scaled_translated_images(template_pts, n):
    """All integer-scaled (k>=1), translated images of template that fit in 0..n-1.

    Template is a list of integer coords (may be negative). Scale by k, then translate
    so all coords land in [0, n-1].
    """
    out = []
    for k in range(1, n + 1):
        scaled = [(x * k, y * k) for x, y in template_pts]
        xs = [p[0] for p in scaled]
        ys = [p[1] for p in scaled]
        w = max(xs) - min(xs)
        h = max(ys) - min(ys)
        if w >= n or h >= n:
            continue
        # translate
        for tx in range(-min(xs), n - max(xs)):
            for ty in range(-min(ys), n - max(ys)):
                img = [(x + tx, y + ty) for x, y in scaled]
                out.append(tuple(sorted(img)))
    return out


def analyze_n(n: int, top_m: int = 10) -> dict:
    board = Board(square_points(n))
    pts = square_points(n)
    quads = []
    for ids in combinations(range(n * n), 4):
        q = tuple(pts[i] for i in ids)
        if is_forbidden_quad(q):
            quads.append(q)
    # classify
    type_counter = Counter()
    type_example = {}
    for q in quads:
        key = classify(q)
        type_counter[key] += 1
        if key not in type_example:
            type_example[key] = q
    total = len(quads)
    # top-m types by frequency
    top = type_counter.most_common(top_m)
    top_count = sum(c for _, c in top)
    top_frac = top_count / total if total else 0.0

    # coverage by scaled-translated-D4 images of the top-m templates
    # Build template as a "canonical" representative: translate so min is 0
    def canonical_template(q):
        xs = [p[0] for p in q]
        ys = [p[1] for p in q]
        return [(x - min(xs), y - min(ys)) for x, y in q]

    covered = set()
    for key, _cnt in top:
        tmpl = canonical_template(type_example[key])
        for img in d4_image(tmpl):
            for placed in scaled_translated_images(img, n):
                # check if placed is a forbidden quad and record its type
                # actually record the placed set itself as covering
                covered.add(placed)
                # also any forbidden quad with same coords
    # which quads are covered
    covered_type_count = 0
    covered_quad_count = 0
    for q in quads:
        qs = tuple(sorted(q))
        # check if qs is in covered (as sorted tuple of coords)
        if qs in covered:
            covered_quad_count += 1
    # type-level coverage
    covered_types = set()
    for q in quads:
        qs = tuple(sorted(q))
        if qs in covered:
            covered_types.add(classify(q))
    n_types = len(type_counter)
    covered_type_count = len(covered_types)

    return {
        "n": n,
        "n_forbidden_quads": total,
        "n_types": n_types,
        "top_m": top_m,
        "top_m_types_count": top_count,
        "top_m_types_frac": top_frac,
        "top_m_type_sizes": [c for _, c in top],
        "covered_quads_by_top_m": covered_quad_count,
        "covered_quads_frac": covered_quad_count / total if total else 0.0,
        "covered_types": covered_type_count,
        "covered_types_frac": covered_type_count / n_types if n_types else 0.0,
    }


def main():
    out = {}
    for n in range(3, 7):
        print(f"n={n} ...", flush=True)
        r = analyze_n(n)
        out[str(n)] = r
        print(
            f"  quads={r['n_forbidden_quads']} types={r['n_types']} "
            f"top10_frac={r['top_m_types_frac']:.3f} "
            f"covered_quads_frac={r['covered_quads_frac']:.3f} "
            f"covered_types_frac={r['covered_types_frac']:.3f}",
            flush=True,
        )
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
