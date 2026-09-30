"""Exact original B501/B502/B506 witness audits, with corrected coordinate metadata."""
from fractions import Fraction
from functools import cache
from itertools import combinations
from pathlib import Path
import hashlib
import json
from round25_forced_verify import geometry,bits,det4

ROOT=Path(__file__).resolve().parents[1]


def main():
    cases=[(4,4137,Fraction(76,135),3),(5,11329,Fraction(2383,3360),3),
           (6,35652737,Fraction(5162,6615),4)]
    records=[]
    for n,s,expected,h in cases:
        points,quads,curves=geometry(n);full=(1<<(n*n))-1
        assert all(s&q!=q for q in quads)
        L=full^s
        for c in curves:
            if (s&c).bit_count()==3:L&=~c
        ids=list(bits(L))
        raw={q&~s for q in quads if not(q&~s)&~L}
        edges=[e for e in raw if not any(f!=e and f&e==f for f in raw)]
        safe_extensions=set()
        for m in range(1<<len(ids)):
            t=sum(1<<p for i,p in enumerate(ids) if m>>i&1)
            safe=not any(t&e==e for e in edges)
            assert safe==all(((s|t)&c).bit_count()<=3 for c in curves)
            if safe:
                assert all(det4([points[p] for p in four])!=0 for four in combinations(bits(s|t),4))
                safe_extensions.add(t)
        @cache
        def solve(t):
            children=[t|(1<<p) for p in reversed(ids) if not t>>p&1 and t|(1<<p) in safe_extensions]
            if not children:return 0,Fraction(0),0
            values=[solve(c) for c in children];seen={v[0] for v in values};g=0
            while g in seen:g+=1
            return g,sum((1-v[1] for v in values),Fraction(0))/len(children),1+max(v[2] for v in values)
        g,p,height=solve(0)
        assert g==0 and p==expected and height==h
        assert len(safe_extensions)==solve.cache_info().currsize
        assert height==max(t.bit_count() for t in safe_extensions)
        dag=[]
        for t in sorted(safe_extensions):
            children=[t|(1<<q) for q in ids if not t>>q&1 and t|(1<<q) in safe_extensions]
            val=solve(t)
            dag.append({'extension_mask':t,'g':val[0],'p_rand':str(val[1]),'height':val[2],
                        'children':children})
        records.append({'n':n,'S_mask':s,'S_ids':list(bits(s)),
                        'S_coordinates':[points[p] for p in bits(s)],'L_ids':ids,
                        'g':g,'p_rand':str(p),'height':height,
                        'all_legal_subset_count':1<<len(ids),'safe_extension_count':len(safe_extensions),
                        'child_p_rand':{q:str(solve(1<<q)[1]) for q in ids},
                        'child_g':{q:solve(1<<q)[0] for q in ids},'complete_safe_extension_dag':dag})
        print('PASS n',n,'P, height',height,'p_rand',p,'safe continuations',len(safe_extensions),flush=True)
    assert Fraction(records[1]['p_rand'])>Fraction(2,3)
    assert Fraction(records[2]['p_rand'])>Fraction(3,4)
    assert records[0]['height']<=3 and Fraction(records[0]['p_rand'])>Fraction(1,2)
    files=['scripts/round36_random_witness_audit.py','scripts/round25_forced_verify.py',
           'round3_b502_pgrand_n6.json','round3_b501_pgrand_n5b.json','round2_b501.json']
    out={'original_verdicts':{'B501':'REFUTED','B502':'SUPPORTED','B506':'REFUTED'},
         'population':'three explicit standard-board witnesses; no full-board extremal census claimed',
         'witnesses':records,'sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}}
    (ROOT/'round36_random_witnesses_verified.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
