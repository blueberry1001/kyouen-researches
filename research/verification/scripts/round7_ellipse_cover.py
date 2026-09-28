"""Integer certificates for B357: linearly many quadratically covered empties.

P_t=(2 Re(z^t), Im(z^t)), z=(3+4i)/5. Four distinct P_t are cyclic iff
their exponents sum to zero. S has exponents 1..6m; marked empties have
exponents -q, q=8m+1..9m. All coordinates below are cleared to integers.
The universal proof is in round7-ellipse-cover.md, not a finite extrapolation.
"""
from itertools import combinations
from math import comb
from pathlib import Path
import json

from kyouen_core import is_forbidden_quad
from round5_quadratic_cover import board_embedding


def determinant(points):
    x,y=points[0]
    rows=[(u-x,v-y,(u-x)**2+(v-y)**2) for u,v in points[1:]]
    (a,b,c),(d,e,f),(g,h,i)=rows
    return a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g)


def binom2(n):
    return n*(n-1)//2 if n>=2 else 0


def cover_count(k,q):
    ordered=sum((-1)**j*comb(3,j)*binom2(q-j*k-1) for j in range(4))
    low=max(1,(q-k+1)//2)
    high=min(k,(q-1)//2)
    two_equal=max(0,high-low+1)
    all_equal=int(q%3==0 and 1<=q//3<=k)
    numerator=ordered-3*two_equal+2*all_equal
    assert numerator>=0 and numerator%6==0
    return numerator//6


def coordinates(exponents,maximum):
    powers=[(1,0)]
    for t in range(1,maximum+1):
        a,b=powers[-1]
        powers.append((3*a-4*b,4*a+3*b))
        assert powers[-1][0]%5==3 and powers[-1][1]%5==4
    scale=5**maximum
    result=[]
    for t in exponents:
        a,b=powers[abs(t)]
        factor=5**(maximum-abs(t))
        x,y=2*a*factor,(b if t>=0 else -b)*factor
        assert x*x+4*y*y==4*scale*scale
        result.append((x,y))
    assert len(set(result))==len(result)
    return scale,result


def main():
    output={'universal_proof_not_finite_extrapolation':True,'epsilon':'1/36','examples':[]}
    for m in (1,2,3,4,6,8):
        k=6*m
        sums=list(range(8*m+1,9*m+1))
        exponents=list(range(1,k+1))+[-q for q in sums]
        scale,all_points=coordinates(exponents,9*m)
        stones,marked=all_points[:k],all_points[k:]
        independent=0
        for index,quad in enumerate(combinations(stones,4)):
            assert determinant(quad)!=0
            if index<100:
                assert not is_forbidden_quad(quad)
                independent+=1
        triples=list(combinations(range(k),3))
        observed=[]
        for q,p in zip(sums,marked):
            b=0
            for indices in triples:
                expected=sum(i+1 for i in indices)==q
                actual=determinant([*(stones[i] for i in indices),p])==0
                assert actual==expected
                b+=actual
            assert b==cover_count(k,q)>=m*m
            for u in range(m+1,2*m+1):
                for v in range(2*m+1,3*m+1):
                    t=q-u-v
                    assert 3*m+1<=t<=6*m and u<v<t
            observed.append(b)
        # Full combinatorial profile, independently from the closed formula.
        census=[0]*(3*k+1)
        for triple in combinations(range(1,k+1),3):
            census[sum(triple)]+=1
        assert all(census[q]==cover_count(k,q) for q in range(3*k+1))
        assert sum(census)==comb(k,3)
        row=dict(m=m,k=k,scale=scale,high_point_count=m,
                 marked_sum_parameters=sums,b_values=observed,guaranteed_b=m*m,
                 safety_quadruples_checked=comb(k,4),cover_quadruples_checked=m*comb(k,3),
                 independent_core_checks=independent,
                 full_ellipse_profile={str(q):b for q,b in enumerate(census) if b},
                 embedding=board_embedding(stones,marked))
        output['examples'].append(row)
        print('m',m,'k',k,'high points',m,'b range',min(observed),max(observed),flush=True)
    target=Path(__file__).resolve().parents[1]/'round7_ellipse_cover.json'
    target.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(target,flush=True)


if __name__=='__main__':
    main()
