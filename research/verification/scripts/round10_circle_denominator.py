"""B453 Gaussian-integer upper bounds for a fixed exact center denominator.

Checks every occupied primitive residue class for norms 1..3000 and q=1..16.
No floating-point arithmetic or inference from finite maxima.
"""
from collections import defaultdict
from math import gcd,isqrt
from pathlib import Path
import json


def factor(n):
    out={};p=2
    while p*p<=n:
        while n%p==0:out[p]=out.get(p,0)+1;n//=p
        p+=1
    if n>1:out[n]=out.get(n,0)+1
    return out


def representations(n):
    out=set()
    for x in range(-isqrt(n),isqrt(n)+1):
        y=isqrt(n-x*x)
        if y*y==n-x*x:
            out.update(((x,y),(x,-y)))
    return out


def multiplier(q,a,b):
    if q==1:return 4
    if q==2:return 4 if a%2 and b%2 else 2
    return 1


def bound(factors,q,a,b):
    value=multiplier(q,a,b)
    for p,e in factors.items():
        if p%4==1 and q%p:value*=e+1
    return value


def mul(z,w):
    a,b=z;c,d=w
    return a*c-b*d,a*d+b*c


def main():
    count=0;exact_small=0;exact_q34=0;all_q34_classes=0
    first_four={};max_observed=defaultdict(int);first_ge={3:{},4:{}}
    for n in range(1,3001):
        ff=factor(n)
        rr=representations(n)
        expected=4
        for p,e in ff.items():
            if p%4==3 and e%2:expected=0
            if p%4==1:expected*=e+1
        assert len(rr)==expected
        for q in range(1,17):
            classes=defaultdict(list)
            for u,v in rr:
                a,b=(-u)%q,(-v)%q
                if gcd(gcd(a,b),q)==1:classes[(a,b)].append((u,v))
            for (a,b),zs in classes.items():
                upper=bound(ff,q,a,b)
                assert len(zs)<=upper
                if q<=2:
                    assert len(zs)==upper
                    exact_small+=1
                if q in (3,4):
                    assert len(zs)==upper==len(rr)//4
                    exact_q34+=1
                    for target in range(1,len(zs)+1):
                        first_ge[q].setdefault(target,n)
                for p in factor(q):
                    if p%4==3:assert n%p!=0
                if q%2==0:assert ff.get(2,0)==int(a%2 and b%2)
                count+=1
                max_observed[q]=max(max_observed[q],len(zs))
                if len(zs)>=4 and q not in first_four:
                    first_four[q]={'norm':n,'center_numerator':[a,b],'q':q,
                                   'radius_squared':f'{n}/{q*q}',
                                   'points':sorted(((u+a)//q,(v+b)//q) for u,v in zs)}
            if q in (3,4):
                modulus=3 if q==3 else 8
                for a in range(q):
                    for b in range(q):
                        if gcd(gcd(a,b),q)!=1:continue
                        compatible=(n-a*a-b*b)%modulus==0
                        predicted=len(rr)//4 if compatible else 0
                        assert len(classes.get((a,b),[]))==predicted
                        all_q34_classes+=1
    assert first_four[3]['norm']==first_four[4]['norm']==65
    explicit=[]
    for q,a,b in ((3,1,1),(4,1,0)):
        pts=sorted(((u+a)//q,(v+b)//q) for u,v in representations(65)
                   if (u+a)%q==0 and (v+b)%q==0)
        assert len(pts)==4
        explicit.append({'q':q,'center_numerator':[a,b],'norm':65,'points':pts})
    families=[]
    for q in (1,2,3,4,5,6,8,10,12):
        d=max(2,q)
        assert d%q==0
        for n in range(1,9):
            points=[]
            for j in range(n+1):
                z=(-1,0)
                for _ in range(j):z=mul(z,(1,d))
                for _ in range(n-j):z=mul(z,(1,-d))
                u,v=z
                assert (u+1)%q==0 and v%q==0
                p=((u+1)//q,v//q)
                assert (q*p[0]-1)**2+(q*p[1])**2==(1+d*d)**n
                points.append(p)
            assert len(set(points))==n+1
            families.append({'q':q,'power':n,'d':d,'guaranteed_points':points,
                             'radius_squared_numerator':(1+d*d)**n,'radius_squared_denominator':q*q})
    assert first_ge[3]==first_ge[4]
    split_minima={}
    for n in range(1,3001):
        ff=factor(n)
        if any(p%4!=1 for p in ff):continue
        divisor_count=1
        for e in ff.values():divisor_count*=e+1
        for target in range(1,divisor_count+1):split_minima.setdefault(target,n)
    assert first_ge[3]==split_minima
    result={'B453':'SUPPORTED','norm_limit':3000,'denominators_checked':list(range(1,17)),
            'primitive_residue_classes_checked':count,'q1_q2_exact_count_checks':exact_small,
            'q3_q4_occupied_exact_count_checks':exact_q34,
            'q3_q4_all_primitive_class_checks':all_q34_classes,
            'q3_q4_common_minimum_norms_at_least_m':first_ge[3],
            'observed_maxima_not_universal_bounds':dict(max_observed),
            'first_four_point_examples_within_scan':first_four,
            'exact_q3_q4_threshold_witnesses':explicit,'fixed_center_unbounded_family_checks':families}
    path=Path(__file__).resolve().parents[1]/'round10_circle_denominator.json'
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('primitive classes',count,'q1/q2 exact checks',exact_small)
    print('exact threshold witnesses',explicit)
    print(path)


if __name__=='__main__':main()
