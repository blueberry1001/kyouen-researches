#!/usr/bin/env python3
"""Exact small-board checks for the q-point fixed-width theorem.

The output is intentionally committed beside the research note.  All geometry
uses integers.  A q-set is forbidden precisely when the lifted matrix with
rows (x^2+y^2,x,y,1) has rank at most three; equivalently every four-row minor
vanishes.  An independent predicate first distinguishes a line from a circle
using cross products and then tests the usual four-point determinant.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from itertools import combinations
from math import comb
from pathlib import Path

from kyouen_core import det4


def lifted(p: tuple[int, int]) -> tuple[int, int, int, int]:
    x, y = p
    return (x * x + y * y, x, y, 1)


def cross(a, b, c) -> int:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def same_circle_or_line_rank(points: tuple[tuple[int, int], ...]) -> bool:
    """Rank test valid for every q >= 4 (not a fictitious q-determinant)."""
    rows = tuple(map(lifted, points))
    return all(det4(*(rows[i] for i in ids)) == 0
               for ids in combinations(range(len(rows)), 4))


def same_circle_or_line_geometric(points: tuple[tuple[int, int], ...]) -> bool:
    """Independent characterization: one line, or one circle through all."""
    a, b = points[:2]
    noncollinear = next((c for c in points[2:] if cross(a, b, c)), None)
    if noncollinear is None:
        return True
    base = (lifted(a), lifted(b), lifted(noncollinear))
    return all(det4(*base, lifted(p)) == 0 for p in points)


def solve(q: int, w: int, m: int) -> dict:
    points = [(x, y) for y in range(w) for x in range(m)]
    edges = []
    for ids in combinations(range(len(points)), q):
        ps = tuple(points[i] for i in ids)
        rank = same_circle_or_line_rank(ps)
        assert rank == same_circle_or_line_geometric(ps)
        if rank:
            edges.append(sum(1 << i for i in ids))

    size = 1 << len(points)
    safe = bytearray(size)
    safe[0] = 1
    by_point = [[] for _ in points]
    for edge in edges:
        for i in range(len(points)):
            if edge >> i & 1:
                by_point[i].append(edge)
    for mask in range(1, size):
        bit = mask & -mask
        i = bit.bit_length() - 1
        parent = mask ^ bit
        safe[mask] = safe[parent] and not any(mask & e == e for e in by_point[i])

    grundy = bytearray(size)
    maximal = Counter()
    maximum = 0
    max_grundy = 0
    for mask in range(size - 1, -1, -1):
        if not safe[mask]:
            continue
        children = []
        for i in range(len(points)):
            child = mask | (1 << i)
            if child != mask and safe[child]:
                children.append(child)
        if not children:
            maximal[mask.bit_count()] += 1
            maximum = max(maximum, mask.bit_count())
        else:
            child_values = {grundy[x] for x in children}
            g = 0
            while g in child_values:
                g += 1
            grundy[mask] = g
            max_grundy = max(max_grundy, g)

    wins = [list(points[i]) for i in range(len(points)) if grundy[1 << i] == 0]
    expected_capacity = (q - 1) * w
    parity_holds = all(not ok or grundy[mask] == ((expected_capacity - mask.bit_count()) & 1)
                       for mask, ok in enumerate(safe))

    # Stronger exact regime: if q > 2w, a circle meets the w horizontal
    # rows in at most 2w < q points and a non-horizontal line in at most
    # w < q points.  Hence the only forbidden q-sets are q points in one
    # row.  This gives an all-m strong solution, not merely an asymptotic
    # one.  Assert the theorem against every exhaustively enumerated case
    # in this regime.
    if q > 2 * w:
        exact_capacity = w * min(m, q - 1)
        row_safe_count = sum(comb(m, k) for k in range(min(m, q - 1) + 1))
        assert len(edges) == w * comb(m, q)
        assert sum(safe) == row_safe_count ** w
        assert maximum == exact_capacity
        assert set(maximal) == {exact_capacity}
        assert all(
            not ok or grundy[mask] == ((exact_capacity - mask.bit_count()) & 1)
            for mask, ok in enumerate(safe)
        )
    return {
        "q": q, "w": w, "m": m, "vertices": len(points),
        "forbidden_q_sets": len(edges), "safe_sets": sum(safe),
        "empty_grundy": grundy[0], "winner": "first" if grundy[0] else "second",
        "maximum_safe_size": maximum,
        "maximal_size_distribution": {str(k): maximal[k] for k in sorted(maximal)},
        "winning_first_moves": wins, "maximum_grundy": max_grundy,
        "fixed_width_parity_formula_holds_all_safe_states": parity_holds,
    }


def subset_threshold(q: int, w: int) -> int:
    n = (q - 1) * (w - 1)
    return q - 1 + 2 * (comb(n, q - 1) - (w - 1)) + (q - 2) * comb(n, q - 2)


def triple_threshold(q: int, w: int) -> int:
    n = (q - 1) * (w - 1)
    return (q - 1 + 2 * (comb(n, 3) - (w - 1) * comb(q - 1, 3))
            + (q - 2) * comb(n, 2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).parent.parent / "q_point_fixed_width.json")
    args = parser.parse_args()
    # Exhaustive ranges are deliberately modest and reproducible in seconds.
    cases = ([(q, 1, m) for q in (4, 5, 6) for m in range(1, q + 3)]
             + [(q, 2, m) for q in (4, 5, 6) for m in range(1, 10)]
             + [(q, 3, m) for q in (4, 5, 6) for m in range(1, 7)]
             + [(5, 4, 4)])
    results = [solve(*case) for case in cases]
    payload = {
        "method": "complete subset enumeration; two exact integer geometry predicates agree",
        "thresholds": {
            f"q{q}_w{w}": {
                "q_minus_1_subset_bound": subset_threshold(q, w),
                "determining_triple_bound": triple_threshold(q, w),
                "stated_minimum_bound": min(subset_threshold(q, w), triple_threshold(q, w)),
            }
            for q in (4, 5, 6) for w in (1, 2, 3)
        },
        "high_q_exact_regime": {
            "condition": "q > 2w",
            "theorem": "only same-row q-sets are forbidden; all m are strongly solved",
            "exhaustive_cases_checked": sum(q > 2 * w for q, w, _ in cases),
        },
        "cases": results,
    }
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output} ({len(results)} cases)")


if __name__ == "__main__":
    main()
