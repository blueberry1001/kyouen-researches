"""Original-scope finite audit of J4/J5, including every J4 perfect matching.

No legacy graph/game output is imported. Geometry uses the independently
verified integer whole-curve generator; graph routines are implemented here.
"""
from collections import Counter
from functools import cache
from itertools import combinations
from pathlib import Path
import hashlib
import json
import struct
import time
from round25_forced_verify import geometry, bits


def game(n, removed=()):
    points, quads, curves = geometry(n)
    allowed = ((1 << (n*n))-1) ^ sum(1 << p for p in removed)

    @cache
    def children(s):
        legal = allowed ^ s
        for curve in curves:
            if (s & curve).bit_count() == 3:
                legal &= ~curve
        return tuple(s | (1 << p) for p in bits(legal))

    values = {}

    def solve(s):
        if s in values:
            return values[s]
        options = [solve(c) for c in children(s)]
        if not options:
            result = 0, frozenset({s.bit_count()}), frozenset({s.bit_count()})
        else:
            seen = {v[0] for v in options}
            g = next(i for i in range(n*n+1) if i not in seen)
            chosen = [v for v in options if not v[0]] if g else options
            terminal = frozenset().union(*(v[1] for v in chosen))
            forced = (frozenset().union(*(v[2] for v in chosen)) if g
                      else chosen[0][2].intersection(*(v[2] for v in chosen[1:])))
            assert all(t % 2 == (s.bit_count()+bool(g)) % 2 for t in terminal)
            result = g, terminal, forced
        values[s] = result
        return result

    solve(0)
    active = list(bits(allowed))
    edges = [(a,b) for a,b in combinations(active,2) if values[(1 << a)|(1 << b)][0] == 0]
    adjacency = {p:set() for p in active}
    for a,b in edges:
        adjacency[a].add(b); adjacency[b].add(a)
    return points, quads, values, edges, adjacency


def components(adjacency):
    unseen = set(adjacency)
    result = []
    while unseen:
        start = min(unseen); todo=[start]; seen={start}
        while todo:
            p=todo.pop()
            for q in adjacency[p]:
                if q not in seen:
                    seen.add(q); todo.append(q)
        unseen -= seen; result.append(sorted(seen))
    return result


def bipartite(adjacency, removed=()):
    color={}
    allowed=set(adjacency)-set(removed)
    for start in sorted(allowed):
        if start in color: continue
        color[start]=0; todo=[start]
        while todo:
            p=todo.pop()
            for q in adjacency[p]&allowed:
                if q in color:
                    if color[q]==color[p]: return False
                else:
                    color[q]=1-color[p]; todo.append(q)
    return True


def perfect_matchings(adjacency, remaining=None):
    if remaining is None: remaining=set(adjacency)
    if not remaining:
        yield (); return
    p=min(remaining)
    for q in sorted(adjacency[p]&remaining):
        for tail in perfect_matchings(adjacency,remaining-{p,q}):
            yield ((p,q),)+tail


def automorphisms(adjacency):
    vertices=set(adjacency); mapped={}; used=set(); results=[]
    def recurse():
        if len(mapped)==len(vertices):
            results.append(dict(mapped)); return
        p=max(vertices-set(mapped),key=lambda p:(len(adjacency[p]&set(mapped)),len(adjacency[p]),-p))
        for q in sorted(vertices-used):
            if len(adjacency[p])!=len(adjacency[q]): continue
            if any((a in adjacency[p])!=(mapped[a] in adjacency[q]) for a in mapped): continue
            mapped[p]=q; used.add(q); recurse(); used.remove(q); del mapped[p]
    recurse()
    return results


def d4(n):
    result=[]
    for reflect in (False,True):
        for rotations in range(4):
            transform={}
            for p in range(n*n):
                x,y=p%n,p//n
                if reflect: x=n-1-x
                for _ in range(rotations): x,y=n-1-y,x
                transform[p]=x+n*y
            result.append(transform)
    return result


def finite_graphs():
    points,quads,g5,edges,adj=game(5)
    noniso={p:qs for p,qs in adj.items() if qs}
    assert len(g5)==151394 and len(edges)==20 and len(noniso)==16
    corners={0,4,20,24}
    paths=[]
    for a in sorted(corners):
        for b in sorted(adj[a]-corners):
            path=[a,b]
            while path[-1] not in corners:
                choices=adj[path[-1]]-{path[-2]}
                assert len(choices)==1
                path.append(next(iter(choices)))
            if a<path[-1]: paths.append(path)
    assert len(paths)==4 and all(len(p)==5 for p in paths)
    assert sorted((p[0],p[-1]) for p in paths)==sorted(e for e in edges if set(e)<=corners)
    edge_index={edge:i for i,edge in enumerate(edges)}
    def cycle_vector(path):
        mask=0
        for a,b in zip(path,path[1:]+path[:1]):
            mask ^= 1 << edge_index[tuple(sorted((a,b)))]
        return mask
    def rank(vectors):
        pivots={}
        for mask in vectors:
            while mask:
                pivot=mask.bit_length()-1
                if pivot in pivots: mask ^= pivots[pivot]
                else: pivots[pivot]=mask; break
        return len(pivots)
    short_cycles=set()
    for start in noniso:
        def walk(path):
            for q in adj[path[-1]]:
                if q==start and len(path)>=3:
                    cycle=min(tuple(path),tuple([start]+list(reversed(path[1:]))))
                    short_cycles.add(cycle)
                elif q>start and q not in path and len(path)<4:
                    walk(path+[q])
        walk([start])
    basis_cycles=[p for p in paths]+[[0,4,24,20]]
    assert rank([cycle_vector(p) for p in basis_cycles])==5
    assert len(short_cycles)==1 and rank([cycle_vector(list(p)) for p in short_cycles])==1
    matchings=list(perfect_matchings(noniso))
    assert len(matchings)==2
    difference=set(matchings[0])^set(matchings[1])
    diff_adj={p:set() for p in noniso}
    for a,b in difference: diff_adj[a].add(b); diff_adj[b].add(a)
    assert len(difference)==16 and len(components(diff_adj))==1 and all(len(q)==2 for q in diff_adj.values())
    autos=automorphisms(noniso)
    expected={tuple(t[p] for p in sorted(noniso)) for t in d4(5)}
    assert {tuple(t[p] for p in sorted(noniso)) for t in autos}==expected
    all_matching_edges=set().union(*(set(m) for m in matchings))
    dead=sorted(set(edges)-all_matching_edges)
    assert len(dead)==4 and all(set(e)<=corners for e in dead)
    assert all(any({tuple(sorted((t[a],t[b]))) for a,b in m}!=set(m) for t in d4(5)) for m in matchings)
    odd_transversals=[]
    for size in range(3):
        odd_transversals=[list(c) for c in combinations(noniso,size) if bipartite(noniso,c)]
        if odd_transversals: break
    assert size==2
    domination=[]
    for size in range(1,17):
        domination=[list(c) for c in combinations(noniso,size) if all(adj[p]&set(c) for p in noniso)]
        if domination: break
    assert size==8 and len(domination)==18
    interior={p:qs-corners for p,qs in noniso.items() if p not in corners}
    assert len(components(interior))==4 and all(len(c)==3 for c in components(interior))
    edge_values=[{'pair':[a,b],'g':g5[(1<<a)|(1<<b)][0],
                  'Tstar':sorted(g5[(1<<a)|(1<<b)][1]),'WFT':sorted(g5[(1<<a)|(1<<b)][2])} for a,b in edges]
    switches=[{'point':p,'children':[r for r in edge_values if p in r['pair']]}
              for p in noniso if len({tuple(r['WFT']) for r in edge_values if p in r['pair']})>1]
    small_holes=[]
    for removed in (0,4):
        _,_,values,hole_edges,_=game(3,(removed,))
        histogram=Counter(v[0] for s,v in values.items() if s.bit_count()==3)
        small_holes.append({'removed':removed,'J_edges':hole_edges,'three_stone_grundy_hist':dict(histogram)})
    assert all(not r['J_edges'] for r in small_holes)
    assert small_holes[0]['three_stone_grundy_hist']!=small_holes[1]['three_stone_grundy_hist']
    return {'n':5,'safe_states':len(g5),'J_edges':edges,'nonisolated_components':components(noniso),
            'long_paths':paths,'basis_cycles':basis_cycles,'cycle_space_dimension':5,
            'short_cycles_length_at_most_four':sorted(short_cycles),'short_cycle_span_dimension':1,
            'perfect_matchings':matchings,'dead_matching_edges':dead,
            'matching_difference_cycle_length':16,'automorphisms':autos,'minimum_odd_transversals':odd_transversals,
            'minimum_total_dominating_sets':domination,'after_corner_deletion_components':components(interior),
            'edge_game_values':edge_values,'B309_switches':switches,'B018_hole_boards':small_holes}


def fixed_pairings():
    _,quads,values,edges,adj=game(4)
    assert len(values)==5811 and values[0][0]==0 and len(edges)==84
    total_pairs=[list(pair) for pair in combinations(adj,2) if all(adj[p]&set(pair) for p in adj)]
    assert total_pairs and all(tuple(pair) in edges for pair in total_pairs)
    count=0; fail_four=0; survives=[]; examples=[]; digest=hashlib.sha256(); certificates=[]
    quad_set=set(quads)
    def certificate(matching,occupied,opponent,reply):
        mate={p:q for a,b in matching for p,q in ((a,b),(b,a))}
        key=sum(mate[p] << (4*p) for p in range(16))
        return struct.pack('<QHBB',key,occupied,opponent,reply)
    for matching in perfect_matchings(adj):
        count+=1
        pair_masks=[(1<<a)|(1<<b) for a,b in matching]
        digest.update(b''.join(q.to_bytes(2,'little') for q in pair_masks))
        immediate=next(((i,j) for i,j in combinations(range(8),2) if pair_masks[i]|pair_masks[j] in quad_set),None)
        if immediate is not None:
            fail_four+=1
            i,j=immediate
            certificates.append(certificate(matching,pair_masks[i],matching[j][0],matching[j][1]))
            if len(examples)<8:
                i,j=immediate
                examples.append({'matching':matching,'first_pair':matching[i],'second_pair':matching[j],
                                 'forbidden_quad_mask':pair_masks[i]|pair_masks[j]})
        else:
            survives.append(matching)
        if count%25000==0: print('J4 matchings',count,'no fourth-move break',len(survives),flush=True)
    assert count==112212
    later_breaks=[]; valid=[]
    for matching in survives:
        pair_masks=[(1<<a)|(1<<b) for a,b in matching]
        failure=None
        for subset in range(256):
            occupied=0
            for i,pair in enumerate(pair_masks):
                if subset>>i&1: occupied |= pair
            if occupied not in values: continue
            for i,(a,b) in enumerate(matching):
                if subset>>i&1: continue
                if occupied|pair_masks[i] not in values:
                    legal_first=[p for p in (a,b) if occupied|(1<<p) in values]
                    if legal_first:
                        failure={'matching':matching,'paired_prefix_mask':occupied,
                                 'opponent_move':legal_first[0],'illegal_fixed_reply':b if legal_first[0]==a else a}
                        break
            if failure: break
        if failure:
            later_breaks.append(failure)
            certificates.append(certificate(matching,failure['paired_prefix_mask'],
                                             failure['opponent_move'],failure['illegal_fixed_reply']))
        else: valid.append(matching)
    print('J4 ALL',count,'fourth-move failures',fail_four,'later',len(later_breaks),'valid',len(valid),flush=True)
    certificate_path=Path(__file__).resolve().parents[1]/'round27_pairing_failures.bin'
    certificate_path.write_bytes(b'KYPAIR27'+struct.pack('<I',len(certificates))+b''.join(certificates))
    return {'n':4,'safe_states':len(values),'g0':0,'J_edges':edges,'total_dominating_pairs':total_pairs,
            'perfect_matching_count':count,'matching_enumeration_sha256':digest.hexdigest(),
            'fourth_move_failure_count':fail_four,'later_failure_count':len(later_breaks),
            'valid_fixed_pairing_count':len(valid),'fourth_move_examples':examples,
            'later_failure_examples':later_breaks[:16],'valid_fixed_pairing_examples':valid[:16],
            'later_failure_paired_prefix_size_hist':dict(Counter(r['paired_prefix_mask'].bit_count() for r in later_breaks)),
            'certificate_file':certificate_path.name,'certificate_records':len(certificates),
            'certificate_sha256':hashlib.sha256(certificate_path.read_bytes()).hexdigest()}


def main():
    started=time.perf_counter(); source=Path(__file__).resolve(); root=source.parents[1]
    graph5=finite_graphs(); print('J5 finite audit PASS',flush=True)
    graph4=fixed_pairings()
    data={'J5':graph5,'J4':graph4,'sources_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
          for p in (source,source.with_name('round25_forced_verify.py'))},'seconds':time.perf_counter()-started}
    (root/'round27_response_graphs.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    print('saved complete matching audit',flush=True)


if __name__=='__main__': main()
