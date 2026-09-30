"""All 255 labeled/9 unlabeled five-vertex minimal residual four-edge types."""
from collections import Counter
from functools import cache
from itertools import combinations,permutations
from pathlib import Path
import hashlib
import json
from round25_forced_verify import geometry,bits

ROOT=Path(__file__).resolve().parents[1]


def value(edges,m=5):
    edges=tuple(edges)
    @cache
    def g(s):
        seen={g(s|(1<<p)) for p in range(m) if not s>>p&1
              and not any((s|(1<<p))&e==e for e in edges)}
        x=0
        while x in seen:x+=1
        return x
    return g(0),g


def canonical(edges):
    return min(tuple(sorted(sum(1<<perm[p] for p in bits(e)) for e in edges))
               for perm in permutations(range(5)))


def subsets(items):
    for m in range(1<<len(items)):
        yield [x for i,x in enumerate(items) if m>>i&1]


def main():
    pairs=[sum(1<<p for p in c) for c in combinations(range(5),2)]
    triples=[sum(1<<p for p in c) for c in combinations(range(5),3)]
    quads=[31^(1<<p) for p in range(5)]
    classes={};labeled=0
    for Q in subsets(quads):
        if not Q:continue
        allowed_pairs=[e for e in pairs if all(e&q!=e for q in Q)]
        for P in subsets(allowed_pairs):
            if not P:continue
            allowed_triples=[e for e in triples if all(e&q!=e for q in Q)
                             and all(e&p!=p for p in P)]
            for T in subsets(allowed_triples):
                family=P+T+Q
                assert all(not (a!=b and a&b==a) for a in family for b in family)
                labeled+=1;key=canonical(family);full,fg=value(family);approx,ag=value(P+T)
                assert full!=approx
                if key not in classes:
                    type_id='q2' if len(Q)==2 else f'q1-d{len(P)}-t{len(T)}'
                    classes[key]={'type':type_id,'minimal_edges':list(key),
                                  'g_full':full,'g_up_to_three':approx,'labeled_count':0}
                record=classes[key];assert record['g_full']==full and record['g_up_to_three']==approx
                record['labeled_count']+=1
    assert labeled==255 and len(classes)==9
    assert len({r['type'] for r in classes.values()})==9
    types={r['type']:r for r in classes.values()}
    expected_counts={'q1-d1-t0':20,'q1-d1-t1':60,'q1-d1-t2':60,'q1-d1-t3':20,
                     'q1-d2-t0':30,'q1-d2-t1':30,'q1-d3-t0':20,'q1-d4-t0':5,'q2':10}
    assert {k:v['labeled_count'] for k,v in types.items()}==expected_counts
    realizations=[]
    for n in (4,5,6,7):
        path=ROOT/f'round40_n{n}_four_types.json'
        if not path.exists():continue
        d=json.loads(path.read_bytes());points,quads,curves=geometry(n)
        assert d['all_safe_sets_considered']=={4:5811,5:151394,6:5081289,7:179810350}[n]
        for r in d['types']:
            s=r['S_mask'];full=(1<<(n*n))-1;L=full^s
            assert all(s&q!=q for q in quads)
            for c in curves:
                if (s&c).bit_count()==3:L&=~c
            ids=list(bits(L));assert ids==r['L_ids'] and len(ids)==5
            raw={q&~s for q in quads if not(q&~s)&~L}
            minimal=[e for e in raw if not any(f!=e and f&e==f for f in raw)]
            compress=lambda e:sum(1<<i for i,p in enumerate(ids) if e>>p&1)
            edges=sorted(map(compress,minimal));assert edges==r['minimal_edges_compressed']
            key=canonical(edges);assert classes[key]['type']==r['type']
            low=[e for e in edges if e.bit_count()<4]
            original,fg=value(edges);approx,ag=value(low)
            assert original==r['g_full']==types[r['type']]['g_full']
            assert approx==r['g_up_to_three']==types[r['type']]['g_up_to_three']
            records=[]
            for m in range(32):
                t=sum(1<<p for i,p in enumerate(ids) if m>>i&1)
                safe=not any(m&e==e for e in edges)
                assert safe==all((s|t)&q!=q for q in quads)
                assert safe==all(((s|t)&c).bit_count()<=3 for c in curves)
                approximate=not any(m&e==e for e in low)
                records.append({'compressed_extension':m,'original_safe':safe,'up_to_three_safe':approximate,
                                'g_full':fg(m) if safe else None,'g_up_to_three':ag(m) if approximate else None})
            realizations.append({'n':n,'type':r['type'],'S_ids':list(bits(s)),
                                 'S_coordinates':[points[p] for p in bits(s)],'L_ids':ids,
                                 'minimal_edges_ids':[list(bits(e)) for e in minimal],
                                 'g_full':original,'g_up_to_three':approx,'all_32_extensions':records})
        assert sum(r['count'] for r in d['types'])==d['nontrivial_four_edge_candidates']
    assert {r['type'] for r in realizations}==set(types)
    tiny=[]
    for n,sids,lids,rank in [(2,[],[0,1,2,3],4),(5,[0,1,2,11,13,22,24],[9,15,23],3)]:
        points,quads,curves=geometry(n);s=sum(1<<p for p in sids)
        L=((1<<(n*n))-1)^s
        assert all(s&q!=q for q in quads)
        for c in curves:
            if (s&c).bit_count()==3:L&=~c
        assert list(bits(L))==lids
        raw={q&~s for q in quads if not(q&~s)&~L}
        assert raw=={L} and len(lids)==rank
        full,fg=value([(1<<rank)-1],rank);free,ag=value([],rank)
        records=[]
        for m in range(1<<rank):
            t=sum(1<<p for i,p in enumerate(lids) if m>>i&1)
            safe=m!=(1<<rank)-1
            assert safe==all((s|t)&q!=q for q in quads)
            assert safe==all(((s|t)&c).bit_count()<=3 for c in curves)
            records.append({'extension':m,'safe':safe,'g_full':fg(m) if safe else None,'g_free':ag(m)})
        tiny.append({'n':n,'S_ids':sids,'L_ids':lids,'sole_edge_rank':rank,
                     'g_full':full,'g_free':free,'all_extensions':records})
    files=['scripts/round40_classification.py','scripts/round40_four_edge_types.cpp',
           'scripts/round25_forced_verify.py','scripts/kc_core.h']
    files += [f'round40_n{n}_four_types.json' for n in (4,5,6,7) if (ROOT/f'round40_n{n}_four_types.json').exists()]
    out={'minimum_legal_size_nontrivial_four_effect':5,'abstract_labeled_count':255,
         'abstract_isomorphism_type_count':9,'all_types_change_g':True,
         'types':sorted(types.values(),key=lambda r:r['type']),
         'geometric_realizations':realizations,'pure_single_edge_realizations':tiny,
         'geometric_types_realized':sorted({r['type'] for r in realizations}),
         'sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}}
    (ROOT/'round40_classification_verified.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS abstract255 labeled /9 types; minimum L5 realized; geometric types',out['geometric_types_realized'])


if __name__=='__main__':main()
