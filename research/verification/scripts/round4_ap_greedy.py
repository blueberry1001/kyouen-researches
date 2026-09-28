"""Construct safe row-wise APs with common difference one by exact roots.

The cubic bound is proved in round4-ap-construction.md; this is not a proof of
B558's quadratic bound. All forbidden starts come from 3 old + 1 new or
2 old + 2 new points. No float operations, search cutoffs, or dependencies.
"""
from itertools import combinations
from math import comb,isqrt
from pathlib import Path
import json

from kyouen_core import is_forbidden_quad


def integer_roots(a,b,c):
    if a==0:
        assert b!=0 or c!=0, "Identically zero constraint is not allowed"
        return {-c//b} if b and (-c)%b==0 else set()
    disc=b*b-4*a*c
    if disc<0:return set()
    root=isqrt(disc)
    if root*root!=disc:return set()
    return {num//(2*a) for num in (-b+root,-b-root) if num%(2*a)==0}


def triple_roots_on_row(triple,row):
    (x1,y1),(x2,y2),(x3,y3)=triple
    dx2,dy2=x2-x1,y2-y1
    dx3,dy3=x3-x1,y3-y1
    dq2=x2*x2+y2*y2-x1*x1-y1*y1
    dq3=x3*x3+y3*y3-x1*x1-y1*y1
    a=dx2*dy3-dx3*dy2
    b=dq3*dy2-dq2*dy3
    c=dq2*dx3-dq3*dx2
    d=-a*(x1*x1+y1*y1)-b*x1-c*y1
    return integer_roots(a,b,a*row*row+c*row+d)


def pair_start_roots(pair,row,i,j):
    (x1,y1),(x2,y2)=pair
    y1-=row
    y2-=row
    a=y2-y1
    b=y2*(i+j-2*x1)-y1*(i+j-2*x2)
    c=y2*((x1-i)*(x1-j)+y1*y1)-y1*((x2-i)*(x2-j)+y2*y2)
    return integer_roots(a,b,c)


def construct(width):
    points=[]
    data=[]
    for r in range(width):
        blocked=set()
        for triple in combinations(points,3):
            for x in triple_roots_on_row(triple,r):
                blocked.update(x-i for i in (0,1,2))
        for pair in combinations(points,2):
            for i,j in combinations((0,1,2),2):
                blocked.update(pair_start_roots(pair,r,i,j))
        bound=6*comb(3*r+1,3)-15*r if r else 0
        assert len(blocked)<=bound,(r,len(blocked),bound)
        start=0
        while start in blocked:start+=1
        assert start<=bound
        points.extend((start+i,r) for i in (0,1,2))
        data.append({"row":r,"start":start,"blocked_integer_starts":len(blocked),
                     "blocked_start_upper_bound":bound,
                     "running_board_length":max(x for x,y in points)+1})
    return points,data


def main():
    points,rows=construct(20)
    # Independent check of every four-set in the largest constructed prefix.
    quads=0
    for q in combinations(points,4):
        assert not is_forbidden_quad(q),q
        quads+=1
    # Independently check the root formulas on all small prefixes/nearby starts.
    root_checks=0
    for row in range(1,5):
        old=[p for p in points if p[1]<row]
        for triple in combinations(old,3):
            roots=triple_roots_on_row(triple,row)
            for x in range(-3,20):
                assert (x in roots)==is_forbidden_quad((*triple,(x,row)))
                root_checks+=1
        for pair in combinations(old,2):
            for i,j in combinations((0,1,2),2):
                roots=pair_start_roots(pair,row,i,j)
                for start in range(-3,20):
                    assert (start in roots)==is_forbidden_quad((*pair,(start+i,row),(start+j,row)))
                    root_checks+=1
    result={"w":20,"points":points,"row_records":rows,
            "all_quadruples_checked":quads,"root_formula_checks":root_checks,
            "bound":"3 + 6*C(3*w-2,3) - 15*(w-1)",
            "quadratic_bound_proved":False}
    path=Path(__file__).resolve().parents[1]/"round4_ap_greedy.json"
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print('row starts',[row['start'] for row in rows])
    print('prefix board lengths',[row['running_board_length'] for row in rows])
    print('four-set checks',quads,'root checks',root_checks)


if __name__=="__main__":main()
