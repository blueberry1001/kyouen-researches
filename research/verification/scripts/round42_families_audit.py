"""Fresh full 4x4 census: exact labeled families and their exchange components."""
from collections import defaultdict
from itertools import combinations,permutations
from functools import cache
from pathlib import Path
import hashlib
import json
from round25_forced_verify import geometry,bits,det4

ROOT=Path(__file__).resolve().parents[1]


@cache
def canonical(m,edges):
    return min(tuple(sorted(sum(1<<perm[p] for p in bits(e)) for e in edges))
               for perm in permutations(range(m)))


def components(states,width):
    left=set(states);answer=[]
    while left:
        todo=[left.pop()];part=[]
        while todo:
            a=todo.pop();part.append(a)
            neighbors=[b for b in left if (a^b).bit_count()<=2*width]
            left.difference_update(neighbors);todo.extend(neighbors)
        answer.append(sorted(part))
    return sorted(answer,key=lambda p:(-len(p),p))


def main():
    points,quads,curves=geometry(4);full=65535
    def legal(s):
        L=full^s
        for c in curves:
            if (s&c).bit_count()==3:L&=~c
        return L
    states=[s for s in range(65536) if all(s&q!=q for q in quads)]
    assert len(states)==5811
    groups=defaultdict(list);withoutL=defaultdict(list);single_pair_abstract=defaultdict(list)
    signature={}
    for s in states:
        L=legal(s);raw={q&~s for q in quads if not(q&~s)&~L}
        edges=tuple(sorted(e for e in raw if not any(f!=e and f&e==f for f in raw)))
        by_curve=set()
        quad_L=full^s
        for q in quads:
            r=q&~s
            if r.bit_count()==1:quad_L&=~r
        assert quad_L==L
        for c in curves:
            need=4-(s&c).bit_count();available=list(bits(c&L))
            for choice in combinations(available,need):by_curve.add(sum(1<<p for p in choice))
        curve_edges=tuple(sorted(e for e in by_curve if not any(f!=e and f&e==f for f in by_curve)))
        assert curve_edges==edges
        signature[s]=(s.bit_count(),L,edges)
        groups[signature[s]].append(s);withoutL[(s.bit_count(),edges)].append(s)
        if L.bit_count()==2 and edges==(L,):single_pair_abstract[s.bit_count()].append(s)
    multi={key:members for key,members in groups.items() if len(members)>1}
    counts={'multi_families':len(multi),'one_exchange_disconnected':0,'two_exchange_disconnected':0}
    witnesses={};failure_metric=None
    for key,members in sorted(multi.items()):
        c1=components(members,1);c2=components(members,2)
        counts['one_exchange_disconnected']+=len(c1)>1
        counts['two_exchange_disconnected']+=len(c2)>1
        if len(c1)>1 and key[1].bit_count()==2 and key[2]==(key[1],) and 'connected_R' not in witnesses:
            witnesses['connected_R']={'k':key[0],'L_ids':list(bits(key[1])),
                                      'R_ids':[list(bits(e)) for e in key[2]],
                                      'all_family_S_masks':members,'one_exchange_components':c1,
                                      'same_R_without_L_family':withoutL[(key[0],key[2])]}
        if len(c2)>1 and 'two_exchange_failure' not in witnesses:
            witnesses['two_exchange_failure']={'k':key[0],'L_ids':list(bits(key[1])),
                                              'R_ids':[list(bits(e)) for e in key[2]],
                                              'all_family_S_masks':members,'two_exchange_components':c2,
                                              'same_R_without_L_family':withoutL[(key[0],key[2])]}
        if len(c1)>1 and failure_metric is None:
            reps=[]
            for i,part in enumerate(c1):
                for s in part:
                    old_illegal=full&~s&~key[1]
                    release={a:list(bits(legal(s^(1<<a))&old_illegal)) for a in bits(s)}
                    for removed,freed in release.items():
                        kept=list(bits(s^(1<<removed)))
                        direct=[p for p in bits(old_illegal) if all(det4([points[q] for q in (*triple,p)])!=0
                                                                  for triple in combinations(kept,3))]
                        assert direct==freed
                    maximum=max(map(len,release.values()),default=0)
                    reps.append((i,s,maximum,release))
            for a,b in combinations(reps,2):
                if a[0]!=b[0] and a[2]!=b[2]:
                    failure_metric={'k':key[0],'L_ids':list(bits(key[1])),'R_ids':[list(bits(e)) for e in key[2]],
                                    'all_family_S_masks':members,'one_exchange_components':c1,
                                    'representatives':[{'component':x[0],'S_ids':list(bits(x[1])),
                                      'max_original_illegal_points_freed_by_one_removal':x[2],
                                      'release_by_removed_stone':x[3]} for x in (a,b)]}
                    break
    abstract=single_pair_abstract[5]
    abstract_parts=components(abstract,1)
    witnesses['exact_abstract_pair_family']={'k':5,'L_size':2,'R_abstract':'one two-edge',
                                           'all_family_S_masks':abstract,'one_exchange_components':abstract_parts}
    witnesses['different_release_capacity']=failure_metric
    assert failure_metric and failure_metric['k']==4
    assert witnesses['two_exchange_failure']['same_R_without_L_family']==witnesses['two_exchange_failure']['all_family_S_masks']
    bridge_ids=[[5,8,11,14],[5,8,14],[7,8,14],[7,13,14],[7,13,14,15]]
    bridge=[sum(1<<p for p in ids) for ids in bridge_ids]
    assert all(s in states for s in bridge)
    assert all((a^b).bit_count() in (1,2) for a,b in zip(bridge,bridge[1:]))
    witnesses['four_stone_bridge_through_three_stones']={'path_S_ids':bridge_ids,'all_states_safe':True}
    abstract_groups=defaultdict(list)
    for s,(k,L,R) in signature.items():
        ids=list(bits(L));m=len(ids)
        if m>6:continue
        es=tuple(sorted(sum(1<<i for i,p in enumerate(ids) if e>>p&1) for e in R))
        abstract_groups[(k,m,canonical(m,es))].append(s)
    witnesses['exact_nonempty_abstract_split']=None
    for (k,m,R),members in sorted(abstract_groups.items()):
        if not R or len(members)<2:continue
        parts=components(members,1)
        if len(parts)>1:
            witnesses['exact_nonempty_abstract_split']={'k':k,'L_size':m,'canonical_R_compressed':list(R),
              'all_family_S_masks':members,'one_exchange_components':parts,
              'all_member_signatures':[{'S_mask':s,'L_ids':list(bits(signature[s][1])),
               'R_ids':[list(bits(e)) for e in signature[s][2]]} for s in members]}
            break
    files=['scripts/round42_families_audit.py','scripts/round25_forced_verify.py']
    out={'n':4,'all_65536_subsets_tested':True,'safe_state_count':len(states),'counts':counts,
         'witnesses':witnesses,'sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}}
    (ROOT/'round42_families_verified.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(counts)
    for k,r in witnesses.items():
        print(k, 'none' if r is None else (r.get('k'),len(r.get('all_family_S_masks',[])),len(r.get('one_exchange_components',r.get('two_exchange_components',[])))))
    if failure_metric:print('B446',failure_metric['representatives'])


if __name__=='__main__':main()
