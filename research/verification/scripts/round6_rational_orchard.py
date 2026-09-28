"""Exact checks accompanying round6-rational-orchard.md.

The universal results use Green--Tao and Mazur, not these finite checks.
Only Python standard-library rational/integer arithmetic is used here.
"""
from collections import Counter
from fractions import Fraction as F
from itertools import combinations
from math import comb, gcd, isqrt, lcm
from pathlib import Path
import json

from kyouen_core import det4, is_forbidden_quad
from round5_quadratic_cover import board_embedding, inversion_points


def canonical_line(a, b):
    x, y = a
    u, v = b
    raw = (y-v, u-x, x*v-y*u)
    scale = lcm(*(F(z).denominator for z in raw))
    ints = [int(z*scale) for z in raw]
    divisor = gcd(*ints)
    ints = [z//divisor for z in ints]
    if next(z for z in ints if z) < 0:
        ints = [-z for z in ints]
    return tuple(ints)


def line_census(points):
    lines = {canonical_line(a, b) for a, b in combinations(points, 2)}
    counts = Counter(sum(a*x+b*y+c == 0 for x, y in points)
                     for a, b, c in lines)
    assert sum(comb(n, 2)*v for n, v in counts.items()) == comb(len(points), 2)
    return counts


def invert(points, p=(0, 0)):
    answer = []
    for x, y in points:
        x, y = x-p[0], y-p[1]
        norm = x*x+y*y
        assert norm
        answer.append((F(x)/norm, F(y)/norm))
    return answer


def assert_safe(points):
    for q in combinations(points, 4):
        assert not is_forbidden_quad(q), q
    return comb(len(points), 4)


def coefficients(quad):
    return tuple(det4(*[(x, y, fn(x, y), 1) for x, y in quad])
                 for fn in (lambda x,y: x*x, lambda x,y: x*y, lambda x,y: y*y))


def shear(points, s):
    return [(x+s*y, s*s*y) for x, y in points]


def make_safe(points):
    coeffs = [coefficients(q) for q in combinations(points, 4)]
    assert all(any(c) for c in coeffs)
    for s in range(1, 4*comb(len(points), 4)+2):
        if all(dx+2*s*dxy+(s*s+s**4)*dy for dx, dxy, dy in coeffs):
            transformed = shear(points, s)
            assert_safe(transformed)
            return s, transformed
    raise AssertionError('finite-root bound failed')


def elliptic_add(p, q, a2, a4):
    if p is None:
        return q
    if q is None:
        return p
    x, y = p
    u, v = q
    if x == u and y == -v:
        return None
    if p == q:
        slope = F(3*x*x+2*a2*x+a4, 2*y)
    else:
        slope = F(v-y, u-x)
    xx = slope*slope-a2-x-u
    return (xx, -y+slope*(x-xx))


def torsion_example(a2, a4, a6, expected):
    group = [None]
    for x in range(-400, 1001):
        rhs = x**3+a2*x*x+a4*x+a6
        if rhs < 0:
            continue
        y = isqrt(rhs)
        if y*y == rhs:
            group.append((F(x), F(y)))
            if y:
                group.append((F(x), F(-y)))
    assert len(group) == expected
    members = set(group)
    for p in group:
        for q in group:
            assert elliptic_add(p, q, a2, a4) in members
    homogeneous = [(F(0), F(1), F(0)) if p is None else (*p, F(1)) for p in group]
    chart = 1
    while any(x+chart*y+chart*chart*z == 0 for x,y,z in homogeneous):
        chart += 1
    affine = [(x/(x+chart*y+chart*chart*z), y/(x+chart*y+chart*chart*z))
              for x,y,z in homogeneous]
    original = line_census(affine)
    assert max(original) <= 3
    expected_delta = expected-1-2*int(expected % 3 == 0)
    assert original[2] == expected_delta
    s, safe = make_safe(affine)
    assert line_census(safe) == original
    shift = 1
    while (-shift, -shift*shift) in safe:
        shift += 1
    moved = [(x+shift,y+shift*shift) for x,y in safe]
    rational = invert(moved)
    scale = lcm(*(z.denominator for p in rational for z in p))
    integer = [tuple(int(z*scale) for z in p) for p in rational]
    checks = assert_safe(integer)
    covers = [idx for idx in combinations(range(expected),3)
              if is_forbidden_quad([integer[j] for j in idx]+[(0,0)])]
    assert len(covers) == original[3]
    assert comb(expected,2)-3*len(covers) == expected_delta
    return dict(k=expected, elliptic_coefficients=[a2,a4,a6],
                projective_chart=chart, shear_parameter=s, translation_parameter=shift,
                scale=scale, b=len(covers), delta=expected_delta,
                four_sets_checked=checks, subgroup_additions_checked=expected**2,
                covering_index_triples=covers, embedding=board_embedding(integer,[(0,0)]))


def main():
    out = dict(universal_proof_not_finite_extrapolation=True,
               inversion_checks=[], torsion_examples=[])
    for n in (2,3,4,6,8,10,12):
        _, _, points = inversion_points(n)
        for p in ((0,0),(1,0),(2,3)):
            inv = invert(points, p)
            census = line_census(inv)
            assert max(census) <= 3
            b = sum(is_forbidden_quad([*q,p]) for q in combinations(points,3))
            delta = comb(len(points),2)-3*b
            assert b == census[3] and delta == census[2]
            out['inversion_checks'].append(dict(N=n,k=len(points),p=p,b=b,delta=delta,
                                                line_multiplicities=dict(census)))
    points = [(x,y) for x in range(3) for y in range(3)]
    checks = 0
    for q in combinations(points,4):
        dx,dxy,dy = coefficients(q)
        assert (dx,dxy,dy) != (0,0,0)
        for s in (1,2,3,5):
            got = det4(*[(x,y,x*x+y*y,1) for x,y in shear(q,s)])
            assert got == s*s*(dx+2*s*dxy+(s*s+s**4)*dy)
            checks += 1
    s, safe = make_safe(points)
    assert line_census(safe) == line_census(points)
    out['affine_formula'] = dict(quadruples=comb(9,4), substitutions_checked=checks,
                                safe_parameter=s, safe_integer_points=safe)
    for coefficients_, size in (((0,0,1),6), ((337,20736,0),16)):
        example = torsion_example(*coefficients_,size)
        out['torsion_examples'].append(example)
        print('rational torsion witness',size,'b',example['b'],'delta',example['delta'],flush=True)
    target = Path(__file__).resolve().parents[1]/'round6_rational_orchard.json'
    target.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('inversion identities',len(out['inversion_checks']),'affine checks',checks,flush=True)
    print(target,flush=True)


if __name__ == '__main__':
    main()
