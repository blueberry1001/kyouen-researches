"""Exact independent checks for circle-window spectrum theorems.

All radii/centres use Fraction and isqrt; no floating point or dependencies.
Proofs, not finite testing, establish the universal classification.
"""
from fractions import Fraction
from itertools import combinations
from math import isqrt
from pathlib import Path
import json


def ceil_fraction(x):
    return -((-x.numerator) // x.denominator)


def circle_points(cx, cy, r2):
    radius_bound = isqrt(ceil_fraction(r2)) + 1
    points = []
    for x in range(cx.numerator // cx.denominator-radius_bound,
                   ceil_fraction(cx)+radius_bound+1):
        for y in range(cy.numerator // cy.denominator-radius_bound,
                       ceil_fraction(cy)+radius_bound+1):
            if (x-cx)**2 + (y-cy)**2 == r2:
                points.append((x, y))
    return points


def axis_blocks(values):
    """Rank block and its exact interval of feasible integer side counts n."""
    values = sorted(set(values))
    blocks = []
    for i in range(len(values)):
        for j in range(i, len(values)):
            lower = values[j]-values[i]+1
            upper = (values[j+1]-values[i-1]-1
                     if i > 0 and j+1 < len(values) else None)
            blocks.append((i, j, lower, upper))
    return values, blocks


def spectra_by_blocks(points):
    if not points:
        return {0}, {0}, {0: [1, 0, 0]}
    xs, xb = axis_blocks(x for x, _ in points)
    ys, yb = axis_blocks(y for _, y in points)
    grid = [[0]*(len(ys)+1) for _ in range(len(xs)+1)]
    ix, iy = {x:i for i,x in enumerate(xs)}, {y:i for i,y in enumerate(ys)}
    for x, y in points:
        grid[ix[x]+1][iy[y]+1] = 1
    for i in range(1, len(xs)+1):
        for j in range(1, len(ys)+1):
            grid[i][j] += grid[i-1][j]+grid[i][j-1]-grid[i-1][j-1]
    square, rectangle = {0}, {0}
    witnesses = {0: [1, max(xs)+1, max(ys)+1]}
    for i, j, lx, ux in xb:
        for k, l, ly, uy in yb:
            count = grid[j+1][l+1]-grid[i][l+1]-grid[j+1][k]+grid[i][k]
            rectangle.add(count)
            n = max(lx, ly)
            if (ux is not None and n > ux) or (uy is not None and n > uy):
                continue
            square.add(count)
            a = max(xs[j]-n+1, xs[i-1]+1) if i else xs[j]-n+1
            b = max(ys[l]-n+1, ys[k-1]+1) if k else ys[l]-n+1
            witnesses.setdefault(count, [n, a, b])
    for count, (n,a,b) in witnesses.items():
        assert sum(a<=x<a+n and b<=y<b+n for x,y in points) == count
    return square, rectangle, witnesses


def spectra_by_brute_windows(points):
    if not points:
        return {0}
    minx, maxx = min(x for x,y in points), max(x for x,y in points)
    miny, maxy = min(y for x,y in points), max(y for x,y in points)
    diameter = max(maxx-minx, maxy-miny)+1
    result = {0}
    for n in range(1, diameter+1):
        for a in range(minx-n+1, maxx+1):
            for b in range(miny-n+1, maxy+1):
                result.add(sum(a<=x<a+n and b<=y<b+n for x,y in points))
    return result


def spectrum_fixed_side(points, n):
    if not points:
        return {0}
    minx, maxx = min(x for x,y in points), max(x for x,y in points)
    miny, maxy = min(y for x,y in points), max(y for x,y in points)
    return {0} | {
        sum(a <= x < a+n and b <= y < b+n for x,y in points)
        for a in range(minx-n+1, maxx+1)
        for b in range(miny-n+1, maxy+1)
    }


def lattice_symmetry_order(points, cx, cy):
    """Signed permutation isometries fixing the circle centre and Z^2."""
    pset = set(points)
    count = 0
    for swap in (False, True):
        for sx in (-1, 1):
            for sy in (-1, 1):
                tx = cx-sx*(cy if swap else cx)
                ty = cy-sy*(cx if swap else cy)
                if tx.denominator != 1 or ty.denominator != 1:
                    continue
                transformed = {(sx*(y if swap else x)+tx,
                                sy*(x if swap else y)+ty) for x,y in points}
                if transformed == pset:
                    count += 1
    return count


def predicted(points, cx, cy):
    m = len(points)
    half_center = (2*cx).denominator == (2*cy).denominator == 1
    on_axis = any(x == cx or y == cy for x,y in points)
    if half_center and not on_axis:
        assert m % 4 == 0
        return set(range(m//2+1)) | set(range(0,m+1,2)), "axis_free_half_center"
    return set(range(m+1)), "full_spectrum"


def unique_extreme(points):
    if len(points) < 2:
        return True
    return any(sum(p[c] == f(q[c] for q in points) for p in points) == 1
               for c in (0,1) for f in (min,max))


def high_circle_counts(n):
    """All circles with >n points need a half-integer centre inside the board."""
    found = {}
    for hx in range(1, 2*(n-1)):
        for hy in range(1, 2*(n-1)):
            by_distance = {}
            for x in range(n):
                for y in range(n):
                    d = (2*x-hx)**2+(2*y-hy)**2
                    by_distance.setdefault(d, []).append((x,y))
            for d, points in by_distance.items():
                if len(points) > n:
                    found.setdefault(len(points), {"center_twice": [hx,hy],
                        "radius_squared_times_four": d, "points": points})
    return found


def triple_completion_spectrum(n):
    """Independent exact circumcircle/line scan; small boards only."""
    board = [(x,y) for x in range(n) for y in range(n)]
    sizes, seen = set(), set()
    for (x1,y1),(x2,y2),(x3,y3) in combinations(board, 3):
        a, b = 2*(x2-x1), 2*(y2-y1)
        c, d = 2*(x3-x1), 2*(y3-y1)
        u = x2*x2+y2*y2-x1*x1-y1*y1
        v = x3*x3+y3*y3-x1*x1-y1*y1
        det = a*d-b*c
        if det == 0:
            size = sum((x2-x1)*(y-y1)==(y2-y1)*(x-x1) for x,y in board)
            sizes.add(size)
            continue
        cx, cy = Fraction(u*d-b*v,det), Fraction(a*v-u*c,det)
        r2 = (x1-cx)**2+(y1-cy)**2
        key = cx,cy,r2
        if key not in seen:
            seen.add(key)
            sizes.add(sum((x-cx)**2+(y-cy)**2==r2 for x,y in board))
    return sizes


def main():
    examples = [
        ("integer_axis_free_8",Fraction(0),Fraction(0),Fraction(5)),
        ("half_half_12",Fraction(1,2),Fraction(1,2),Fraction(25,2)),
        ("integer_axial_12",Fraction(0),Fraction(0),Fraction(25)),
        ("mixed_half_axial_6",Fraction(1,2),Fraction(0),Fraction(25,4)),
        ("denominator_3_4",Fraction(1,3),Fraction(1,3),Fraction(65,9)),
        ("denominator_3_6",Fraction(1,3),Fraction(0),Fraction(325,9)),
        ("half_half_16",Fraction(1,2),Fraction(1,2),Fraction(85,2)),
        ("integer_axis_free_16",Fraction(0),Fraction(0),Fraction(65)),
        ("half_half_4",Fraction(1,2),Fraction(1,2),Fraction(1,2)),
        ("integer_axial_4",Fraction(0),Fraction(0),Fraction(1)),
        ("mixed_half_axis_free_4",Fraction(1,2),Fraction(0),Fraction(5,4)),
        ("integer_axial_12_width_21",Fraction(0),Fraction(0),Fraction(100)),
        ("mixed_half_axis_free_12_width_21",Fraction(1,2),Fraction(0),Fraction(425,4)),
    ]
    result = {"integer_and_fraction_only":True, "examples":[],
              "high_counts_by_board":[], "general_pointset_checks":0}
    for name,cx,cy,r2 in examples:
        points = circle_points(cx,cy,r2)
        square, rectangle, witnesses = spectra_by_blocks(points)
        expected, kind = predicted(points,cx,cy)
        assert square == rectangle == expected, name
        assert spectra_by_brute_windows(points) == square, name
        assert (len(points)-1 in square) == unique_extreme(points), name
        widths = [max(p[c] for p in points)-min(p[c] for p in points)+1 for c in (0,1)]
        diameter = max(widths)
        fixed_checks = []
        for n in range(1, diameter+3):
            fixed = spectrum_fixed_side(points, n)
            maximum = max(fixed)
            # A unit translation changes a circle's occupancy by at most two.
            assert all(k in fixed or k+1 in fixed for k in range(maximum)), (name,n)
            if (2*cx).denominator != 1 or (2*cy).denominator != 1:
                assert fixed == set(range(maximum+1)), (name,n)
            if n >= diameter:
                assert fixed == expected, (name,n)
            fixed_checks.append({"n":n,"spectrum":sorted(fixed)})
        result["examples"].append({"name":name,"center":[str(cx),str(cy)],
            "r2":str(r2),"points":points,"m":len(points),"type":kind,
            "spectrum":sorted(square),"holes":sorted(set(range(len(points)+1))-square),
            "square_witnesses":witnesses,"bbox_widths":widths,
            "lattice_symmetry_order":lattice_symmetry_order(points,cx,cy),
            "fixed_side_checks":fixed_checks})
        print(name, len(points), sorted(square), flush=True)
    # The rank-block criterion also applies without concyclicity.
    small_grid = [(x,y) for x in range(3) for y in range(3)]
    for k in range(1,5):
        for points in combinations(small_grid,k):
            square, _, _ = spectra_by_blocks(points)
            assert square == spectra_by_brute_windows(points)
            if k >= 2:
                assert (k-1 in square) == unique_extreme(points)
            result["general_pointset_checks"] += 1
    witness_11 = [p for p in circle_points(Fraction(6),Fraction(5),Fraction(25))
                  if 0 <= p[0] <= 10 and 0 <= p[1] <= 10]
    assert len(witness_11) == 11
    result["B462_witness"] = {"n":11,"center":[6,5],"r2":25,"points":witness_11}
    for n in range(2,13):
        high = high_circle_counts(n)
        all_sizes = set(range(3,n+1)) | set(high)
        if n <= 6:
            assert triple_completion_spectrum(n) == all_sizes
        if n < 11:
            assert 11 not in all_sizes
        result["high_counts_by_board"].append({"n":n,"high_circle_sizes":sorted(high),
            "all_triple_circle_or_line_sizes":sorted(all_sizes),
            "three_stone_legal_counts":sorted(n*n-size for size in all_sizes),
            "high_circle_witnesses":high,"independent_triple_scan":n<=6})
        print("board",n,"sizes",sorted(all_sizes),flush=True)
    output=Path(__file__).resolve().parents[1]/"round4_circle_windows.json"
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(output,flush=True)


if __name__ == "__main__":
    main()
