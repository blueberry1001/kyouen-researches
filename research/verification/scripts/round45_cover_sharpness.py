"""Exact certificates for the improved cover bound and sharp two-curve overlap."""
from fractions import Fraction
from itertools import combinations
from math import gcd,lcm
from pathlib import Path
import hashlib
import json
from round25_forced_verify import det4,curve

ROOT=Path(__file__).resolve().parents[1]


def line(a,b):
    x,y=a;xx,yy=b;coeff=[yy-y,x-xx,(xx-x)*y-(yy-y)*x]
    factor=gcd(*coeff);coeff=[v//factor for v in coeff]
    if next(v for v in coeff if v)<0:coeff=[-v for v in coeff]
    return tuple(coeff)


def main():
    T=[(4,4),(4,7),(4,8),(7,4),(10,4),(1,10)]
    assert all(det4(four)!=0 for four in combinations(T,4))
    rational=[(Fraction(x,x*x+y*y),Fraction(y,x*x+y*y)) for x,y in T]
    scale=lcm(*(v.denominator for p in rational for v in p))
    S=[tuple(int(v*scale) for v in p) for p in rational];p=(0,0)
    assert all(det4(four)!=0 for four in combinations(S,4))
    triples=[list(ids) for ids in combinations(range(6),3) if det4([S[i] for i in ids]+[p])==0]
    assert len(triples)==4
    assert all(len(set(a)&set(b))<=1 for a,b in combinations(triples,2))
    lines={line(a,b) for a,b in combinations(T,2)}
    line_records=[]
    for a,b,c in sorted(lines):
        ids=[i for i,(x,y) in enumerate(T) if a*x+b*y+c==0]
        assert len(ids) in (2,3)
        line_records.append({'coefficients':[a,b,c],'T_ids':ids})
    t2=sum(len(r['T_ids'])==2 for r in line_records);t3=sum(len(r['T_ids'])==3 for r in line_records)
    assert t2==3 and t3==4 and t2+3*t3==15
    six={'T_coordinates':T,'inversion_scale':scale,'S_coordinates':S,'p':p,
         'n':max(max(q) for q in S)+1,'blocking_triples_S_indices':triples,
         'b':4,'delta':3,'pair_count_bound':5,'improved_bound':4,
         'all_T_lines':line_records}
    S2=[(0,5),(1,2),(1,6),(0,1),(3,0),(3,4)];Tids=[0,1,2];Uids=[3,4,5]
    p=(0,3);q=(4,3)
    assert all(det4(four)!=0 for four in combinations(S2,4))
    C=curve([S2[i] for i in Tids]);D=curve([S2[i] for i in Uids]);assert C!=D
    def on(coeff,point):
        a,b,c,d=coeff;x,y=point;return a*(x*x+y*y)+b*x+c*y+d==0
    common=[(x,y) for y in range(7) for x in range(7) if on(C,(x,y)) and on(D,(x,y))]
    assert common==[p,q] and p not in S2 and q not in S2
    for ids in [Tids,Uids]:
        assert all(det4([S2[i] for i in ids]+[r])==0 for r in [p,q])
    overlap={'n':7,'S_coordinates':S2,'T_indices':Tids,'U_indices':Uids,
             'curve_T_coefficients':C,'curve_U_coefficients':D,'exact_common_complement_points':common,
             'minimum_stone_count_for_two_empty_common_complements':6}
    files=['scripts/round45_cover_sharpness.py','scripts/round25_forced_verify.py']
    out={'B071_original_verdict':'SUPPORTED','B072_original_verdict':'SUPPORTED','B073_original_verdict':'REFUTED',
         'B075_original_verdict':'SUPPORTED','improved_general_bound':'For every safe S with k>=4 and empty p, b<=floor(k*(k-1)/6)-1.',
         'sharp_six_stone_witness':six,'sharp_overlap_witness':overlap,
         'primary_source':'https://terrytao.wordpress.com/2012/08/24/on-sets-defining-few-ordinary-lines/',
         'sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}}
    (ROOT/'round45_cover_verified.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS sharp k6 b4 delta3, n',six['n'],'; B075 sharp two empty complements with six stones')


if __name__=='__main__':main()
