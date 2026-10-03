#!/usr/bin/env python3
"""Exact packing bounds and independent exhaustive small-board audit (stdlib)."""

import argparse
import itertools
import json
import math
from pathlib import Path


def choose(n, k):
    return math.comb(n, k) if n >= k >= 0 else 0


def bound(w, q, cross_pairs=True):
    if w < 1 or q < 4:
        raise ValueError("require w >= 1 and q >= 4")
    r, a, n = q - 1, q - 2, (q - 1) * (w - 1)
    budget = choose(n, 3) - (w - 1) * choose(r, 3)
    d0, d1 = choose(r, 3), choose(r - 1, 3)
    per_point = choose(n, 2) // choose(r - 1, 2)
    cross_cost = choose(r - 1, 2) - (r - 1) // 2
    if cross_pairs and cross_cost:
        cross_budget = choose(n, 2) - (w - 1) * choose(r, 2)
        per_point = min(per_point, cross_budget // cross_cost)
    ymax = a * per_point
    if d1:
        ymax = min(ymax, budget // d1)
        period = d0 // math.gcd(d0, d1)
        # f(y+period)-f(y)=period-2*d1/gcd(d0,d1).
        if d0 > 2 * d1:
            ys = range(max(0, ymax - period + 1), ymax + 1)
        else:
            ys = range(min(ymax, period - 1) + 1)
    else:
        ys = [ymax]
    best, witness = -1, None
    for y in ys:
        x = (budget - d1 * y) // d0
        if 2 * x + y > best:
            best, witness = 2 * x + y, [x, y]
    old_a = r + 2 * (choose(n, r) - (w - 1)) + a * choose(n, r - 1)
    old_b = r + 2 * budget + a * choose(n, 2)
    return {"w": w, "q": q, "old_T": min(old_a, old_b),
            "packing_U": r + best, "combined": min(old_a, r + best),
            "Q": budget, "Y": a * per_point, "d0": d0, "d1": d1,
            "integer_optimizer": witness}


def det3(rows):
    (a, b, c), (d, e, f), (g, h, i) = rows
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def curve_key(points):
    """Primitive (A,B,C,D) of a circle or line through three points."""
    rows = [(x*x + y*y, x, y, 1) for x, y in points]
    coeff = [(-1)**j * det3([row[:j] + row[j+1:] for row in rows]) for j in range(4)]
    divisor = math.gcd(*coeff)
    if not divisor:
        raise AssertionError("three distinct lifted points must be independent")
    coeff = [v // divisor for v in coeff]
    if next(v for v in coeff if v) < 0:
        coeff = [-v for v in coeff]
    return tuple(coeff)


def on_curve(key, p):
    a, b, c, d = key
    x, y = p
    return a*(x*x+y*y) + b*x + c*y + d == 0


def board_audit(w, m, q):
    points = [(x, y) for y in range(w) for x in range(m)]
    keys = {curve_key(triple) for triple in itertools.combinations(points, 3)}
    curves = {key: sum(1 << i for i, p in enumerate(points) if on_curve(key, p)) for key in keys}
    forbidden_curves = [(key, mask) for key, mask in curves.items() if mask.bit_count() >= q]
    row_masks = [((1 << m) - 1) << (y*m) for y in range(w)]
    r = q - 1
    safe_count = row_checks = 0
    for state in range(1 << len(points)):
        if any((state & cmask).bit_count() >= q for _, cmask in forbidden_curves):
            continue
        safe_count += 1
        for rowmask in row_masks:
            b = (state & rowmask).bit_count()
            if b >= r:
                continue
            row_checks += 1
            outside = state & ~rowmask
            x = y = 0
            used_triples = set()
            per_target_pairs = {}
            blocked = 0
            for key, cmask in forbidden_curves:
                occupied = cmask & state
                missing = cmask & rowmask & ~state
                if occupied.bit_count() != r or not missing:
                    continue
                target = occupied & rowmask
                assert target.bit_count() <= 1
                if target:
                    y += 1
                    assert key[0] != 0
                else:
                    x += 1
                assert missing.bit_count() <= 2 - target.bit_count()
                blocked |= missing
                ext = [i for i in range(len(points)) if occupied & outside & (1 << i)]
                triples = set(itertools.combinations(ext, 3))
                assert used_triples.isdisjoint(triples)
                used_triples |= triples
                if target:
                    pairs = set(itertools.combinations(ext, 2))
                    prior = per_target_pairs.setdefault(target, set())
                    assert prior.isdisjoint(pairs)
                    prior |= pairs
            u = outside.bit_count()
            ext_counts = [(outside & rm).bit_count() for rm in row_masks]
            actual_budget = choose(u, 3) - sum(choose(k, 3) for k in ext_counts)
            assert choose(r, 3)*x + choose(r-1, 3)*y <= actual_budget
            assert y <= b * (choose(u, 2) // choose(r-1, 2))
            e = choose(r-1, 2) - (r-1)//2
            if e:
                cross = choose(u, 2) - sum(choose(k, 2) for k in ext_counts)
                assert y <= b * (cross // e)
            assert blocked.bit_count() <= 2*x + y
            assert b + blocked.bit_count() < bound(w, q)["packing_U"]
    return {"w": w, "m": m, "q": q, "safe_sets": safe_count, "row_checks": row_checks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--quick", action="store_true", help="skip exhaustive geometry audit")
    args = parser.parse_args()
    checks = 0
    for w in range(1, 21):
        for q in range(4, 31):
            data = bound(w, q)
            assert data["packing_U"] <= bound(w, q, False)["packing_U"]
            assert data["combined"] <= data["old_T"]
            # Independent full integer scan for small parameters.
            if w <= 6 and q <= 10:
                brute = max(2*((data["Q"]-data["d1"]*y)//data["d0"])+y
                            for y in range(data["Y"]+1) if data["d1"]*y <= data["Q"])
                assert q-1+brute == data["packing_U"]
            checks += 1
    assert bound(3, 5)["packing_U"] == 40
    boards = [] if args.quick else [board_audit(w, m, q)
        for w in (1, 2, 3) for m in (2, 3, 4) for q in (4, 5, 6)]
    result = {"schema": 1, "bound_checks": checks,
              "thresholds": [bound(w, q) for w in (2, 3, 4, 5, 10) for q in (4, 5, 6, 7, 8, 10)],
              "exhaustive_boards": boards}
    output = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(output)
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
