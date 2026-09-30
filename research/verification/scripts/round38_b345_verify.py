"""B345 exact geometric counterexample with one pair and one minimal triple."""
from functools import cache
from itertools import combinations
from pathlib import Path
import hashlib
import json
from round25_forced_verify import geometry,bits,det4

ROOT=Path(__file__).resolve().parents[1]


def main():
    found=json.loads((ROOT/'round38_b345_n5_search.json').read_bytes())
    points,quads,curves=geometry(5);s=found['S_mask'];assert all(s&q!=q for q in quads)
    L=(1<<25)-1^s
    for c in curves:
        if (s&c).bit_count()==3:L&=~c
    ids=list(bits(L));assert ids==[10,19,22,23]
    raw={q&~s for q in quads if not(q&~s)&~L}
    edges=sorted(e for e in raw if not any(f!=e and f&e==f for f in raw))
    pair=(1<<19)|(1<<23);triple=(1<<10)|(1<<19)|(1<<22)
    assert set(edges)=={pair,triple}
    subsets=[]
    for m in range(16):
        t=sum(1<<p for i,p in enumerate(ids) if m>>i&1)
        safe=not any(t&e==e for e in edges)
        assert safe==all((s|t)&q!=q for q in quads)
        assert safe==all(((s|t)&c).bit_count()<=3 for c in curves)
        assert safe==all(det4([points[p] for p in four])!=0 for four in combinations(bits(s|t),4))
        subsets.append({'extension_mask':t,'original_safe':safe,'without_triple_safe':t&pair!=pair})
    def game(family):
        @cache
        def value(t):
            children=[t|(1<<p) for p in reversed(ids) if not t>>p&1
                      and not any((t|(1<<p))&e==e for e in family)]
            seen={value(c) for c in children};g=0
            while g in seen:g+=1
            return g
        g=value(0)
        safe=[r['extension_mask'] for r in subsets if not any(r['extension_mask']&e==e for e in family)]
        assert len(safe)==value.cache_info().currsize
        return {'g':g,'child_g':{p:value(1<<p) for p in ids},
                'all_safe_mex_values':[{'extension_mask':t,'g':value(t)} for t in safe]}
    original=game(edges);without=game([pair]);assert original['g']==found['g_full']==3
    assert without['g']==found['g_minus']==1
    # Each clique, including a singleton, contributes nimber1. Three cliques
    # therefore xor to1; the triple connects three different clique components.
    components=[[19,23],[10],[22]]
    assert all(len(set(bits(triple))&set(c))==1 for c in components)
    files=['scripts/round38_b345_verify.py','scripts/round38_b345_search.cpp',
           'scripts/round25_forced_verify.py','scripts/kc_core.h','round38_b345_n5_search.json']
    out={'original_verdict':'REFUTED','n':5,'S_mask':s,'S_ids':list(bits(s)),
         'S_coordinates':[points[p] for p in bits(s)],'L_ids':ids,
         'clique_components':components,'minimal_residual_pair':[19,23],
         'sole_minimal_triple':[10,19,22],'four_edges':0,'all_16_extensions':subsets,
         'original_game':original,'without_triple_game':without,
         'sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}}
    (ROOT/'round38_b345_verified.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS B345 REFUTED: K2+K1+K1, sole triple crosses all3, exact g1->3 when added')
    print('S',out['S_ids'],'children',original['child_g'],without['child_g'])


if __name__=='__main__':main()
