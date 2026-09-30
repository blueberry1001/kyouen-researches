"""Certify B068 with exact polynomial determinants, not degree-only proxies."""
from functools import cache
from itertools import combinations
from pathlib import Path
import hashlib
import json
from round25_forced_verify import geometry, bits, det4

ROOT=Path(__file__).resolve().parents[1]


def characteristic(A):
    # Polynomial determinant of xI-A by Laplace expansion, memoized by columns.
    # This differs from the searcher's matrix-power/Newton computation.
    n=len(A)
    @cache
    def determinant(columns):
        if not columns:return (1,)
        row=n-len(columns);answer=[0]*(len(columns)+1)
        for j,col in enumerate(columns):
            rest=determinant(columns[:j]+columns[j+1:])
            sign=(-1)**j
            for k,c in enumerate(rest):
                answer[k]-=sign*A[row][col]*c
                if row==col:answer[k+1]+=sign*c
        return tuple(answer)
    return list(reversed(determinant(tuple(range(n)))))


def main():
    found=json.loads((ROOT/'round34_b068_n6_search.json').read_bytes())
    n=6;points,quads,curves=geometry(n);full=(1<<36)-1
    records=[]
    for r in found['pair']:
        s=r['S_mask'];assert all(s&q!=q for q in quads)
        L=full^s
        for c in curves:
            if (s&c).bit_count()==3:L&=~c
        assert L==r['L_mask'];ids=list(bits(L));assert len(ids)==8
        raw={q&~s for q in quads if not(q&~s)&~L}
        edges=sorted(e for e in raw if not any(f!=e and f&e==f for f in raw))
        assert all(e.bit_count()==2 for e in edges)
        A=[[0]*8 for _ in range(8)];index={p:i for i,p in enumerate(ids)}
        for e in edges:
            a,b=bits(e);A[index[a]][index[b]]=A[index[b]][index[a]]=1
        graph=0;b=0
        for i in range(8):
            for j in range(i+1,8):
                graph|=A[i][j]<<b;b+=1
        assert graph==r['graph_compressed']
        degree=sorted(map(sum,A));polynomial=characteristic(A)
        subsets=[];safe_masks=set()
        for m in range(256):
            t=sum(1<<p for i,p in enumerate(ids) if m>>i&1)
            graph_safe=not any(t&e==e for e in edges)
            assert graph_safe==all((s|t)&q!=q for q in quads)
            assert graph_safe==all(((s|t)&c).bit_count()<=3 for c in curves)
            direct=all(det4([points[p] for p in four])!=0 for four in combinations(bits(s|t),4))
            assert graph_safe==direct
            subsets.append({'extension_mask':t,'safe':graph_safe})
            if graph_safe:safe_masks.add(t)
        @cache
        def value(t):
            children=[t|(1<<p) for p in reversed(ids) if not t>>p&1 and t|(1<<p) in safe_masks]
            seen={value(c) for c in children};g=0
            while g in seen:g+=1
            return g
        assert value(0)==r['g']
        values=[{'extension_mask':t,'g':value(t)} for t in sorted(safe_masks)]
        records.append({'S_mask':s,'S_ids':list(bits(s)), 'S_coordinates':[points[p] for p in bits(s)],
                        'L_ids':ids,'pair_edges':[list(bits(e)) for e in edges],
                        'adjacency_matrix':A,'degree_sequence':degree,'characteristic_polynomial':polynomial,
                        'g':value(0),'all_256_extensions':subsets,'all_safe_mex_values':values,
                        'first_child_g':{p:value(1<<p) for p in ids}})
    a,b=records
    assert a['degree_sequence']==b['degree_sequence']==[4,4,4,5,5,5,5,6]
    assert a['characteristic_polynomial']==b['characteristic_polynomial']==[1,0,-19,-28,28,42,-16,-8,0]
    assert bool(a['g'])!=bool(b['g'])
    # Spectra count multiplicity, so exact equal characteristic polynomials
    # of real symmetric adjacency matrices establish exact cospectrality.
    files=['scripts/round34_b068_verify.py','scripts/round34_b068_search.cpp',
           'scripts/round25_forced_verify.py','scripts/kc_core.h','round34_b068_n6_search.json']
    out={'original_verdict':'SUPPORTED','n':n,'pair':records,
         'sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}}
    (ROOT/'round34_b068_verified.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS B068: exact polynomial equality, all minimal residuals pairs, both256 extensions, g3 vs0')
    print('S IDs',a['S_ids'],b['S_ids'])


if __name__=='__main__':main()
