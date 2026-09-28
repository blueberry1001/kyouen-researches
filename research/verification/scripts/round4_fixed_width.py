"""Independent exact checks for the fixed-width theorem and B541--B550.

Run from the repository root with Python 3.11+. No third-party packages.
The theorem for unbounded widths/lengths is proved in round4-fixed-width.md;
finite computation here supplies cross-checks, finite exceptions, and witnesses.
"""
from collections import Counter
from itertools import combinations
import json
from math import comb
from pathlib import Path

from kyouen_core import board_rect, is_forbidden_quad


def sum_mask(xs):
    return sum(1 << s for s in {a + b for a, b in combinations(xs, 2)})


def row_catalog(m):
    return {
        sum(1 << x for x in xs): (xs, sum_mask(xs))
        for k in range(min(m, 3) + 1)
        for xs in combinations(range(m), k)
    }


def solve_two_rows(m):
    rows = row_catalog(m)
    full = (1 << m) - 1
    states = [
        (a, b) for a in rows for b in rows
        if not (rows[a][1] & rows[b][1])
    ]
    states.sort(key=lambda s: -(s[0].bit_count() + s[1].bit_count()))
    g = {}
    terminal = Counter()
    for a, b in states:
        children = []
        for r, (occupied, other) in enumerate(((a, b), (b, a))):
            if occupied.bit_count() == 3:
                continue
            empty = full ^ occupied
            while empty:
                bit = empty & -empty
                empty ^= bit
                nxt = occupied | bit
                if rows[nxt][1] & rows[other][1]:
                    continue
                children.append((nxt, b) if r == 0 else (a, nxt))
        values = {g[t] for t in children}
        mex = 0
        while mex in values:
            mex += 1
        g[a, b] = mex
        if not children:
            terminal[a.bit_count() + b.bit_count()] += 1

    hist = dict(sorted(Counter(g.values()).items()))
    max_g = max(g.values())
    max_witness = next(s for s in states if g[s] == max_g)
    replies = {
        str(x): [y for y in range(m) if g[1 << x, 1 << y] == 0]
        for x in range(m)
    }
    three_pairs = [
        (a, b) for a, b in states if a.bit_count() == b.bit_count() == 3
    ]
    separated = 0
    mixed_witness = None
    for a, b in three_pairs:
        sa = {x + y for x, y in combinations(rows[a][0], 2)}
        sb = {x + y for x, y in combinations(rows[b][0], 2)}
        if max(sa) < min(sb) or max(sb) < min(sa):
            separated += 1
        elif mixed_witness is None:
            mixed_witness = [rows[a][0], rows[b][0]]
    result = {
        "m": m, "safe_states": len(g), "empty_g": g[0, 0],
        "g_histogram": hist, "max_g": max_g,
        "max_g_witness_rows": [rows[a][0] for a in max_witness],
        "terminal_size_histogram": dict(sorted(terminal.items())),
        "opposite_row_winning_replies": replies,
        "first_row_winning_columns": [x for x in range(m) if g[1 << x, 0] == 0],
        "three_by_three_count": len(three_pairs),
        "three_by_three_separated": separated,
        "mixed_witness": mixed_witness,
        "parity_formula_failures": sum(
            value != ((6 - a.bit_count() - b.bit_count()) % 2)
            for (a, b), value in g.items()
        ),
    }
    return result, g


def geometry_cross_check(m, specialized):
    """A separate full solver using only forbidden 4x4 determinants."""
    board = board_rect(m, 2)
    generic = board.solve_grundy()
    rowbits = (1 << m) - 1
    decoded = {(s & rowbits, s >> m): value for s, value in generic.items()}
    assert decoded == specialized, (m, "Grundy/state-set mismatch")
    q_mismatches = 0
    for indices in combinations(range(2 * m), 4):
        a = [i for i in indices if i < m]
        b = [i - m for i in indices if i >= m]
        by_sum = len(a) == 4 or len(b) == 4 or (
            len(a) == len(b) == 2 and sum(a) == sum(b)
        )
        by_det = is_forbidden_quad([board.points[i] for i in indices])
        q_mismatches += by_sum != by_det
    assert q_mismatches == 0
    return {"m": m, "states_checked": len(generic),
            "quadruples_checked": comb(2 * m, 4) if m >= 2 else 0,
            "forbidden_quadruples": len(board.quads), "mismatches": 0}


def runs(values):
    out = []
    for x in values:
        if not out or out[-1][1] != x - 1:
            out.append([x, x])
        else:
            out[-1][1] = x
    return out


def shift_witness():
    m, a, b = 30, (0, 4, 8), (4, 16, 28)
    sa = {x + y for x, y in combinations(a, 2)}
    sb = {x + y for x, y in combinations(b, 2)}
    forbidden = sorted({(v - u) // 2 for u in sa for v in sb if (v - u) % 2 == 0})
    lo, hi = -min(a), m - 1 - max(a)
    allowed = []
    determinant_checks = 0
    for t in range(lo, hi + 1):
        points = [(x + t, 0) for x in a] + [(x, 1) for x in b]
        quad_results = [is_forbidden_quad(q) for q in combinations(points, 4)]
        safe = not any(quad_results)
        assert safe == (t not in forbidden)
        determinant_checks += len(quad_results)
        if safe:
            allowed.append(t)
    allowed_runs = runs(allowed)
    assert len(allowed_runs) == 10 and 0 in allowed
    return {"m": m, "shifted_row_A": a, "fixed_row_B": b,
            "pair_sums_A": sorted(sa), "pair_sums_B": sorted(sb),
            "board_admissible_shift_range": [lo, hi],
            "forbidden_shifts": forbidden, "allowed_shift_runs": allowed_runs,
            "number_of_runs": len(allowed_runs), "determinant_checks": determinant_checks}


def main():
    result = {
        "method": "Integer pair-sum DP, independently checked by determinant DP",
        "theorem_not_inferred_from_finite_data": True,
        "two_rows": [], "independent_geometry_checks": [],
        "sufficient_length_bound": {
            str(w): 3 + 2 * (comb(3 * w - 2, 3) - (w - 1))
            for w in range(1, 11)
        },
    }
    for m in range(1, 10):
        row, g = solve_two_rows(m)
        result["two_rows"].append(row)
        if m <= 8:
            result["independent_geometry_checks"].append(geometry_cross_check(m, g))
        if m >= 6:
            assert all(row["opposite_row_winning_replies"].values())
        if m == 9:
            assert row["parity_formula_failures"] == 0
        assert row["max_g"] <= 3
        print(f"m={m}: states={len(g)}, g(empty)={row['empty_g']}, max_g={row['max_g']}", flush=True)
    result["B546"] = shift_witness()
    output = Path(__file__).resolve().parents[1] / "round4_fixed_width.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {output}", flush=True)


if __name__ == "__main__":
    main()
