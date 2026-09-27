#!/usr/bin/env python3
"""B211-B220: rectangular boards w x m (w columns, m rows... actually w width).

Convention: board_rect(w, h) has x in 0..w-1, y in 0..h-1.
We study fixed width w, growing length h = m.

Also verifies the 2-row sum-collision lemma used by B214.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, board_rect, det4  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "batch09_rectangles.json"


def sum_collision_lemma(max_x: int = 8) -> dict:
    """(a,0),(b,0),(c,1),(d,1) concyclic iff a+b == c+d."""
    from itertools import combinations
    agree = 0
    total = 0
    for xs in combinations(range(max_x), 4):
        for row0 in combinations(xs, 2):
            row1 = tuple(x for x in xs if x not in row0)
            pts = [(row0[0], 0), (row0[1], 0), (row1[0], 1), (row1[1], 1)]
            rows = [(x * x + y * y, x, y, 1) for (x, y) in pts]
            c = det4(*rows) == 0
            s = (row0[0] + row0[1] == row1[0] + row1[1])
            total += 1
            if c == s:
                agree += 1
    # also 3+1 splits
    agree31 = total31 = 0
    for xs in combinations(range(max_x), 4):
        for row0 in combinations(xs, 3):
            row1 = tuple(x for x in xs if x not in row0)
            pts = [(x, 0) for x in row0] + [(row1[0], 1)]
            rows = [(x * x + y * y, x, y, 1) for (x, y) in pts]
            c = det4(*rows) == 0
            # 3 on a line + 1 off: never concyclic with 3 collinear? actually
            # 3 collinear + 1 off are never concyclic (circle meets line in <=2)
            total31 += 1
            if c == False:
                agree31 += 1
    return {
        "sum_rule_agree": agree,
        "sum_rule_total": total,
        "three_plus_one_never_concyclic": agree31 == total31,
        "three_plus_one_total": total31,
    }


def solve_rect(w: int, h: int) -> dict:
    b = board_rect(w, h)
    g = b.solve_grundy()
    empty_g = g[0]
    K = max(occ.bit_count() for occ in g)
    # winning first moves: g({p}) == 0
    win_first = []
    lose_first = []
    for p in range(b.V):
        gg = g.get(1 << p)
        if gg is None:
            # shouldn't happen
            continue
        if gg == 0:
            win_first.append(p)
        else:
            lose_first.append(p)
    # terminal size dist under random greedy (exact)
    dist = b.exact_terminal_dist()
    mean = sum(t * p for t, p in dist.items())
    # collinear-only quads (for B218)
    coll = 0
    conc = 0
    for ids in (
        (i, j, k, l)
        for i in range(b.V - 3)
        for j in range(i + 1, b.V - 2)
        for k in range(j + 1, b.V - 1)
        for l in range(k + 1, b.V)
    ):
        pts = [b.points[t] for t in ids]
        # collinear if all on one line
        (x1, y1), (x2, y2), (x3, y3), (x4, y4) = pts
        collinear = (
            (x2 - x1) * (y3 - y1) == (x3 - x1) * (y2 - y1)
            and (x2 - x1) * (y4 - y1) == (x4 - x1) * (y2 - y1)
        )
        rows = [b.rows[t] for t in ids]
        if det4(*rows) == 0:
            if collinear:
                coll += 1
            else:
                conc += 1
    return {
        "w": w,
        "h": h,
        "V": b.V,
        "F": len(b.quads),
        "F_collinear": coll,
        "F_concyclic": conc,
        "empty_g": empty_g,
        "winner": "F" if empty_g != 0 else "S",
        "K": K,
        "n_reachable": len(g),
        "max_g": max(g.values()),
        "n_win_first": len(win_first),
        "n_lose_first": len(lose_first),
        "win_first": win_first,
        "lose_first": lose_first,
        "rand_mean_X": mean,
        "rand_dist": {str(t): p for t, p in sorted(dist.items())},
    }


def main():
    results = {"lemma": sum_collision_lemma(), "boards": {}}

    # 2 x m : width 2, length m (h=m)
    for m in range(1, 11):
        key = f"2x{m}"
        r = solve_rect(2, m)
        results["boards"][key] = r
        print(f"{key}: g={r['empty_g']} winner={r['winner']} K={r['K']} "
              f"F={r['F']} reach={r['n_reachable']} "
              f"win_first={r['n_win_first']}/{r['V']} meanX={r['rand_mean_X']:.3f}", flush=True)

    # 3 x m
    for m in range(1, 9):
        key = f"3x{m}"
        r = solve_rect(3, m)
        results["boards"][key] = r
        print(f"{key}: g={r['empty_g']} winner={r['winner']} K={r['K']} "
              f"F={r['F']} reach={r['n_reachable']} "
              f"win_first={r['n_win_first']}/{r['V']} meanX={r['rand_mean_X']:.3f}", flush=True)

    # same-area pairs for B217
    by_area = defaultdict(list)
    for key, r in results["boards"].items():
        by_area[r["V"]].append((key, r))
    same_area = {}
    for area, lst in by_area.items():
        if len(lst) < 2:
            continue
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                k1, r1 = lst[i]
                k2, r2 = lst[j]
                same_area[f"{k1}|{k2}"] = {
                    "area": area,
                    "K1": r1["K"], "K2": r2["K"],
                    "winner1": r1["winner"], "winner2": r2["winner"],
                    "same_K": r1["K"] == r2["K"],
                    "diff_winner": r1["winner"] != r2["winner"],
                }
    results["same_area_pairs"] = same_area

    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
