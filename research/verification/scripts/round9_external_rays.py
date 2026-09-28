"""B388 exact certificates: bounded circle part and eventual line counting.

escape_without_circles uses only pair directions and the squared diameter.
Circle enumeration below is an independent, finite verification step.
"""
from collections import defaultdict
from fractions import Fraction
from itertools import combinations
from math import gcd, isqrt, lcm, comb
from pathlib import Path
import json
import struct

from round9_geometry import curve, evaluate, determinant


def ceildiv(a,b):
    return -((-a)//b)


def bbox(stones):
    return min(x for x,y in stones),max(x for x,y in stones),min(y for x,y in stones),max(y for x,y in stones)


def distance(p,box):
    x,y=p; x0,x1,y0,y1=box
    return max(0,x0-x,x-x1,y0-y,y-y1)


def direction(u,v):
    a,b=v[0]-u[0],v[1]-u[1]
    g=gcd(a,b); a,b=a//g,b//g
    if a<0 or (a==0 and b<0): a,b=-a,-b
    return a,b


def triple_lines_by_pairs(stones):
    lines=set()
    for p in stones:
        grouped=defaultdict(list)
        for q in stones:
            if p!=q: grouped[direction(p,q)].append(q)
        for neighbors in grouped.values():
            assert len(neighbors)<=2
            if len(neighbors)==2: lines.add(curve([p,*neighbors]))
    return sorted(lines)


def escape_without_circles(stones):
    box=bbox(stones)
    q=max((x-u)**2+(y-v)**2 for x,y in stones for u,v in stones)
    cutoff=isqrt(q**3)+1
    lines=triple_lines_by_pairs(stones)
    nonhorizontal=[z for z in lines if z[1]!=0]
    y=box[3]+cutoff
    x0=box[0]
    blocked=set()
    for _,a,b,c in nonhorizontal:
        numerator=-b*y-c
        if numerator%a==0:
            x=numerator//a
            if x0<=x<=x0+len(nonhorizontal): blocked.add(x)
    x=next(x for x in range(x0,x0+len(nonhorizontal)+1) if x not in blocked)
    p=(x,y)
    assert all(evaluate(line,p) for line in lines)
    return {'squared_diameter':q,'circle_cutoff':cutoff,'escape_point':p,
            'escape_distance':distance(p,box),'lines':lines,
            'nonhorizontal_line_count':len(nonhorizontal)}


def circle_points(coeff):
    a,b,c,d=coeff
    assert a>0
    delta=b*b+c*c-4*a*d
    assert delta>0
    root=isqrt(delta)
    result=set()
    for x in range(ceildiv(-root-b,2*a),(root-b)//(2*a)+1):
        remaining=delta-(2*a*x+b)**2
        if remaining<0: continue
        v=isqrt(remaining)
        if v*v!=remaining: continue
        for signed in {v,-v}:
            if (signed-c)%(2*a)==0:
                p=(x,(signed-c)//(2*a))
                assert evaluate(coeff,p)==0
                result.add(p)
    return result


def line_parameters(line,stones):
    _,a,b,c=line
    v=(b,-a)
    assert gcd(*v)==1
    if v[0]<0 or (v[0]==0 and v[1]<0): v=(-v[0],-v[1])
    p=next(p for p in stones if evaluate(line,p)==0)
    return p,v


def line_count(parameters,n):
    p,v=parameters
    lo,hi=None,None
    for q,a in zip(p,v):
        if a==0:
            if abs(q)>n: return 0
            continue
        if a>0: lower,upper=ceildiv(-n-q,a),(n-q)//a
        else: lower,upper=ceildiv(q-n,-a),(q+n)//(-a)
        lo=lower if lo is None else max(lo,lower)
        hi=upper if hi is None else min(hi,upper)
    return max(0,hi-lo+1)


def intersections(lines):
    out=defaultdict(set)
    for i,j in combinations(range(len(lines)),2):
        _,a,b,c=lines[i]; _,d,e,f=lines[j]
        den=a*e-b*d
        if den==0: continue
        xn,yn=b*f-c*e,c*d-a*f
        if xn%den==0 and yn%den==0:
            out[(xn//den,yn//den)].update((i,j))
    return out


def main():
    root=Path(__file__).resolve().parents[3]
    masks=struct.unpack('<16Q',(root/'night-research/maxsafe_n7_K14.bin').read_bytes())
    examples=[('horizontal',[(0,0),(1,0),(2,0)]),
              ('slope_half',[(0,0),(2,1),(4,2)]),
              ('triangle',[(0,0),(2,0),(0,2)]),
              ('parabola',[(t,t*t) for t in range(1,7)])]
    for i in (0,1):
        examples.append((f'n7_maximum_{i}',[(j%7,j//7) for j in range(49) if masks[i]>>j&1]))
    result={'B388':'SUPPORTED','universal_proof_not_finite_extrapolation':True,'examples':[]}
    for name,stones in examples:
        assert all(determinant(q)!=0 for q in combinations(stones,4))
        certificate=escape_without_circles(stones)
        box=bbox(stones)
        cc={curve(t) for t in combinations(stones,3)}
        assert len(cc)==comb(len(stones),3)
        lines=certificate['lines']
        assert set(lines)=={c for c in cc if c[0]==0}
        circles=[c for c in cc if c[0]!=0]
        point_union=set().union(*(circle_points(c) for c in circles)) if circles else set()
        assert all(distance(p,box)<certificate['circle_cutoff'] for p in point_union)
        assert all(evaluate(c,certificate['escape_point']) for c in cc)
        params=[line_parameters(line,stones) for line in lines]
        height=[max(abs(x),abs(y)) for p,(x,y) in params]
        period=lcm(*height) if height else 1
        slope=sum((Fraction(2,h) for h in height),Fraction(0))
        inter=intersections(lines)
        circle_only={p for p in point_union if all(evaluate(line,p) for line in lines)}
        occupied={p for p in stones if any(evaluate(c,p)==0 for c in cc)}
        def inside(p,n): return max(map(abs,p))<=n
        def count(n):
            return (sum(line_count(p,n) for p in params)
                    -sum(len(v)-1 for p,v in inter.items() if inside(p,n))
                    +sum(inside(p,n) for p in circle_only)-sum(inside(p,n) for p in occupied))
        grids=(0,1,2,4,8,12) if len(stones)<10 else (7,9)
        for n in grids:
            direct=sum((x,y) not in stones and any(evaluate(c,(x,y))==0 for c in cc)
                       for x in range(-n,n+1) for y in range(-n,n+1))
            assert direct==count(n)
        anchor_bound=max(max(map(abs,p)) for p in stones)
        start=anchor_bound+certificate['circle_cutoff']
        start=max([start,*[max(map(abs,p)) for p in inter]])
        for p,v in params:
            h,j=sorted(map(abs,v),reverse=True)
            a=max(map(abs,p))
            start=max(start,a if h==j else ceildiv(a*(h+j),h-j))
        drift=slope*period
        assert drift.denominator==1
        for n in range(start,start+2*period+1):
            assert count(n+period)-count(n)==drift
        first_safe=None
        for radius in range(1,10):
            x0,x1,y0,y1=box
            frame=[(x,y) for x in range(x0-radius,x1+radius+1)
                         for y in range(y0-radius,y1+radius+1)
                         if distance((x,y),box)==radius]
            legal=[p for p in frame if all(evaluate(c,p) for c in cc)]
            if legal:
                first_safe={'radius':radius,'count':len(legal),'first_points':legal[:12]}
                break
        width,height_box=box[1]-box[0],box[3]-box[2]
        frame_bound=max(1,(4*len(circles)+len(lines)-width-height_box)//4+1)
        assert first_safe and first_safe['radius']<=frame_bound
        row={'name':name,'stones':stones,'box':box,**certificate,
             'circle_count':len(circles),'finite_circle_lattice_points':len(point_union),
             'line_direction_heights':height,'far_field_slope':str(slope),
             'eventual_period':period,'verified_recurrence_start':start,
             'recurrence_increment':int(drift),'frame_bound':frame_bound,
             'first_safe_shell':first_safe,'sample_counts':{str(n):count(n) for n in grids}}
        result['examples'].append(row)
        print(name,'lines',len(lines),'slope',slope,'period',period,'r',first_safe['radius'],flush=True)
    target=root/'research/verification/round9_external_rays.json'
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(target,flush=True)


if __name__=='__main__':
    main()
