#!/usr/bin/env python3
"""Followup: B282 deformation/rigidity, B284 embedding maximality,
B286/B287 min bounding box for Q-classes.

Q is the labeled forbidden-4-set hypergraph on sorted points (translate-normalized).
Classes = exact same labeled Q. Isomorphic-but-different-labelings may split;
documented as a limitation.

Writes round5_b271_fu_geom.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, is_forbidden_quad, square_points

OUT = Path(__file__).resolve().parents[1] / "round5_b271_fu_geom.json"


def collinear(p, q, r):
    return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]) == 0


def q_of(points):
    k = len(points)
    quads = []
    n_col = 0
    n_cyc = 0
    for ids in combinations(range(k), 4):
        pts4 = [points[i] for i in ids]
        if is_forbidden_quad(pts4):
            quads.append(ids)  # sorted tuple of indices
            a, b, c, d = pts4
            if collinear(a, b, c) and collinear(a, b, d):
                n_col += 1
            else:
                n_cyc += 1
    return tuple(quads), n_col, n_cyc


def bbox(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), max(xs), min(ys), max(ys)


def side_len(points):
    x0, x1, y0, y1 = bbox(points)
    return max(x1 - x0, y1 - y0)


def translate_normalize(points):
    x0, y0 = bbox(points)[0], bbox(points)[2]
    return tuple(sorted((p[0] - x0, p[1] - y0) for p in points))


def enumerate_configs(box, k):
    pts = [(x, y) for y in range(box + 1) for x in range(box + 1)]
    seen = set()
    out = []
    for combo in combinations(pts, k):
        norm = translate_normalize(combo)
        if norm not in seen:
            seen.add(norm)
            out.append(list(norm))
    return out


def collect_classes(box_list, k_list):
    classes = {}
    total = 0
    for box in box_list:
        for k in k_list:
            configs = enumerate_configs(box, k)
            total += len(configs)
            print(f"  box={box} k={k} configs={len(configs)}", flush=True)
            for pts in configs:
                q, n_col, n_cyc = q_of(pts)
                key = (k, q)
                if key not in classes:
                    classes[key] = {
                        "k": k,
                        "q": q,
                        "n_col": n_col,
                        "n_cyc": n_cyc,
                        "members": [],
                    }
                classes[key]["members"].append({"pts": pts, "side": side_len(pts), "box": box})
    return classes, total


def analyse(classes):
    results = []
    for key, cl in classes.items():
        members = cl["members"]
        k = cl["k"]
        sides = [m["side"] for m in members]
        min_side = min(sides)
        norms = set(translate_normalize(m["pts"]) for m in members)
        results.append({
            "k": k,
            "n_quads": len(cl["q"]),
            "q_sample": str(cl["q"])[:120],
            "n_members": len(members),
            "n_norm_forms": len(norms),
            "min_side": min_side,
            "max_side": max(sides),
            "min_side_pts": list(min(members, key=lambda m: m["side"])["pts"]),
            "n_col": cl["n_col"],
            "n_cyc": cl["n_cyc"],
            "has_multiple_norms": len(norms) > 1,
        })
    return results


def b284_embedding(n=3):
    pts_small = square_points(n)
    pts_big = square_points(n + 1)
    b_small = Board(pts_small, name=f"{n}x{n}")
    b_big = Board(pts_big, name=f"{n+1}x{n+1}")
    all_max = []
    for occ in range(1 << (n * n)):
        if b_small.is_maximal(occ):
            all_max.append(occ)
    index_s = {p: i for i, p in enumerate(pts_small)}
    index_b = {p: i for i, p in enumerate(pts_big)}
    embed = {index_s[p]: index_b[p] for p in pts_small}
    n_image_maximal = 0
    n_image_safe = 0
    failures = []
    for occ in all_max:
        occ2 = 0
        for i in range(n * n):
            if (occ >> i) & 1:
                occ2 |= 1 << embed[i]
        if b_big.is_safe(occ2):
            n_image_safe += 1
        if b_big.is_maximal(occ2):
            n_image_maximal += 1
        elif len(failures) < 6:
            mv = b_big.legal_moves(occ2) if b_big.is_safe(occ2) else []
            failures.append({
                "S_small": [list(pts_small[i]) for i in range(n * n) if (occ >> i) & 1],
                "image_safe": b_big.is_safe(occ2),
                "extra_moves": [list(pts_big[v]) for v in mv[:10]],
            })
    extra_pts = [p for p in pts_big if p not in set(pts_small)]
    return {
        "n": n,
        "K_small": b_small.max_safe_size(),
        "n_maximal_small": len(all_max),
        "n_image_safe": n_image_safe,
        "n_image_maximal": n_image_maximal,
        "ratio": n_image_maximal / len(all_max) if all_max else None,
        "extra_points": [list(p) for p in extra_pts],
        "failures_sample": failures,
    }


def b282_game_type(classes, analysis):
    """For classes with multiple normalized forms (same labeled Q, different geometry),
    check whether empty-position nimber matches across forms."""
    checks = []
    # rebuild member access
    for key, cl in classes.items():
        if len(cl["q"]) == 0:
            continue
        norms = {}
        for m in cl["members"]:
            nrm = translate_normalize(m["pts"])
            if nrm not in norms:
                norms[nrm] = m["pts"]
        if len(norms) < 2:
            continue
        pts_list = list(norms.values())[:2]
        A = [tuple(p) for p in pts_list[0]]
        B = [tuple(p) for p in pts_list[1]]
        try:
            gA = Board(A, name="A").solve_grundy().get(0)
            gB = Board(B, name="B").solve_grundy().get(0)
            checks.append({
                "A": [list(p) for p in A],
                "B": [list(p) for p in B],
                "gA": gA,
                "gB": gB,
                "same": gA == gB,
                "k": cl["k"],
                "n_quads": len(cl["q"]),
            })
        except Exception as e:
            checks.append({"error": str(e), "A": [list(p) for p in A], "B": [list(p) for p in B]})
        if len(checks) >= 10:
            break
    n_flex = sum(1 for a in analysis if a["has_multiple_norms"] and a["n_quads"] > 0)
    return {
        "n_classes_nonemptyQ_with_multiple_norms": n_flex,
        "game_type_checks": checks,
        "all_same_g": all(c.get("same") for c in checks if "same" in c) if checks else None,
    }


def main():
    result = {}
    print("collect classes box<=3 k=4,5 ...", flush=True)
    classes, total = collect_classes([2, 3], [4, 5])
    analysis = analyse(classes)
    print("B282 ...", flush=True)
    result["B282"] = b282_game_type(classes, analysis)
    result["B282"]["total_configs"] = total
    result["B282"]["n_classes"] = len(analysis)
    result["B282"]["flexible_sample"] = [a for a in analysis if a["has_multiple_norms"] and a["n_quads"] > 0][:8]
    OUT.write_text(json.dumps(result, indent=2, default=str))

    print("B284 ...", flush=True)
    result["B284"] = {"n2_to_3": b284_embedding(2), "n3_to_4": b284_embedding(3)}
    OUT.write_text(json.dumps(result, indent=2, default=str))

    print("collect classes box<=3 k=4,5,6 ...", flush=True)
    classes2, total2 = collect_classes([2, 3], [4, 5, 6])
    analysis2 = analyse(classes2)
    k2_ok = all(a["min_side"] <= a["k"] ** 2 for a in analysis2)
    worst = max(analysis2, key=lambda a: a["min_side"], default=None)
    result["B286_B287"] = {
        "total_configs": total2,
        "n_classes": len(analysis2),
        "k2_bound_holds": k2_ok,
        "worst_min_side": worst,
        "min_side_hist": {f"k{k}_side{s}": c for (k, s), c in sorted(Counter((a["k"], a["min_side"]) for a in analysis2).items())},
        "top_min_side": sorted(analysis2, key=lambda a: -a["min_side"])[:15],
    }
    OUT.write_text(json.dumps(result, indent=2, default=str))
    print("WROTE", OUT, flush=True)


if __name__ == "__main__":
    main()
