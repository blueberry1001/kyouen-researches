#!/usr/bin/env python3
"""B201-B210: point-deletion (board holes) experiments.

For each board size n and each deleted point set D (|D|=1 or 2 on small n),
solve the game on B_n \\ D and record empty g, winner, and max safe size K.
"""
from __future__ import annotations

import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kyouen_core import Board, board_square, board_square_minus  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "batch09_point_deletion.json"


def solve_summary(b: Board) -> dict:
    g = b.solve_grundy()
    # max safe size via DFS over reachable states (exact)
    K = max(occ.bit_count() for occ in g.keys())
    n_maximal = sum(1 for occ in g.keys() if not b.legal_moves(occ))
    empty_g = g[0]
    return {
        "V": b.V,
        "F": len(b.quads),
        "empty_g": empty_g,
        "winner": "F" if empty_g != 0 else "S",  # first wins iff empty is N (g>0)
        "K": K,
        "n_reachable": len(g),
        "n_maximal": n_maximal,
    }


def d4_orbit_of_point(x: int, y: int, n: int) -> list[tuple[int, int]]:
    s = set()
    for fx, fy, sw in itertools.product((False, True), repeat=3):
        xx, yy = x, y
        if fx:
            xx = n - 1 - xx
        if fy:
            yy = n - 1 - yy
        if sw:
            xx, yy = yy, xx
        s.add((xx, yy))
    return sorted(s)


def point_class(x: int, y: int, n: int) -> str:
    if (x, y) in ((0, 0), (0, n - 1), (n - 1, 0), (n - 1, n - 1)):
        return "corner"
    if x in (0, n - 1) or y in (0, n - 1):
        return "edge"
    if n % 2 == 1 and x == y == n // 2:
        return "center"
    return "interior"


def max_safe_points(full_board: Board, K_full: int) -> list[int]:
    """Return list of point ids appearing in at least one max safe set (n small)."""
    points_in_max = set()
    sys.setrecursionlimit(100000)
    # DFS over reachable safe sets of size K_full
    stack = [0]
    seen = {0}
    while stack:
        occ = stack.pop()
        if occ.bit_count() == K_full:
            m = occ
            while m:
                b = m & -m
                points_in_max.add(b.bit_length() - 1)
                m ^= b
            continue
        for u in full_board.legal_moves(occ):
            c = occ | (1 << u)
            if c not in seen:
                seen.add(c)
                stack.append(c)
    return sorted(points_in_max)


def main():
    results = {"single": {}, "pairs": {}, "full": {}, "meta": {}}

    for n in (3, 4, 5):
        full = board_square(n)
        fs = solve_summary(full)
        results["full"][str(n)] = fs
        print(f"full n={n}: {fs}", flush=True)
        K_full = fs["K"]
        in_max = max_safe_points(full, K_full)
        results["meta"][f"n{n}_points_in_some_max"] = in_max
        results["meta"][f"n{n}_class_of_missing"] = {
            f"{p}": {"xy": (p % n, p // n), "class": point_class(p % n, p // n, n),
                     "in_max": p in in_max, "d0": sum(1 for q in full.quads if q & (1 << p))}
            for p in range(n * n)
        }

        singles = {}
        for p in range(n * n):
            x, y = p % n, p // n
            b = board_square_minus(n, [(x, y)])
            s = solve_summary(b)
            s["point"] = p
            s["xy"] = (x, y)
            s["class"] = point_class(x, y, n)
            s["in_max"] = p in in_max
            s["K_unchanged"] = s["K"] == K_full
            s["winner_flip"] = s["winner"] != fs["winner"]
            singles[str(p)] = s
            print(f"  del({x},{y}) class={s['class']} K={s['K']} winner={s['winner']} "
                  f"flip={s['winner_flip']} g={s['empty_g']}", flush=True)
        results["single"][str(n)] = singles

    # pair deletions on n=4 (cheap) and n=5 (sample by orbits of pairs)
    for n, mode in ((4, "all"), (5, "orbit_sample")):
        full = board_square(n)
        fs = results["full"][str(n)]
        K_full = fs["K"]
        pairs = {}
        if mode == "all":
            cand = list(itertools.combinations(range(n * n), 2))
        else:
            # one representative per unordered D4-pair orbit: use first pair in lex order per orbit signature
            seen_sig = set()
            cand = []
            for p, q in itertools.combinations(range(n * n), 2):
                sig_parts = []
                for pp, qq in ((p, q), (q, p)):
                    sig_parts.append((pp % n, pp // n, qq % n, qq // n))
                # orbit signature = min over D4 images of the pair
                best = None
                for fx, fy, sw in itertools.product((False, True), repeat=3):
                    coords = []
                    for pid in (p, q):
                        x, y = pid % n, pid // n
                        if fx:
                            x = n - 1 - x
                        if fy:
                            y = n - 1 - y
                        if sw:
                            x, y = y, x
                        coords.append((x, y))
                    coords = tuple(sorted(coords))
                    if best is None or coords < best:
                        best = coords
                if best not in seen_sig:
                    seen_sig.add(best)
                    cand.append((p, q))

        singles = results["single"][str(n)]
        for p, q in cand:
            pts = [(p % n, p // n), (q % n, q // n)]
            b = board_square_minus(n, pts)
            s = solve_summary(b)
            s["points"] = [p, q]
            s["K_unchanged"] = s["K"] == K_full
            s["winner_flip"] = s["winner"] != fs["winner"]
            sp = singles[str(p)]
            sq = singles[str(q)]
            s["single_p_winner"] = sp["winner"]
            s["single_q_winner"] = sq["winner"]
            s["single_p_K"] = sp["K"]
            s["single_q_K"] = sq["K"]
            s["K_loss_additive"] = (K_full - s["K"]) == (K_full - sp["K"]) + (K_full - sq["K"])
            s["g_single_p"] = sp["empty_g"]
            s["g_single_q"] = sq["empty_g"]
            s["g_pair"] = s["empty_g"]
            s["g_interaction"] = (
                sp["winner"] == sq["winner"] == fs["winner"] and s["winner_flip"]
            )
            pairs[f"{p}-{q}"] = s
        results["pairs"][str(n)] = pairs
        print(f"pairs n={n}: {len(pairs)} solved", flush=True)

    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
