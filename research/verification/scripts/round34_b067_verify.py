"""Certify the old B067 candidate using unrestricted extensions and exact height."""
from functools import cache
from itertools import combinations
from pathlib import Path
import hashlib
import json
from round25_forced_verify import geometry, bits, det4
from round23_b251_audit import det4 as original_det4

ROOT=Path(__file__).resolve().parents[1]


def main():
    n=4;points,quads,curves=geometry(n)
    # Independent original-coordinate determinant convention as well.
    rows=[(x*x+y*y,x,y,1) for x,y in points]
    other=[sum(1<<p for p in ids) for ids in combinations(range(16),4)
           if original_det4([rows[p] for p in ids])==0]
    assert other==quads
    ids=[0,6,7,9];s=sum(1<<p for p in ids)
    assert all(s&q!=q for q in quads)
    L=(1<<16)-1^s
    for c in curves:
        if (s&c).bit_count()==3:L&=~c
    assert list(bits(L))==[1,2,5,8,11,12,14,15]
    raw={q&~s for q in quads if not(q&~s)&~L}
    edges=sorted(e for e in raw if not any(f!=e and f&e==f for f in raw))
    pairs=[e for e in edges if e.bit_count()==2]
    cycle=[11,12,1,8,2,15,14]
    expected={sum(1<<p for p in pair) for pair in zip(cycle,cycle[1:]+cycle[:1])}
    induced={e for e in pairs if not e&~sum(1<<p for p in cycle)}
    assert induced==expected and len(expected)==7
    extensions=[]
    for r in range(9):
        for choice in combinations(bits(L),r):
            t=sum(1<<p for p in choice)
            safe=not any((s|t)&q==q for q in quads)
            assert safe==all(((s|t)&c).bit_count()<=3 for c in curves)
            assert safe==not_any_edge(t,edges)
            direct=all(det4([points[p] for p in four])!=0 for four in combinations(bits(s|t),4))
            assert safe==direct
            extensions.append({'ids':list(choice),'mask':t,'safe':safe})
    safe_masks={r['mask'] for r in extensions if r['safe']}
    h=max(t.bit_count() for t in safe_masks)
    assert h==3
    @cache
    def value(t):
        seen={value(t|(1<<p)) for p in bits(L&~t) if t|(1<<p) in safe_masks}
        g=0
        while g in seen:g+=1
        return g
    max_extensions=[list(bits(t)) for t in sorted(safe_masks) if t.bit_count()==h]
    files=['scripts/round34_b067_verify.py','scripts/round25_forced_verify.py','scripts/round23_b251_audit.py']
    out={'original_verdict':'REFUTED','n':n,'S_ids':ids,'S_coordinates':[points[p] for p in ids],
         'S_mask':s,'L_ids':list(bits(L)), 'height':h,'K_of_S':len(ids)+h,'g':value(0),
         'induced_cycle':cycle,'pair_edges':[list(bits(e)) for e in pairs],
         'minimal_residual_edges':[list(bits(e)) for e in edges],
         'max_extensions':max_extensions,'all_256_extensions':extensions,
         'safe_extension_count':len(safe_masks),
         'sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}}
    (ROOT/'round34_b067_verified.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS B067 REFUTED: induced C7, exact unrestricted height3, K(S)=7, all256 extensions')


def not_any_edge(t,edges):
    return not any(t&e==e for e in edges)


if __name__=='__main__':main()
