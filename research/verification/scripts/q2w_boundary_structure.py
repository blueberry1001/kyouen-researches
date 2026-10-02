#!/usr/bin/env python3
"""Verify the q=2w boundary structure and the mod-9 lattice refinement.

No third-party dependencies are required.
"""

from __future__ import annotations

import itertools
import json
from math import comb


def det4(points: tuple[tuple[int, int], ...]) -> int:
    """Exact 4-point lifted determinant after translating the first point."""
    (x0, y0), *rest = points
    rows = []
    for x, y in rest:
        dx, dy = x - x0, y - y0
        rows.append((dx * dx + dy * dy, dx, dy))
    (a, b, c), (d, e, f), (g, h, i) = rows
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def all_four_minors_zero(points: list[tuple[int, int]]) -> bool:
    return all(det4(q) == 0 for q in itertools.combinations(points, 4))


def q2w_pair_criterion(rows: tuple[tuple[int, int], ...]) -> bool:
    """Criterion for 2 points on every row y=0,1,...,w-1 to be concyclic."""
    sums = [a + b for a, b in rows]
    if len(set(sums)) != 1:
        return False
    products = [a * b for a, b in rows]
    return all(
        products[i + 2] - 2 * products[i + 1] + products[i] == 2
        for i in range(len(products) - 2)
    )


def check_pair_criterion(w: int, m: int) -> dict[str, int]:
    pairs = tuple(itertools.combinations(range(m), 2))
    tested = concyclic = mismatches = 0
    for rows in itertools.product(pairs, repeat=w):
        criterion = q2w_pair_criterion(rows)
        points = [(x, y) for y, pair in enumerate(rows) for x in pair]
        exact = all_four_minors_zero(points)
        tested += 1
        concyclic += int(exact)
        mismatches += int(criterion != exact)
    assert mismatches == 0
    return {
        "w": w,
        "q": 2 * w,
        "m": m,
        "pair_assignments": tested,
        "concyclic": concyclic,
        "mismatches": mismatches,
    }


def modular_bounds() -> dict[str, object]:
    squares = {x * x % 9 for x in range(9)}
    max_good_5 = []
    max_good_6 = []
    for c in range(9):
        def best(length: int) -> int:
            return max(
                sum((n - (c + 2 * y) ** 2) % 9 in squares for y in range(length))
                for n in range(9)
            )

        max_good_5.append(best(5))
        max_good_6.append(best(6))

    assert squares == {0, 1, 4, 7}
    assert max(max_good_5) <= 4
    assert max(max_good_6) <= 4
    return {
        "modulus": 9,
        "square_residues": sorted(squares),
        "max_double_rows_among_5_by_c_mod_9": max_good_5,
        "max_double_rows_among_6_by_c_mod_9": max_good_6,
    }


def f_bound(w: int) -> int:
    """Maximum allowed 1s under the proved local modular constraints."""
    if w <= 4:
        return w
    if w == 5:
        return 4
    k, r = divmod(w, 6)
    return 4 * k + min(r, 4)


def check_f_bound(limit: int = 30) -> list[dict[str, int]]:
    """DP-check the closed form against all length-w binary strings implicitly."""
    states: dict[tuple[int, ...], int] = {(): 0}
    rows = []
    for w in range(1, limit + 1):
        nxt: dict[tuple[int, ...], int] = {}
        for state, score in states.items():
            for bit in (0, 1):
                seq = state + (bit,)
                if len(seq) >= 5 and all(seq[-5:]):
                    continue
                if len(seq) >= 6 and sum(seq[-6:]) > 4:
                    continue
                new_state = seq[-5:]
                nxt[new_state] = max(nxt.get(new_state, -1), score + bit)
        states = nxt
        exact = max(states.values())
        formula = f_bound(w)
        assert exact == formula, (w, exact, formula)
        rows.append(
            {
                "w": w,
                "max_double_rows_under_local_constraints": exact,
                "circle_point_upper_bound": w + exact,
                "row_only_for_q_at_least": w + exact + 1,
            }
        )
    return rows


def main() -> None:
    result = {
        "pair_criterion_cross_checks": [
            check_pair_criterion(2, 6),
            check_pair_criterion(3, 6),
            check_pair_criterion(4, 5),
        ],
        "modular_lemma": modular_bounds(),
        "lattice_circle_upper_bounds": check_f_bound(),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
