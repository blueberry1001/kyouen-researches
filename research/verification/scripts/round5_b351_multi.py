#!/usr/bin/env python3
"""Round5 B351-B400 multi-job: B379, B380, B382, B388, B400, B370.

Uses the 408 maximal 8-stone sets (round4_b371.bin).
Integer-only geometry via kyouen_core.
"""
from __future__ import annotations

import json
import struct
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, board_square, det4  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
BIN = ROOT / "research" / "verification" / "round4_b371.bin"
OUT = ROOT / "research" / "verification" / "round5_b351_multi.json"


def load_masks(path: Path):
    data = path.read_bytes()
    (count,) = struct.unpack_from("<Q", data, 0)
    return list(struct.unpack_from(f"<{count}Q", data, 8))


def mask_to_ids(mask: int, n: int = 8) -> list[int]:
    return [i for i in range(n * n) if (mask >> i) & 1]


def is_edge_point(x, y, n=8) -> bool:
    return x == 0 or y == 0 or x == n - 1 or y == n - 1


def can_add_fast(b: Board, S_list: list[int], p: int) -> bool:
    """S is safe; p is addable iff no triple of S forms a forbidden quad with p."""
    row_p = b.rows[p]
    for t in combinations(S_list, 3):
        if det4(b.rows[t[0]], b.rows[t[1]], b.rows[t[2]], row_p) == 0:
            return False
    return True


def can_add_xy(b: Board, S_list: list[int], x: int, y: int) -> bool:
    """S safe (ids on 8x8); can we add geometric point (x,y) even outside board?"""
    row_p = (x * x + y * y, x, y, 1)
    for t in combinations(S_list, 3):
        if det4(b.rows[t[0]], b.rows[t[1]], b.rows[t[2]], row_p) == 0:
            return False
    return True


def is_maximal_safe(b: Board, S_list: list[int]) -> bool:
    S = set(S_list)
    for p in range(b.V):
        if p not in S and can_add_fast(b, S_list, p):
            return False
    return True


def b_coverage(b: Board, S_list: list[int]) -> list[int]:
    empt = [i for i in range(b.V) if i not in set(S_list)]
    cov = [0] * len(empt)
    for tri in combinations(S_list, 3):
        r0, r1, r2 = b.rows[tri[0]], b.rows[tri[1]], b.rows[tri[2]]
        for ei, e in enumerate(empt):
            if det4(r0, r1, r2, b.rows[e]) == 0:
                cov[ei] += 1
    return cov


def single_cover_split(b: Board, S_list: list[int], n: int = 8):
    cov = b_coverage(b, S_list)
    empt = [i for i in range(b.V) if i not in set(S_list)]
    se = si = 0
    for ei, c in enumerate(cov):
        if c == 1:
            p = empt[ei]
            x, y = p % n, p // n
            if is_edge_point(x, y, n):
                se += 1
            else:
                si += 1
    return se, si, sum(cov)


def classify_outer(x, y, xs, ys):
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    dx = 0
    if x < minx:
        dx = minx - x
    elif x > maxx:
        dx = x - maxx
    dy = 0
    if y < miny:
        dy = miny - y
    elif y > maxy:
        dy = y - maxy
    side = []
    if x < minx:
        side.append("L")
    if x > maxx:
        side.append("R")
    if y < miny:
        side.append("T")
    if y > maxy:
        side.append("B")
    if not side:
        side = ["I"]
    return "".join(side) + f":{dx},{dy}"


def b380_analysis(sets_data):
    by_sum = defaultdict(list)
    for rec in sets_data:
        by_sum[rec["sum_b"]].append(rec)
    out = {}
    for sb, recs in sorted(by_sum.items()):
        ratios = [(r["se"], r["si"]) for r in recs]
        pure_edge = sum(1 for se, si in ratios if si == 0 and se > 0)
        pure_int = sum(1 for se, si in ratios if se == 0 and si > 0)
        edge_heavy = sum(1 for se, si in ratios if si > 0 and se >= 2 * si)
        int_heavy = sum(1 for se, si in ratios if se > 0 and si >= 2 * se)
        out[str(sb)] = {
            "count": len(recs),
            "pure_edge": pure_edge,
            "pure_interior": pure_int,
            "edge_heavy_ge2": edge_heavy,
            "interior_heavy_ge2": int_heavy,
            "both_heavy_present": edge_heavy > 0 and int_heavy > 0,
            "se_range": [min(se for se, _ in ratios), max(se for se, _ in ratios)],
            "si_range": [min(si for _, si in ratios), max(si for _, si in ratios)],
            "sample_pairs": ratios[:16],
        }
    return out


def addable_points(b, S_list):
    S = set(S_list)
    return [p for p in range(b.V) if p not in S and can_add_fast(b, S_list, p)]


def b379_search(b8: Board, masks, offset=(1, 1), max_try_sets=40, max_r=0):
    n9 = 9
    b9 = board_square(n9)

    def embed_id(i8, off):
        x, y = i8 % 8, i8 // 8
        return (y + off[1]) * n9 + (x + off[0])

    results = []
    step = max(1, len(masks) // max_try_sets)
    idxs = list(range(0, len(masks), step))[:max_try_sets]
    for idx in idxs:
        S8 = mask_to_ids(masks[idx])
        S9 = [embed_id(i, offset) for i in S8]
        found = None
        # r=0: add 1 addable point; result must be 9-stone maximal
        for p in addable_points(b9, S9):
            if is_maximal_safe(b9, S9 + [p]):
                found = {"r": 0, "add": [p], "remove": []}
                break
        if not found and max_r >= 1:
            # r=1: remove 1, add 2 addable-to-base
            for ri in range(8):
                base = S9[:ri] + S9[ri + 1 :]
                addable = addable_points(b9, base)
                if len(addable) < 2:
                    continue
                for a, c in combinations(addable, 2):
                    if is_maximal_safe(b9, base + [a, c]):
                        found = {"r": 1, "add": [a, c], "remove": [S9[ri]]}
                        break
                if found:
                    break
        if not found and max_r >= 2:
            for r1, r2 in combinations(range(8), 2):
                base = [S9[i] for i in range(8) if i not in (r1, r2)]
                addable = addable_points(b9, base)
                if len(addable) < 3:
                    continue
                cand = addable[:30]
                for a, c, d in combinations(cand, 3):
                    if is_maximal_safe(b9, base + [a, c, d]):
                        found = {"r": 2, "add": [a, c, d], "remove": [S9[r1], S9[r2]]}
                        break
                if found:
                    break
        rec = {"idx": idx, "offset": list(offset)}
        if found:
            rec.update(found)
            rec["found"] = True
            rec["k9"] = 9
        else:
            rec["found"] = False
        results.append(rec)
    return results


def b382_outer(b8: Board, masks, sample=24):
    out = []
    n = 8
    step = max(1, len(masks) // sample)
    for idx in list(range(0, len(masks), step))[:sample]:
        S = mask_to_ids(masks[idx])
        xs = [i % n for i in S]
        ys = [i // n for i in S]
        minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
        first = []
        for x in range(minx - 1, maxx + 2):
            for y in range(miny - 1, maxy + 2):
                if 0 <= x < n and 0 <= y < n:
                    continue
                dx = 0 if minx <= x <= maxx else (minx - x if x < minx else x - maxx)
                dy = 0 if miny <= y <= maxy else (miny - y if y < miny else y - maxy)
                if max(dx, dy) != 1:
                    continue
                if can_add_xy(b8, S, x, y):
                    first.append(classify_outer(x, y, xs, ys))
        out.append(
            {
                "idx": idx,
                "n_first": len(first),
                "types": sorted(set(first)),
                "all": first,
            }
        )
    return out


def are_collinear_pts(pts) -> bool:
    (x1, y1), (x2, y2) = pts[0], pts[1]
    dx, dy = x2 - x1, y2 - y1
    for x, y in pts[2:]:
        if dx * (y - y1) != dy * (x - x1):
            return False
    return True


def reason_forbidden(b: Board, S_list: list[int], x: int, y: int):
    row_p = (x * x + y * y, x, y, 1)
    line_hit = False
    circle_hit = False
    for t in combinations(S_list, 3):
        if det4(b.rows[t[0]], b.rows[t[1]], b.rows[t[2]], row_p) == 0:
            pts = [(b.rows[i][1], b.rows[i][2]) for i in t] + [(x, y)]
            if are_collinear_pts(pts):
                line_hit = True
            else:
                circle_hit = True
            if line_hit and circle_hit:
                return "both"
    if line_hit and circle_hit:
        return "both"
    if line_hit:
        return "line"
    if circle_hit:
        return "circle"
    return None


def b388_far_reason(b8: Board, masks, idx=0, dists=(2, 4, 6, 10)):
    S = mask_to_ids(masks[idx])
    xs = [i % 8 for i in S]
    ys = [i // 8 for i in S]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    out = []
    for d in dists:
        n_line_only = n_circle_only = n_both = n_free = 0
        samples = []
        for x in range(minx - d, maxx + d + 1):
            for y in range(miny - d, maxy + d + 1):
                dx = 0 if minx <= x <= maxx else (minx - x if x < minx else x - maxx)
                dy = 0 if miny <= y <= maxy else (miny - y if y < miny else y - maxy)
                if max(dx, dy) != d:
                    continue
                kind = reason_forbidden(b8, S, x, y)
                if kind is None:
                    n_free += 1
                elif kind == "line":
                    n_line_only += 1
                elif kind == "circle":
                    n_circle_only += 1
                else:
                    n_both += 1
                if len(samples) < 4:
                    samples.append({"xy": [x, y], "reason": kind})
        out.append(
            {
                "dist": d,
                "line_only": n_line_only,
                "circle_only": n_circle_only,
                "both": n_both,
                "free": n_free,
                "samples": samples,
            }
        )
    return out


def b400_three_rows(b8: Board, masks):
    recs = []
    for mask in masks:
        S = mask_to_ids(mask)
        rowc = Counter(i // 8 for i in S)
        rows3 = [r for r, c in rowc.items() if c == 3]
        clustered = False
        for a, c in combinations(rows3, 2):
            if abs(a - c) <= 1:
                clustered = True
        se, si, sumb = single_cover_split(b8, S)
        cov = b_coverage(b8, S)
        maxb = max(cov) if cov else 0
        recs.append(
            {
                "n_rows3": len(rows3),
                "clustered": clustered,
                "se": se,
                "si": si,
                "sum_b": sumb,
                "max_b": maxb,
            }
        )

    def mean(xs):
        return round(sum(xs) / len(xs), 3) if xs else None

    cl = [r for r in recs if r["clustered"]]
    sc = [r for r in recs if r["n_rows3"] >= 1 and not r["clustered"]]
    none = [r for r in recs if r["n_rows3"] == 0]
    return {
        "n_total": len(recs),
        "n_clustered": len(cl),
        "n_scattered_with_rows3": len(sc),
        "n_no_rows3": len(none),
        "clustered_mean_sum_b": mean([r["sum_b"] for r in cl]),
        "scattered_mean_sum_b": mean([r["sum_b"] for r in sc]),
        "clustered_mean_max_b": mean([r["max_b"] for r in cl]),
        "scattered_mean_max_b": mean([r["max_b"] for r in sc]),
        "rows3_hist": dict(Counter(r["n_rows3"] for r in recs)),
    }


def is_safe(b: Board, S_list: list[int]) -> bool:
    for t in combinations(S_list, 4):
        if det4(b.rows[t[0]], b.rows[t[1]], b.rows[t[2]], b.rows[t[3]]) == 0:
            return False
    return True


def b370_shrink(b8: Board, masks, sample=8):
    """3-out 2-in (net 7 stones) shrink of 8-stone maximal: why candidates fail.

    fail_unsafe = new forbidden quad appears (safety).
    fail_uncovered = safe but some empty point is addable (coverage).
    success = safe and maximal (would be a 7-stone maximal).
    """
    out = []
    step = max(1, len(masks) // sample)
    for idx in list(range(0, len(masks), step))[:sample]:
        S = mask_to_ids(masks[idx])
        fail_unsafe = fail_uncovered = success = 0
        total = 0
        for gone in combinations(range(8), 3):
            base = [S[i] for i in range(8) if i not in gone]
            bset = set(base)
            empt = [p for p in range(64) if p not in bset]
            for a, c in combinations(empt, 2):
                T = base + [a, c]
                total += 1
                if not is_safe(b8, T):
                    fail_unsafe += 1
                elif is_maximal_safe(b8, T):
                    success += 1
                else:
                    fail_uncovered += 1
        out.append(
            {
                "idx": idx,
                "total_3out2in": total,
                "fail_unsafe": fail_unsafe,
                "fail_uncovered": fail_uncovered,
                "success_maximal": success,
            }
        )
    return out


def flush(result):
    OUT.write_text(json.dumps(result, indent=1), encoding="utf-8")


def main():
    masks = load_masks(BIN)
    b8 = board_square(8)
    result = {"n_masks": len(masks)}

    print("coverage pass for B380...", flush=True)
    sets_data = []
    for i, mask in enumerate(masks):
        S = mask_to_ids(mask)
        se, si, sumb = single_cover_split(b8, S)
        sets_data.append({"idx": i, "se": se, "si": si, "sum_b": sumb})
    result["b380"] = b380_analysis(sets_data)
    result["b380_global"] = {
        "pure_edge_total": sum(v["pure_edge"] for v in result["b380"].values()),
        "pure_interior_total": sum(v["pure_interior"] for v in result["b380"].values()),
        "groups_with_both_heavy": sum(
            1 for v in result["b380"].values() if v["both_heavy_present"]
        ),
        "n_groups": len(result["b380"]),
    }
    flush(result)

    print("B400...", flush=True)
    result["b400"] = b400_three_rows(b8, masks)
    flush(result)

    print("B382...", flush=True)
    result["b382"] = b382_outer(b8, masks, sample=16)
    flush(result)

    print("B388...", flush=True)
    result["b388"] = b388_far_reason(b8, masks, idx=0, dists=(2, 4, 6, 10))
    flush(result)

    print("B379 offset (1,1) r=0 only...", flush=True)
    result["b379"] = b379_search(b8, masks, offset=(1, 1), max_try_sets=30, max_r=0)
    flush(result)

    print("B370...", flush=True)
    result["b370"] = b370_shrink(b8, masks, sample=4)
    flush(result)

    print("B379 deeper on a few sets...", flush=True)
    result["b379_deep"] = b379_search(b8, masks, offset=(1, 1), max_try_sets=4, max_r=1)
    flush(result)

    print("Wrote", OUT)


if __name__ == "__main__":
    main()
