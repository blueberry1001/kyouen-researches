"""Exact auxiliary geometry for round9 certificates; no external packages."""
from itertools import combinations
from math import gcd


def normalize(values):
    divisor = 0
    for v in values:
        divisor = gcd(divisor, v)
    values = tuple(v//divisor for v in values)
    first = next(v for v in values if v)
    return tuple(-v for v in values) if first < 0 else values


def curve(triple):
    """Primitive (a,b,c,d) for a(x*x+y*y)+b*x+c*y+d=0, a>=0."""
    (x,y),(u,v),(s,t) = triple
    u,v,s,t = u-x,v-y,s-x,t-y
    a = u*t-v*s
    if a == 0:
        b,c = v,-u
        return normalize((0,b,c,-b*x-c*y))
    b = (s*s+t*t)*v-(u*u+v*v)*t
    c = (u*u+v*v)*s-(s*s+t*t)*u
    return normalize((a,b-2*a*x,c-2*a*y,a*(x*x+y*y)-b*x-c*y))


def evaluate(coefficients, point):
    a,b,c,d = coefficients
    x,y = point
    return a*(x*x+y*y)+b*x+c*y+d


def curves(stones):
    result = {curve(t) for t in combinations(stones, 3)}
    assert len(result) == len(list(combinations(stones, 3)))
    return result


def determinant(points):
    x,y = points[0]
    rows = [(u-x,v-y,(u-x)**2+(v-y)**2) for u,v in points[1:]]
    (a,b,c),(d,e,f),(g,h,i) = rows
    return a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g)
