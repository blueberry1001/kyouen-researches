"""B065 exact witness: fresh geometry, all subsets, three independent mex routes."""
from functools import cache
from itertools import combinations
from pathlib import Path
import hashlib
import json
from round25_forced_verify import geometry,bits,det4

ROOT=Path(__file__).resolve().parents[1]


def main():
    d=json.loads((ROOT/'round41_n8_bounded.json').read_bytes())
    n=d['n'];s=d['S_mask'];points,quads,curves=geometry(n)
    assert n==8 and all(s&q!=q for q in quads)
    full=(1<<(n*n))-1;L=full^s
    for c in curves:
        if (s&c).bit_count()==3:L&=~c
    ids=list(bits(L));assert ids==d['L_ids'] and len(ids)==7
    for p in bits(full^s):
        direct=all(det4([points[q] for q in (*triple,p)])!=0 for triple in combinations(list(bits(s)),3))
        assert direct==bool(L>>p&1)
    raw={q&~s for q in quads if not(q&~s)&~L}
    edges=sorted(e for e in raw if not any(f!=e and f&e==f for f in raw))
    assert edges and min(e.bit_count() for e in edges)>=3
    compressed=sorted(sum(1<<i for i,p in enumerate(ids) if e>>p&1) for e in edges)
    N=1<<len(ids);safe=[False]*N;values=[None]*N;records=[]
    for m in range(N):
        t=sum(1<<p for i,p in enumerate(ids) if m>>i&1);occupied=s|t
        residual_safe=not any(t&e==e for e in edges)
        quad_safe=all(occupied&q!=q for q in quads)
        curve_safe=all((occupied&c).bit_count()<=3 for c in curves)
        determinant_safe=all(det4([points[q] for q in four])!=0 for four in combinations(list(bits(occupied)),4))
        assert residual_safe==quad_safe==curve_safe==determinant_safe
        safe[m]=quad_safe
    for m in range(N-1,-1,-1):
        if not safe[m]:continue
        seen={values[m|1<<p] for p in range(len(ids)) if not m>>p&1 and safe[m|1<<p]}
        v=0
        while v in seen:v+=1
        values[m]=v
    @cache
    def curve_mex(t):
        occupied=s|t;legal=L&~t
        for c in curves:
            if (occupied&c).bit_count()==3:legal&=~c
        seen={curve_mex(t|1<<p) for p in bits(legal)}
        v=0
        while v in seen:v+=1
        return v
    @cache
    def edge_mex(m):
        seen=set()
        for p in reversed(range(len(ids))):
            child=m|1<<p
            if m>>p&1 or any(child&e==e for e in compressed):continue
            seen.add(edge_mex(child))
        v=0
        while v in seen:v+=1
        return v
    for m in range(N):
        t=sum(1<<p for i,p in enumerate(ids) if m>>i&1)
        if safe[m]:assert values[m]==curve_mex(t)==edge_mex(m)
        records.append({'compressed_extension':m,'extension_ids':list(bits(t)),
                        'safe':safe[m],'g':values[m]})
    assert values[0]==d['g']==5 and d['pair_edges']==0
    child_values=[values[1<<i] for i in range(len(ids))]
    assert set(child_values)==set(range(5))
    old=json.loads((ROOT/'round39_empty_pair_audited.json').read_bytes())
    assert old['finite_exclusion']=='No B065 witness for n<=7; if it exists, n>=8'
    assert all(r['max_computed_g']<=3 for r in old['large_board_censuses'])
    files=['scripts/round41_audit.py','scripts/round41_empty_pair_bounded.cpp',
           'scripts/round25_forced_verify.py','scripts/kc_core.h','round41_n8_bounded.json',
           'round39_empty_pair_audited.json','round39-b065-seven-board-exclusion.md']
    out={'original_verdict':'SUPPORTED','minimum_board_n':8,'n':n,'S_mask':s,
         'S_ids':list(bits(s)),'S_coordinates':[points[p] for p in bits(s)],
         'L_ids':ids,'L_coordinates':[points[p] for p in ids],
         'minimal_residual_edges_ids':[list(bits(e)) for e in edges],
         'minimal_residual_edges_compressed':compressed,'pair_edge_count':0,'g':values[0],
         'child_g':dict(zip(map(str,ids),child_values)),
         'winning_moves':[p for p,g in zip(ids,child_values) if g==0],
         'all_128_extensions':records,'safe_extension_count':sum(safe),
         'search_complete':False,'search_note':'Stopped at first exact witness; 47711132 safe sets visited, not a census.',
         'sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}}
    (ROOT/'round41_b065_verified.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS B065 g5 pair-empty; minimum board8; S',out['S_ids'],'L',ids)
    print('R',out['minimal_residual_edges_ids'],'children',out['child_g'],'safe',sum(safe))


if __name__=='__main__':main()
