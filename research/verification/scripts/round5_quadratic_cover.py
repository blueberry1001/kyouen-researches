"""Exact certificates for B074 (false) and B356 (true).

T(t)=(t,2t^3), t=+-1,...,+-N, is safe. Invert about zero and clear
denominators to get integer S_N with b(0)=2*floor((N-1)^2/4).
Translate a second copy by (T,T^2), avoiding all mixed forbidden four-sets.
Universal proofs are in round5-quadratic-cover.md, not inferred from tests.
"""
from itertools import combinations
from math import lcm,prod
from pathlib import Path
import json

from kyouen_core import det4,is_forbidden_quad


def inversion_points(n):
    scale=lcm(*(t*(1+4*t**4) for t in range(1,n+1)))
    points=[]
    params=list(range(-n,0))+list(range(1,n+1))
    for t in params:
        denominator=t*(1+4*t**4)
        assert scale%denominator==0
        x=scale//denominator
        points.append((x,2*t*t*x))
    return params,scale,points


def covering_triples(points,p):
    return [q for q in combinations(points,3) if is_forbidden_quad((*q,p))]


def board_embedding(points,marked):
    all_points=points+marked
    ox=min(x for x,y in all_points)
    oy=min(y for x,y in all_points)
    shifted=[(x-ox,y-oy) for x,y in points]
    special=[(x-ox,y-oy) for x,y in marked]
    side=max(max(x for x,y in shifted+special),max(y for x,y in shifted+special))+1
    return {"n":side,"points":shifted,"empty_points":special,"translation":[-ox,-oy]}


def main():
    result={"single_centre":[],"two_centres":[],"universal_proof_not_finite_extrapolation":True}
    for n in (2,3,4,5,6,8,10,12):
        tt,scale,s=inversion_points(n)
        determinant_checks=0
        for values in combinations(tt,4):
            e=[1]+[sum(prod(c) for c in combinations(values,k)) for k in range(1,5)]
            q=e[1]**2*e[2]-e[2]**2-e[1]*e[3]+e[4]
            vandermonde=prod(b-a for a,b in combinations(values,2))
            matrix=[(t*t+4*t**6,t,2*t**3,1) for t in values]
            assert det4(*matrix)==2*vandermonde*(1-4*q)!=0
            determinant_checks+=1
        for quad in combinations(s,4):
            assert not is_forbidden_quad(quad)
            determinant_checks+=1
        expected=2*((n-1)**2//4)
        triples=covering_triples(s,(0,0))
        assert len(triples)==expected
        parameter_triples=[q for q in combinations(tt,3) if sum(q)==0]
        assert len(parameter_triples)==expected
        result["single_centre"].append({"N":n,"k":len(s),"scale":scale,
            "b":expected,"delta":len(s)*(len(s)-1)//2-3*expected,
            "determinant_checks":determinant_checks,"embedding":board_embedding(s,[(0,0)])})
        print('single',n,'k',len(s),'b',expected,flush=True)
    for n in (4,6,8):
        _,scale,s=inversion_points(n)
        t=1
        attempts=[]
        while True:
            shift=(t,t*t)
            moved=[(x+t,y+t*t) for x,y in s]
            union=s+moved
            if len(set(union))!=len(union) or (0,0) in union or shift in union:
                attempts.append({"T":t,"point_collision":True});t+=1;continue
            bad=None
            checked=0
            for quad in combinations(union,4):
                checked+=1
                if is_forbidden_quad(quad):bad=quad;break
            if bad is None:break
            attempts.append({"T":t,"forbidden_quad":bad});t+=1
        b1=len(covering_triples(union,(0,0)))
        b2=len(covering_triples(union,shift))
        old=2*((n-1)**2//4)
        assert min(b1,b2)>=old
        assert 64*min(b1,b2)>=len(union)**2
        result["two_centres"].append({"N":n,"k":len(union),"T":t,"scale":scale,
            "b_values":[b1,b2],"guaranteed_b":old,"four_sets_checked":checked,
            "rejected_translations":attempts,"embedding":board_embedding(union,[(0,0),shift])})
        print('double',n,'k',len(union),'T',t,'b',b1,b2,flush=True)
    path=Path(__file__).resolve().parents[1]/"round5_quadratic_cover.json"
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(path,flush=True)


if __name__=="__main__":main()
