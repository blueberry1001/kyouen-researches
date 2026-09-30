"""Audit original n=7 conclusions only after both exact solvers agree."""
from collections import Counter
from pathlib import Path
import argparse
import hashlib
import json
from round25_forced_verify import geometry
from round27_response_graphs import components, perfect_matchings, game

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--prepare',action='store_true',help='generate independent n4/n7 quad inputs only')
    args=parser.parse_args()
    if args.prepare:
        for n in (4,7):
            _,quads,_=geometry(n)
            (ROOT/f'round28_n{n}_quads.txt').write_text(
                f'{n*n} {len(quads)}\n'+' '.join(map(str,quads))+'\n',encoding='utf-8')
        print('Independent determinant inputs prepared')
        return
    small_primary=json.loads((ROOT/'round28_n4_layers.json').read_text())
    small_independent=json.loads((ROOT/'round28_n4_independent.json').read_text())
    sa={L['k']:L for L in small_primary['levels']}
    sb={L['k']:L for L in small_independent['levels']}
    _,_,small_values,*_=game(4)
    for k,L in sa.items():
        histogram={str(g):count for g,count in Counter(v[0] for s,v in small_values.items() if s.bit_count()==k).items()}
        assert L['histogram']==sb[k]['histogram']==histogram
        if k<=3:
            assert L['values']==sb[k]['values']
            for s,g,t,w in L['values']:
                expected=small_values[s]
                assert g==expected[0]
                assert set(i for i in range(64) if t>>i&1)==set(expected[1])
                assert set(i for i in range(64) if w>>i&1)==set(expected[2])
    primary=json.loads((ROOT/'round28_n7_layers.json').read_text())
    independent=json.loads((ROOT/'round28_n7_independent.json').read_text())
    enum=json.loads((ROOT/'round28_n7_enum.json').read_text())
    old=json.loads((ROOT/'data/n7_stream.json').read_text())
    a={L['k']:L for L in primary['levels']}
    b={L['k']:L for L in independent['levels']}
    assert primary['total_states']==independent['states']==enum['n_safe_subsets']==179810350
    assert primary['total_edges']==independent['edges']==old['edge_total']==1499354401
    for k,L in a.items():
        assert L['states']==b[k]['states']==enum['level_sizes'][k]==old['level_sizes'][k]
        assert L['histogram']==b[k]['histogram']
        assert L['histogram'].get('0',0)==old['levels'][k]['n_P']
        if k<=3:assert L['values']==b[k]['values']
    _,quads,_=geometry(7)
    text=(ROOT/'round28_n7_quads.txt').read_text().split()
    assert list(map(int,text[:2]))==[49,6364]
    assert list(map(int,text[2:]))==quads
    K=14
    maxg=[b[k]['max_g'] for k in sorted(b)]
    sigma=next(k for k,g in enumerate(maxg) if g==K-k)
    assert sigma==4 and maxg[:5]==[0,1,5,7,10]
    root=a[0]['values'][0]
    assert root==[0,0,(1<<8)|(1<<10)|(1<<12)|(1<<14),0]
    edges=[tuple(i for i in range(49) if s>>i&1) for s,g,t,w in a[2]['values'] if g==0]
    adj={i:set() for i in range(49)}
    for p,q in edges:adj[p].add(q);adj[q].add(p)
    assert len(edges)==552 and len(components(adj))==1
    corners=[0,6,42,48]
    assert all(adj[p]=={24} for p in corners)
    cutpoints=[p for p in adj if len(components({q:v-{p} for q,v in adj.items() if q!=p}))>1]
    bridges=[]
    for p,q in edges:
        reduced={z:set(v) for z,v in adj.items()}
        reduced[p].remove(q);reduced[q].remove(p)
        if len(components(reduced))>1:bridges.append([p,q])
    assert cutpoints==[24] and {tuple(sorted(e)) for e in bridges}=={tuple(sorted((p,24))) for p in corners}
    reduced={q:v-{24} for q,v in adj.items() if q!=24}
    assert sorted(map(len,components(reduced)))==[1,1,1,1,44]
    matching=next(perfect_matchings(adj,set(adj)-{6,42,48}))
    covered=[p for edge in matching for p in edge]
    assert len(matching)==23 and len(set(covered))==46 and all(q in adj[p] for p,q in matching)
    # Four leaves share one neighbor: at least three must be unmatched.
    # Thus 23 pairs is maximum, and the required 24 pairs cannot exist.
    result={
        'checked_states':primary['total_states'],'checked_edges':primary['total_edges'],
        'n4_independent_whole_curve_check':True,
        'max_grundy_by_layer':maxg,'sigma7':sigma,'sigma_witness':b[4]['max_witness'],
        'root':{'g':root[1],'Tstar':[8,10,12,14],'WFT':[]},
        'J7':{'edges':edges,'degree_histogram':dict(Counter(map(len,adj.values()))),
              'components':components(adj),'corner_neighbors':{p:sorted(adj[p]) for p in corners},
              'bridges':bridges,'cutpoints':cutpoints,'components_without_center':components(reduced),
              'maximum_matching':matching,'maximum_matching_size':23,'unmatched':[6,42,48]},
        'original_verdicts':{'B022':'SUPPORTED','B040':'REFUTED','B313':'REFUTED',
                             'B314':'REFUTED','B315':'SUPPORTED'},
        'still_partial':['B006','B016','B021','B319','B321','B322','B331','B335'],
    }
    files=['scripts/round28_low_layers.cpp','scripts/round28_recursive_verify.cpp',
           'scripts/round28_run.sh','scripts/round28_audit.py','scripts/round25_forced_verify.py',
           'scripts/round27_response_graphs.py','scripts/round5_prand_stream.cpp','scripts/kc_core.h',
           'round28_n7_quads.txt','round28_n7_layers.json','round28_n7_independent.json',
           'round28_n7_enum.json','round28_n4_layers.json','round28_n4_independent.json']
    result['sha256']={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files}
    (ROOT/'round28_n7_audited.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Exact original-scope audit passed: B022/B315 supported; B040/B313/B314 refuted',flush=True)

if __name__=='__main__':main()
