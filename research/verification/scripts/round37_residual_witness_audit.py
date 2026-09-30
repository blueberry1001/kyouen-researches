"""Original single residual-edge and pair-synergy witnesses, audited independently."""
from functools import cache
from pathlib import Path
import hashlib
import json
from round25_forced_verify import geometry,bits

ROOT=Path(__file__).resolve().parents[1]


def case(n,S,deleted_sets):
    points,quads,curves=geometry(n);s=sum(1<<p for p in S);full=(1<<(n*n))-1
    L=full^s
    for c in curves:
        if (s&c).bit_count()==3:L&=~c
    raw={q&~s for q in quads if not(q&~s)&~L}
    edges=sorted(e for e in raw if not any(f!=e and f&e==f for f in raw))
    ids=list(bits(L));index={p:i for i,p in enumerate(ids)};N=1<<len(ids)
    def compressed(e):return sum(1<<index[p] for p in bits(e))
    variants=[]
    for deletion in deleted_sets:
        deleted={sum(1<<p for p in e) for e in deletion};assert deleted<=set(edges)
        kept=[e for e in edges if e not in deleted]
        unsafe=bytearray(N)
        for e in kept:
            c=compressed(e);rest=N-1^c;t=rest
            while True:
                unsafe[c|t]=1
                if not t:break
                t=(t-1)&rest
        values={}
        for m in range(N-1,-1,-1):
            if unsafe[m]:continue
            seen={values[m|(1<<i)] for i in range(len(ids)) if not m>>i&1 and m|(1<<i) in values}
            g=0
            while g in seen:g+=1
            values[m]=g
        @cache
        def direct(t):
            seen=set()
            for p in reversed(ids):
                if t>>p&1:continue
                c=t|(1<<p)
                if not any(c&e==e for e in kept):seen.add(direct(c))
            g=0
            while g in seen:g+=1
            assert g==values[compressed(t)]
            return g
        assert direct(0)==values[0]
        assert direct.cache_info().currsize==len(values)
        variants.append({'deleted_edges':deletion,'g0':values[0], 'safe_extensions':len(values),
                         'all_safe_mex_independently_agree':True,
                         'child_g':{p:direct(1<<p) for p in ids}})
    # The baseline residual family is exactly the geometric continuation game.
    for m in range(N):
        t=sum(1<<p for i,p in enumerate(ids) if m>>i&1)
        assert (not any(t&e==e for e in edges))==all(((s|t)&c).bit_count()<=3 for c in curves)
    return {'n':n,'S_ids':S,'S_coordinates':[points[p] for p in S],'L_ids':ids,
            'minimal_residual_edges':[list(bits(e)) for e in edges], 'variants':variants}


def main():
    forest=case(4,[0,2],[[],[[1,10,12]]])
    assert [r['g0'] for r in forest['variants']]==[5,0]
    pair_edges=[e for e in forest['minimal_residual_edges'] if len(e)==2]
    assert len(pair_edges)==5 and len({p for e in pair_edges for p in e})==10
    # All five pair edges are disjoint: a matching, hence a forest.
    synergy=case(3,[0,1,4],[[],[[2,6,8]],[[2,7,8]],[[2,6,8],[2,7,8]]])
    assert [r['g0'] for r in synergy['variants']]==[0,0,0,3]
    assert any(len(e)==2 for e in synergy['minimal_residual_edges'])
    files=['scripts/round37_residual_witness_audit.py','scripts/round25_forced_verify.py']
    out={'original_verdicts':{'B342':'REFUTED','B346':'SUPPORTED'},'forest':forest,'synergy':synergy,
         'sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}}
    (ROOT/'round37_residual_witnesses_verified.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS existing original witnesses: B342 forest single deletion |diff|5; B346 only simultaneous deletion flips')


if __name__=='__main__':main()
