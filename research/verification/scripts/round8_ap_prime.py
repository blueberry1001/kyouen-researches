"""Exact certificates for the universal quadratic-width AP construction B558.

For w>=2 choose prime p>16(w-1)^2+1, and use (2r^2+jp,r), j=0,1,2.
No four points are collinear or concyclic. Proof: round8-ap-quadratic-prime.md.
"""
from itertools import combinations, product
from math import comb, isqrt, prod
from pathlib import Path
import json

from kyouen_core import is_forbidden_quad
from round7_ellipse_cover import determinant


def is_prime(n):
    return n >= 2 and all(n%d for d in range(2, isqrt(n)+1))


def construct(w):
    if w == 1:
        return 1, [(0, 0), (1, 0), (2, 0)]
    bound = 16*(w-1)**2+1
    p = bound+1
    while not is_prime(p):
        p += 1
    assert bound < p <= 2*bound
    points = [(2*r*r+j*p, r) for r in range(w) for j in range(3)]
    return p, points


def repeated_row_identity_audit():
    count = 0
    for a in (2, 3, 5):
        p = 997
        for r in range(7):
            for s, t in combinations([v for v in range(7) if v != r], 2):
                for u, v in combinations(range(3), 2):
                    for c, d in product(range(3), repeat=2):
                        points = [(a*r*r+u*p,r), (a*r*r+v*p,r),
                                  (a*s*s+c*p,s), (a*t*t+d*p,t)]
                        value = determinant(points)
                        divisor = (v-u)*p
                        f = a*a*(s*s+s*t+t*t+r*(s+t)-r*r)+1
                        expected = (s-r)*(t-r)*(t-s)*f
                        assert value%divisor == 0
                        assert (value//divisor-expected)%p == 0
                        count += 1
    return count


def main():
    result = {'universal_proof_not_finite_extrapolation': True,
              'status_B558': 'SUPPORTED',
              'construction': '(2*r*r+j*p,r); r=0..w-1; j=0,1,2',
              'prime_condition': '16*(w-1)^2+1 < p <= 32*(w-1)^2+2',
              'width_bound': '66*(w-1)^2+5 for w>=2; 3 for w=1',
              'repeated_row_formula_checks': repeated_row_identity_audit(),
              'examples': []}
    for w in range(1, 21):
        p, points = construct(w)
        width = max(x for x,y in points)+1
        assert len(set(points)) == 3*w
        assert width <= 66*(w-1)**2+5
        for r in range(w):
            xs = [x for x,y in points if y==r]
            assert len(xs)==3 and xs[1]-xs[0]==xs[2]-xs[1]==p
        by_rows = [0]*5
        independent_checks = 0
        for quad in combinations(points, 4):
            rows = [y for x,y in quad]
            distinct = len(set(rows))
            by_rows[distinct] += 1
            value = determinant(quad)
            assert value != 0
            if distinct == 4:
                expected = -8*sum(rows)*prod(rows[j]-rows[i] for i in range(4) for j in range(i+1,4))
                assert (value-expected)%p == 0 and expected%p != 0
            if independent_checks < 100:
                assert not is_forbidden_quad(quad)
                independent_checks += 1
        result['examples'].append({'w': w, 'p': p, 'width': width, 'stone_count': 3*w,
                                   'all_quadruples_checked': comb(3*w,4),
                                   'quadruples_by_distinct_rows': by_rows,
                                   'independent_core_checks': independent_checks, 'points': points})
        print(f'w={w} p={p} width={width} quads={comb(3*w,4)} safe', flush=True)
    result['total_quadruples_checked'] = sum(e['all_quadruples_checked'] for e in result['examples'])
    target = Path(__file__).resolve().parents[1]/'round8_ap_prime.json'
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(target, flush=True)


if __name__ == '__main__':
    main()
