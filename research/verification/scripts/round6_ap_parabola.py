"""B558 candidate audit, NOT a proof for unbounded row span.

Enumerate all four-point row-offset/column-label patterns of bounded span.
For each pattern solve the concyclicity polynomial in the common integer
parameter shift h exactly. Thus h is unbounded, but row span is bounded.
"""
import argparse
from collections import Counter
from itertools import combinations_with_replacement, product
from math import comb, isqrt
from pathlib import Path
import json

from kyouen_core import det4


def circle_determinant(points):
    x,y = points[0]
    rows = [(u-x,v-y,(u-x)**2+(v-y)**2) for u,v in points[1:]]
    (a,b,c),(d,e,f),(g,h,i) = rows
    return a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g)


def polynomial(a, rows, labels):
    values = [circle_determinant([(a*(r+h)**2+j,r) for r,j in zip(rows,labels)])
              for h in (0,1,2)]
    constant = values[0]
    assert (values[2]-2*values[1]+constant) % 2 == 0
    quadratic = (values[2]-2*values[1]+constant)//2
    linear = values[1]-constant-quadratic
    assert (quadratic,linear,constant) != (0,0,0)
    return quadratic,linear,constant


def integer_roots(a,b,c):
    if a == 0:
        return [-c//b] if b and c % b == 0 else []
    discriminant = b*b-4*a*c
    if discriminant < 0:
        return []
    root = isqrt(discriminant)
    if root*root != discriminant:
        return []
    return sorted({z//(2*a) for z in (-b+root,-b-root) if z % (2*a) == 0})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--span',type=int,default=39)
    parser.add_argument('--coefficient',type=int,default=2)
    args = parser.parse_args()
    assert args.span >= 1 and args.coefficient >= 2
    a = args.coefficient
    labels_all = [q for q in product(range(3),repeat=4) if min(q) == 0]
    by_rows = Counter()
    degrees = Counter()
    roots_below_family = Counter()
    first_below = []
    family_counterexamples = []
    determinant_checks = 0
    total = 0
    for span in range(1,args.span+1):
        for r1,r2 in combinations_with_replacement(range(span+1),2):
            rr = (0,r1,r2,span)
            for jj in labels_all:
                if any(rr[i] == rr[i+1] and jj[i] >= jj[i+1] for i in range(3)):
                    continue
                aa,bb,cc = polynomial(a,rr,jj)
                by_rows[len(set(rr))] += 1
                degrees[2 if aa else 1 if bb else 0] += 1
                total += 1
                # Sparse independent expansion checks, including extrapolation
                # beyond the interpolation nodes h=0,1,2.
                if total % 997 == 1:
                    for h in (-3,3,17):
                        pts = [(a*(r+h)**2+j,r) for r,j in zip(rr,jj)]
                        full = det4(*[(x*x+y*y,x,y,1) for x,y in pts])
                        expected = aa*h*h+bb*h+cc
                        # First-row subtraction leaves the last-column cofactor
                        # with negative sign in the 4x4 expansion.
                        assert full == -circle_determinant(pts) == -expected
                        determinant_checks += 1
                for h in integer_roots(aa,bb,cc):
                    record = dict(h=h,row_offsets=rr,labels=jj,polynomial=[aa,bb,cc])
                    if h >= span+1:
                        pts = [(a*(r+h)**2+j,r) for r,j in zip(rr,jj)]
                        assert circle_determinant(pts) == 0
                        family_counterexamples.append(record)
                    else:
                        roots_below_family['nonnegative' if h >= 0 else 'negative'] += 1
                        if len(first_below) < 12:
                            first_below.append(record)
        if span % 10 == 0:
            print('span',span,'patterns',total,'counterexamples',len(family_counterexamples),flush=True)
    out = dict(candidate='x=a*(r+w)^2+j-a*w^2; j=0,1,2; r=0,...,w-1',
               coefficient=a,max_row_span=args.span,
               shift_range='ALL integer h >= span+1, solved exactly as polynomial roots',
               normalized_patterns=total,patterns_by_distinct_rows=dict(by_rows),
               polynomial_degrees=dict(degrees),independent_determinant_checks=determinant_checks,
               roots_below_family=dict(roots_below_family),first_roots_below_family=first_below,
               family_counterexamples=family_counterexamples,
               verified_w_max=args.span+1 if not family_counterexamples else None,
               status='PARTIAL; unbounded row span NOT proved',complete=True)
    target = Path(__file__).resolve().parents[1]/f'round6_ap_parabola_a{a}_span{args.span}.json'
    target.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('complete',total,'counterexamples',len(family_counterexamples),target,flush=True)


if __name__ == '__main__':
    main()
