"""Original B047 counterexample: exact residual C5, with all continuations checked."""
from collections import Counter
from functools import cache
from itertools import combinations
from pathlib import Path
import hashlib
import json
from round25_forced_verify import geometry,bits,det4

ROOT=Path(__file__).resolve().parents[1]

def main():
    n=5;points,quads,curves=geometry(n);full=(1<<25)-1
    ids=[0,1,6,13,15,23];s=sum(1<<p for p in ids)
    def safe_quads(mask):return not any(mask&q==q for q in quads)
    def safe_curves(mask):return all((mask&c).bit_count()<=3 for c in curves)
    assert safe_quads(s) and safe_curves(s)
    legal=sum(1<<p for p in bits(full^s) if safe_quads(s|(1<<p)))
    curve_legal=full^s
    for c in curves:
        if (c&s).bit_count()==3:curve_legal&=~c
    assert legal==curve_legal and list(bits(legal))==[2,14,17,20,24]
    raw={q&~s for q in quads if (q&~s)&~legal==0}
    minimal=sorted(a for a in raw if not any(b!=a and b&a==b for b in raw))
    cycle=[2,17,24,14,20]
    expected=sorted((1<<p)|(1<<q) for p,q in zip(cycle,cycle[1:]+cycle[:1]))
    assert minimal==expected and all(a.bit_count()==2 for a in minimal)
    # Exhaust all 32 subsets of the five initially legal vertices. This checks
    # that no higher-order or future constraint survives beyond the C5 edges.
    subsets=[];safe_extensions=[]
    for r in range(6):
        for choice in combinations(bits(legal),r):
            t=sum(1<<p for p in choice)
            graph_safe=not any(t&e==e for e in minimal)
            assert safe_quads(s|t)==safe_curves(s|t)==graph_safe
            direct=all(det4([points[p] for p in four])!=0 for four in combinations(bits(s|t),4))
            assert direct==graph_safe
            subsets.append({'extension':list(choice),'safe':graph_safe})
            if graph_safe:safe_extensions.append(t)
    assert len(safe_extensions)==11
    @cache
    def solve(t):
        children=[t|(1<<p) for p in bits(legal&~t) if safe_curves(s|t|(1<<p))]
        seen={solve(c) for c in children}
        return next(g for g in range(6) if g not in seen)
    assert solve(0)==0 and all(solve(1<<p)==1 for p in bits(legal))
    # Explicit transitive automorphisms are the five cyclic rotations.
    rotations=[{cycle[i]:cycle[(i+shift)%5] for i in range(5)} for shift in range(5)]
    for perm in rotations:
        image=sorted(sum(1<<perm[p] for p in bits(e)) for e in minimal)
        assert image==minimal
    witnesses={str(e):next(q for q in quads if q&~s==e) for e in minimal}
    terminal=[t for t in safe_extensions if not any(safe_curves(s|t|(1<<p)) for p in bits(legal&~t))]
    assert len(terminal)==5 and all(t.bit_count()==2 for t in terminal)
    result={'original_verdict':'REFUTED','n':n,'S_mask':s,'S_ids':ids,
            'S_coordinates':[points[p] for p in ids],'legal_ids':list(bits(legal)),
            'legal_coordinates':[points[p] for p in bits(legal)],'cycle_order':cycle,
            'minimal_residual_edges':[list(bits(e)) for e in minimal],
            'edge_quad_witnesses':{e:list(bits(q)) for e,q in witnesses.items()},
            'raw_residual_size_histogram':dict(Counter(a.bit_count() for a in raw)),
            'transitive_rotations':rotations,'g':0,'first_child_g':{p:solve(1<<p) for p in bits(legal)},
            'all_extensions':subsets,'safe_extension_count':11,
            'terminal_extension_count':5,'terminal_total_stones':8,
            'pairing_impossibility':'All five vertices are legal at S. A fixed response involution must map each to a distinct currently legal vertex; it has no fixed points, so its domain must have even size. Legality cannot return after adding stones.'}
    files=['scripts/round31_b047_odd_cycle.py','scripts/round25_forced_verify.py']
    result['sha256']={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files}
    (ROOT/'round31_b047_odd_cycle.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('B047 REFUTED: exact residual C5; all 32 continuations and transitive rotations verified')

if __name__=='__main__':main()
