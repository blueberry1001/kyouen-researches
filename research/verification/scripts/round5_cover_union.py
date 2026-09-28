"""Equal-size safe configurations with quadratic b but unbounded coverage ratio.

This verifies finite certificates for the universal proof in
round5-cover-union.md. No large board is enumerated: the finite-circle upper
bound and the horizontal-line lower bound certify any requested ratio.
"""
from itertools import combinations
from math import isqrt
from pathlib import Path
import json

from kyouen_core import is_forbidden_quad
from round5_quadratic_cover import inversion_points,covering_triples,board_embedding


def collinear(q):
    (x1,y1),(x2,y2),(x3,y3)=q
    return (x2-x1)*(y3-y1)==(x3-x1)*(y2-y1)


def augment(base,block,avoid_triples):
    t=1
    while True:
        points=base+[(x+t,y+t*t) for x,y in block]
        if len(set(points))!=len(points) or (0,0) in points:t+=1;continue
        if avoid_triples and any(collinear(q) for q in combinations(points,3)):
            t+=1;continue
        if any(is_forbidden_quad(q) for q in combinations(points,4)):
            t+=1;continue
        return t,points


def all_circle_lattice_upper_bound(points):
    bound=0
    for (x1,y1),(x2,y2),(x3,y3) in combinations(points,3):
        dx2,dy2=x2-x1,y2-y1
        dx3,dy3=x3-x1,y3-y1
        dq2=x2*x2+y2*y2-x1*x1-y1*y1
        dq3=x3*x3+y3*y3-x1*x1-y1*y1
        a=dx2*dy3-dx3*dy2
        assert a!=0
        b=dq3*dy2-dq2*dy3
        c=dq2*dx3-dq3*dx2
        d=-a*(x1*x1+y1*y1)-b*x1-c*y1
        num,den=b*b+c*c-4*a*d,4*a*a
        radius=isqrt(num//den)
        if radius*radius*den<num:radius+=1
        bound+=4*radius+2
    return bound


def main():
    result=[]
    for n in (4,5,6):
        _,scale,base=inversion_points(n)
        assert not any(collinear(q) for q in combinations(base,3))
        ta,a=augment(base,[(0,0),(1,0),(0,1)],True)
        tb,b=augment(base,[(0,0),(1,0),(2,0)],False)
        k=len(a)
        assert k==len(b)==2*n+3
        ba,bb=len(covering_triples(a,(0,0))),len(covering_triples(b,(0,0)))
        assert min(ba,bb)>=2*((n-1)**2//4)
        assert 32*min(ba,bb)>=k*k
        upper=all_circle_lattice_upper_bound(a)
        ea,eb=board_embedding(a,[(0,0)]),board_embedding(b,[(0,0)])
        width=max(ea['n'],eb['n'],10*upper+4)
        assert len({y for x,y in eb['points'][-3:]})==1
        horizontal_y=eb['points'][-1][1]
        assert sum(y==horizontal_y for x,y in eb['points'])==3
        assert width-3>10*upper
        result.append({'N':n,'k':k,'base_scale':scale,'translation_parameters':[ta,tb],
            'b_at_marked_empty_points':[ba,bb],'A_embedding':ea,'B_embedding':eb,
            'A_all_lattice_forbidden_upper_bound':upper,
            'example_common_board_width':width,'guaranteed_ratio_strictly_greater_than':10,
            'B_horizontal_line_y':horizontal_y})
        print('N',n,'k',k,'T',ta,tb,'b',ba,bb,'bound digits',len(str(upper)),flush=True)
    path=Path(__file__).resolve().parents[1]/'round5_cover_union.json'
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(path,flush=True)


if __name__=='__main__':main()
