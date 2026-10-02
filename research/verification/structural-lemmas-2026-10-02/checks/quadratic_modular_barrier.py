"""Reproduce the quadratic modular construction and its exact small cases.

No third-party packages or repository solver are required.
The general upper bound is proved in the accompanying report via
Dias da Silva--Hamidoune; these checks are finite cross-checks only.
"""
from itertools import combinations
from math import comb, prod
from pathlib import Path
import hashlib
import json
import random


def prime(n):
    return n >= 2 and all(n % d for d in range(2, int(n**0.5) + 1))


def det4(points):
    """Integer determinant with columns [1,x,y,x*x+y*y]."""
    x0, y0 = points[0]
    q0 = x0*x0 + y0*y0
    rows = [(x-x0, y-y0, x*x+y*y-q0) for x, y in points[1:]]
    (a,b,c),(d,e,f),(g,h,i) = rows
    return a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g)


def quad_points(p, u, v, w, params):
    return [tuple((u[j]*t*t + v[j]*t + w[j]) % p for j in range(2)) for t in params]


def check_identity():
    rng = random.Random(20261002)
    tests = 0
    for p in (5,7,11,13,19,29,31):
        for _ in range(100):
            u, v, w = [tuple(rng.randrange(p) for _ in range(2)) for _ in range(3)]
            ts = rng.sample(range(p), 4)
            pts = quad_points(p,u,v,w,ts)
            factor = v[0]*u[1]-v[1]*u[0]
            bracket = (u[0]*u[0]+u[1]*u[1])*sum(ts)+2*(u[0]*v[0]+u[1]*v[1])
            vand = prod(ts[j]-ts[i] for i in range(4) for j in range(i+1,4))
            assert (det4(pts)-factor*bracket*vand) % p == 0
            tests += 1
    return tests


def construction_checks():
    records=[]
    for p in range(5,128):
        if not prime(p):
            continue
        m=(p+14)//4
        ts=list(range(-1,m-1))
        pts=[(t%p,t*t%p) for t in ts]
        assert len(set(pts)) == m
        for inds in combinations(range(m),4):
            vals=[ts[i] for i in inds]
            d=det4([pts[i] for i in inds])
            assert 2 <= sum(vals) <= p-1
            assert d % p != 0
            assert (d-sum(vals)*prod(vals[j]-vals[i] for i in range(4) for j in range(i+1,4))) % p == 0
        records.append({'p':p,'size':m,'parameters':ts,'coordinates':pts,'four_point_checks':comb(m,4)})
    return records


def maximum_subset(p, modular):
    pts=[(t,t*t%p) for t in range(p)]
    edges=[]
    for ids in combinations(range(p),4):
        d=det4([pts[i] for i in ids])
        if (d % p == 0) if modular else (d == 0):
            edges.append(sum(1<<i for i in ids))
    for k in range(p,2,-1):
        examined=0
        for inds in combinations(range(p),k):
            examined+=1
            mask=sum(1<<i for i in inds)
            if not any(mask&e==e for e in edges):
                return {'p':p,'modular':modular,'maximum':k,'parameters':list(inds),'coordinates':[pts[i] for i in inds], 'forbidden_quadruples':len(edges)}
    raise AssertionError('Every three distinct points must be safe')


def main():
    records=construction_checks()
    out={'identity_checks':check_identity(),
         'construction_records':records,
         'total_construction_four_point_checks':sum(r['four_point_checks'] for r in records),
         'exact_small_maxima':[maximum_subset(p,modular) for p in (5,7,11,19) for modular in (True,False)],
         'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    Path(__file__).with_suffix('.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in out.items() if k!='construction_records'},indent=2))


if __name__=='__main__':
    main()
