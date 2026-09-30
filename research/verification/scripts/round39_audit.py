"""Audit complete finite B065 exclusion through n7 and its exact g3 witness."""
from functools import cache
from pathlib import Path
import hashlib
import json
from round25_forced_verify import geometry,bits

ROOT=Path(__file__).resolve().parents[1]


def game(curves,vertices):
    at=[[c for c in curves if c>>p&1] for p in range(vertices)]
    @cache
    def value(s,legal):
        seen=set()
        for p in bits(legal):
            child=s|(1<<p);next_legal=legal&~(1<<p)
            for c in at[p]:
                if (child&c).bit_count()==3:next_legal&=~c
            seen.add(value(child,next_legal))
        g=0
        while g in seen:g+=1
        return g
    return value


def main():
    results=[]
    for n,expected in [(4,5811),(5,151394),(6,5081289),(7,179810350)]:
        a=json.loads((ROOT/f'round39_empty_pair_n{n}_search.json').read_bytes())
        b=json.loads((ROOT/f'round39_empty_pair_n{n}_curves.json').read_bytes())
        for key in ['n','all_safe_sets_considered','S_size_min','L_size_min','empty_pair_candidates',
                    'max_computed_g','legal_size_histogram','g_histogram']:
            assert a[key]==b[key],(n,key)
        assert a['all_safe_sets_considered']==expected
        assert a['uncomputed_over_cap']==0 and a['witness'] is None
        assert sum(a['g_histogram'].values())==a['empty_pair_candidates']
        assert sum(a['legal_size_histogram'].values())==a['empty_pair_candidates']
        assert a['max_computed_g']<=3
        results.append(b)
    small=[]
    for n in (1,2,3,5):
        points,quads,curves=geometry(n);full=(1<<(n*n))-1;solve=game(curves,n*n)
        root=solve(0,full)
        singles=[solve(1<<p,full^(1<<p)) for p in range(n*n)]
        assert max(singles,default=0)<=3 and root<=3
        assert solve.cache_info().currsize=={1:2,2:15,3:298,5:151394}[n]
        small.append({'n':n,'empty_g':root,'single_stone_g':singles,
                      'all_standard_safe_states_checked':solve.cache_info().currsize})
        print('whole-curve low-stone audit n',n,'root',root,'single max',max(singles),flush=True)
    for n in (4,7):
        d=json.loads((ROOT/f'round28_n{n}_layers.json').read_bytes())
        low=[r for layer in d['levels'] if layer['k']<=1 for r in layer['values']]
        assert len(low)==n*n+1 and max(r[1] for r in low)<=3
    d=json.loads((ROOT/'round25_forced_n6.json').read_bytes())
    assert len(d['first_moves'])==36 and all(r['g']==0 for r in d['first_moves'])
    top=results[-1];s=top['maximum_witness_S_mask'];L=top['maximum_witness_L_mask']
    points,quads,curves=geometry(7);full=(1<<49)-1;legal=full^s
    for c in curves:
        if (s&c).bit_count()==3:legal&=~c
    assert legal==L
    raw={q&~s for q in quads if not(q&~s)&~L}
    edges=sorted(e for e in raw if not any(f!=e and f&e==f for f in raw))
    assert all(e.bit_count()>=3 for e in edges)
    solve=game(curves,49);assert solve(s,L)==3
    ids=list(bits(L));extensions=[]
    for m in range(1<<len(ids)):
        t=sum(1<<p for i,p in enumerate(ids) if m>>i&1)
        safe=not any(t&e==e for e in edges)
        assert safe==all(((s|t)&c).bit_count()<=3 for c in curves)
        if not safe:continue
        child_legal=L&~t
        for c in curves:
            if ((s|t)&c).bit_count()==3:child_legal&=~c
        extensions.append({'extension_mask':t,'g':solve(s|t,child_legal)})
    files=['scripts/round39_audit.py','scripts/round39_geometry_inputs.py',
           'scripts/round39_empty_pair_search.cpp','scripts/round39_curve_census.cpp',
           'scripts/round25_forced_verify.py','scripts/kc_core.h',
           'round28_n4_layers.json','round28_n7_layers.json','round25_forced_n6.json']
    for n in (4,5,6,7):
        files += [f'round39_empty_pair_n{n}_search.json',f'round39_empty_pair_n{n}_curves.json',f'round39_n{n}_input.txt']
    out={'original_verdict':'PARTIAL','finite_exclusion':'No B065 witness for n<=7; if it exists, n>=8',
         'large_board_censuses':results,'low_stone_small_board_checks':small,
         'g3_pair_empty_witness':{'n':7,'S_ids':list(bits(s)),'S_mask':s,'L_ids':ids,
                                'minimal_residual_edges':[list(bits(e)) for e in edges],
                                'g':3,'all_safe_extension_mex':extensions},
         'sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}}
    (ROOT/'round39_empty_pair_audited.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS B065 finite exclusion through n7; independent counts/histograms agree; original remains PARTIAL')


if __name__=='__main__':main()
