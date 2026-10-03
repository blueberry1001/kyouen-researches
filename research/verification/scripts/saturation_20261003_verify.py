"""Independent exact audits for the 2026-10-03 saturation constructions.

Only Python's standard library is required. Geometry is recomputed here from
coordinates, independently of the C++ walk's precomputed completion masks.
The line-cover theorem is a mathematical proof in the companion note; finite
checks below validate its counting ingredients without extrapolating them.
"""
from collections import Counter
from fractions import Fraction
from functools import cache
from itertools import combinations, permutations, product
from math import comb, gcd, pi
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent


def determinant(points):
    """Full 4x4 Leibniz determinant of (x^2+y^2,x,y,1)."""
    rows = [(x*x+y*y, x, y, 1) for x, y in points]
    total = 0
    for perm in permutations(range(4)):
        inversions = sum(perm[i] > perm[j] for i in range(4) for j in range(i+1, 4))
        term = (-1) ** inversions
        for i, j in enumerate(perm):
            term *= rows[i][j]
        total += term
    return total


def curve(triple):
    (x,y),(u,v),(r,s) = triple
    u -= x; v -= y; r -= x; s -= y
    a = u*s-v*r
    if a:
        fx = (u*u+v*v)*s-(r*r+s*s)*v
        fy = u*(r*r+s*s)-r*(u*u+v*v)
        c = [a, -2*a*x-fx, -2*a*y-fy, a*(x*x+y*y)+fx*x+fy*y]
    else:
        c = [0, -v, u, v*x-u*y]
    g = gcd(*c)
    c = [z//g for z in c]
    if next(z for z in c if z) < 0:
        c = [-z for z in c]
    return tuple(c)


def on_curve(c, point):
    a,b,c_,d = c
    x,y = point
    return a*(x*x+y*y)+b*x+c_*y+d == 0


def audit_witness(n, ids):
    assert len(set(ids)) == len(ids) and all(0 <= p < n*n for p in ids)
    ids = sorted(ids)
    points = [(p % n, p//n) for p in ids]
    dets = [determinant(t) for t in combinations(points, 4)]
    assert all(dets)
    triples = list(combinations(range(len(ids)), 3))
    coefficients = [curve([points[i] for i in t]) for t in triples]
    assert len(set(coefficients)) == comb(len(ids), 3)  # safety: one triple per curve
    assert all(sum(on_curve(c, p) for p in points) == 3 for c in coefficients)
    blockers = []
    multiplicities = Counter()
    for p in range(n*n):
        if p in ids:
            continue
        point = (p % n, p//n)
        hits = [i for i,c in enumerate(coefficients) if on_curve(c, point)]
        assert hits, (n, ids, p)
        i = hits[0]
        triple = triples[i]
        assert determinant([points[j] for j in triple]+[point]) == 0
        blockers.append({'point_id': p, 'triple_ids': [ids[j] for j in triple],
                         'curve_coefficients': coefficients[i]})
        multiplicities[len(hits)] += 1
    return {'n': n, 'k': len(ids), 'ids': ids, 'coordinates': points,
            'checked_safe_quadruples': len(dets), 'blocked_empty_points': len(blockers),
            'min_abs_nonzero_determinant': min(map(abs,dets)),
            'three_stone_lines': [c for c in coefficients if c[0] == 0],
            'blocker_multiplicity_histogram': dict(sorted(multiplicities.items())),
            'empty_point_certificates': blockers}


@cache
def phi(d):
    return sum(gcd(t,d) == 1 for t in range(1,d+1))


def line_cover_bound(n, k, q=4):
    """Integer B_q(n,k) from the direction-capacity knapsack, q>=4."""
    assert q >= 4
    r = q-1
    remaining = k*(k-1)//(r*(r-1))
    per_direction = k//r
    total = 0
    for d in range(1,(n-1)//(r-1)+1):
        take = min(remaining, 4*phi(d)*per_direction)
        total += take*((n-1)//d+1-r)
        remaining -= take
    return total


def universal_coefficient(k):
    """Exact rational F(k), so B(n,k)<=n*F(k)."""
    if k < 3:
        return Fraction(0)
    remaining = k*(k-1)//6
    total = Fraction(0)
    d = 1
    while remaining:
        take = min(remaining, 4*phi(d)*(k//3))
        total += Fraction(take,d)
        remaining -= take
        d += 1
    return total


def audit_directions_and_bound():
    direction_checks = []
    for d in range(1,101):
        directions = {(a,b) for a in range(-d,d+1) for b in range(-d,d+1)
                      if max(abs(a),abs(b)) == d and gcd(a,b) == 1
                      and (a > 0 or (a == 0 and b > 0))}
        assert len(directions) == 4*phi(d)
        direction_checks.append({'d':d, 'primitive_unoriented_directions':len(directions)})

    # Independent small knapsack check: construct and sort individual slots.
    for n in range(2,31):
        for k in range(3,31):
            for q in range(4,9):
                r = q-1
                weights = []
                for d in range(1,(n-1)//(r-1)+1):
                    weights.extend([(n-1)//d+1-r] * (4*phi(d)*(k//r)))
                expected = sum(sorted(weights,reverse=True)[:k*(k-1)//(r*(r-1))])
                assert line_cover_bound(n,k,q) == expected
            assert line_cover_bound(n,k) <= n*universal_coefficient(k)

    # All subsets of the 4x4 board satisfying the line-only safety condition.
    n = 4
    points = list(product(range(n),repeat=2))
    lines = {curve(t) for t in combinations(points,3) if curve(t)[0] == 0}
    line_records = []
    for c in lines:
        mask = sum(1<<i for i,p in enumerate(points) if on_curve(c,p))
        line_records.append((c,mask))
    checked = 0
    maximal_histogram = Counter()
    for s in range(1 << len(points)):
        intersections = [(c,m,(s&m).bit_count()) for c,m in line_records]
        if any(r >= 4 for c,m,r in intersections):
            continue
        checked += 1
        k = s.bit_count()
        triples = [(c,m) for c,m,r in intersections if r == 3]
        actual_sum = sum(m.bit_count()-3 for c,m in triples)
        assert actual_sum <= line_cover_bound(n,k)
        assert len(triples) <= k*(k-1)//6
        direction_multiplicities = Counter()
        forbidden = 0
        for (a,b,c,d),m in triples:
            # Direction (c,-b), modulo its sign.
            direction = (c,-b)
            if direction[0] < 0 or (direction[0] == 0 and direction[1] < 0):
                direction = (-direction[0],-direction[1])
            direction_multiplicities[direction] += 1
            forbidden |= m
        assert all(count <= k//3 for count in direction_multiplicities.values())
        if (s|forbidden) == (1<<16)-1:
            maximal_histogram[k] += 1
            assert 16-k <= line_cover_bound(n,k)

    finite_bounds = []
    for n in [5,10,11,20,50,100,500,1000]:
        k = next(k for k in range(1,3*n+1) if n*n-k <= line_cover_bound(n,k))
        finite_bounds.append({'n':n, 'line_only_saturation_lower_bound':k,
                             'B_at_k_minus_1':line_cover_bound(n,k-1),
                             'required_coverage_at_k_minus_1':n*n-(k-1)})
    return {'direction_shells_checked':direction_checks,
            'all_4x4_line_safe_subsets_checked':checked,
            '4x4_line_only_maximal_size_histogram':dict(sorted(maximal_histogram.items())),
            'finite_line_only_lower_bounds':finite_bounds,
            'asymptotic_line_cover_coefficient':4/(pi*6**0.5),
            'asymptotic_line_only_saturation_constant':(3*pi*pi/8)**(1/3)}


def audit_exact_searches():
    raw = json.loads((HERE/'saturation_20261003_exact_results.json').read_text())
    # Independent triple-to-curve census, instead of the searcher's all-quad loop.
    n = 11
    points = list(product(range(n),repeat=2))
    curves = Counter(curve(t) for t in combinations(points,3))
    inverse_binomial = {comb(r,3):r for r in range(3,2*n+1)}
    sizes = []
    for c,frequency in curves.items():
        assert frequency in inverse_binomial
        size = inverse_binomial[frequency]
        sizes.append(size)
    quads = sum(comb(r,4) for r in sizes)
    max_completion = max(sizes)-3
    assert quads == 95670 and max_completion == 9
    for record in raw['results']:
        assert record['n'] == 11 and record['complete'] and not record['found']
        assert record['forbidden_quads'] == quads
        assert record['triple_completion_incidence'] == 4*quads
        assert record['max_completion'] == max_completion
        if record['k'] >= 6:
            assert record['nodes_by_depth'][1] == 6
    assert {r['k'] for r in raw['results']} >= {5,6,7}
    assert all(comb(k,3)*max_completion < n*n-k for k in range(3,6))
    return {'independent_curve_count':len(curves), 'quad_count':quads,
            'max_triple_completion':max_completion,
            'completed_stone_counts':[r['k'] for r in raw['results']],
            'inherited_lower_bound':raw['inherited_lower_bound'],
            's11_certified_lower_bound':max(r['k'] for r in raw['results'])+1}


def audit_pair_sum_relaxation():
    ids = [4,7,9,13,19,23,27,30,32,35,42,44,56,58,59,66,70,71,73,81,88,90,98]
    points = [(p%10,p//10) for p in ids]
    directions = []
    for orientation in (0,1):
        groups = [[] for _ in range(10)]
        for p in points:
            groups[p[1-orientation]].append(p[orientation])
        sums = Counter(sum(pair) for group in groups for pair in combinations(group,2))
        assert max(map(len,groups)) <= 3
        assert sums == Counter({s:1 for s in range(1,18)})
        directions.append({'occupancies':list(map(len,groups)), 'pair_sum_counts':dict(sorted(sums.items()))})
    forbidden = [t for t in combinations(points,4) if determinant(t) == 0]
    assert len(forbidden) == 53
    return {'n':10, 'relaxation_optimum':23, 'ids':ids, 'coordinates':points,
            'row_and_column_audits':directions, 'not_a_safe_configuration':True,
            'forbidden_quadruples':forbidden,
            'forbidden_straight_quadruples':sum(curve(t[:3])[0] == 0 for t in forbidden)}


def audit_new_nineteen_family():
    old = [9,15,16,18,20,22,30,36,44,58,62,65,67,70,71,87,91,93,97]
    new = [0,7,8,14,16,20,21,31,35,42,47,67,69,70,73,82,89,93,99]
    assert all(determinant([(p%10,p//10) for p in t]) for t in combinations(old,4))
    overlaps = []
    for reflection in (False,True):
        for rotations in range(4):
            transformed = set()
            for p in old:
                x,y = p%10,p//10
                if reflection:
                    x = 9-x
                for _ in range(rotations):
                    x,y = 9-y,x
                transformed.add(x+10*y)
            overlaps.append(len(set(new)&transformed))
    assert max(overlaps) == 6
    boundary_counts = [sum(p//10 == y for p in new) for y in (0,9)]
    boundary_counts += [sum(p%10 == x for p in new) for x in (0,9)]
    assert min(boundary_counts) >= 2

    union = [2,6,16,18,21,25,32,35,40,59,62,67,74,77,78,80,81,83,97,99]
    bad = [list(t) for t in combinations(union,4)
           if determinant([(p%10,p//10) for p in t]) == 0]
    assert bad == [[25,59,62,83]]
    quad = bad[0]
    base = [p for p in union if p not in quad]
    triples = list(combinations(base,3))
    curves = [curve([(p%10,p//10) for p in t]) for t in triples]
    legal,blockers = [],[]
    for p in range(100):
        if p in base:
            continue
        hits = [i for i,c in enumerate(curves) if on_curve(c,(p%10,p//10))]
        if not hits:
            legal.append(p)
        else:
            i = hits[0]
            assert determinant([(v%10,v//10) for v in triples[i]]+[(p%10,p//10)]) == 0
            blockers.append({'point_id':p,'triple_ids':triples[i],'curve_coefficients':curves[i]})
    assert legal == quad
    family = [[p for p in union if p != removed] for removed in quad]
    assert all(len(set(a)&set(b)) == 18 for a,b in combinations(family,2))
    return {'new_nineteen_maximal':audit_witness(10,new),
            'round57_nineteen_ids':old, 'D4_overlap_counts':overlaps,
            'minimum_exchange_distance_modulo_D4':19-max(overlaps),
            'new_boundary_counts_top_bottom_left_right':boundary_counts,
            'one_obstruction_union_ids':union, 'only_forbidden_quad_ids':quad,
            'quad_circle':curve([(p%10,p//10) for p in quad[:3]]),
            'sixteen_stone_base_ids':base, 'base_legal_ids':legal,
            'base_blocker_certificates':blockers, 'four_pairwise_adjacent_nineteen_maximals':family}


def main():
    witnesses = [
        (11, [5,8,45,50,52,55,58,63,103,115]),
        (12, [6,9,50,55,57,61,64,69,113,126,137]),
        (13, [7,29,41,48,49,54,58,63,84,131,132,163]),
        (14, [17,21,24,37,46,67,119,128,133,135,156,171,182]),
        (15, [7,21,46,60,108,110,115,126,147,172,176,179,186,194]),
    ]
    result = {'claim_scope':'Explicit maximal witnesses give upper bounds only; no exact s_n is asserted.',
              'witnesses':[audit_witness(n,ids) for n,ids in witnesses],
              'line_cover_bound_checks':audit_directions_and_bound(),
              'exact_search_audit':audit_exact_searches(),
              'pair_sum_relaxation_audit':audit_pair_sum_relaxation(),
              'new_nineteen_family_audit':audit_new_nineteen_family(),
              'source_sha256':{name:hashlib.sha256((HERE/name).read_bytes()).hexdigest()
                  for name in ['saturation_20261003_verify.py','saturation_20261003_search.cpp',
                               'saturation_20261003_exact.cpp','saturation_20261003_exact_results.json',
                               '../round56_complete_verified.json','../round56-ten-board-eight-stone-exclusion.md']}}
    out = HERE/'saturation_20261003_verified.json'
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'witnesses':[(r['n'],r['k']) for r in result['witnesses']],
                      'line_only_safe_sets_checked':result['line_cover_bound_checks']['all_4x4_line_safe_subsets_checked'],
                      'output':str(out)}))


if __name__ == '__main__':
    main()
