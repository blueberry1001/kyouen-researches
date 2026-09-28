"""B376/B377/B379: independent audits of the saved complete n8 k8 catalogue.

The input is one uint64 count, followed by that many little-endian masks.
Do not overwrite the source catalogue or the earlier parallel statistics.
"""
from collections import Counter, defaultdict
from functools import lru_cache
from hashlib import sha256
from itertools import combinations, product
from pathlib import Path
import json
import struct

from kyouen_core import is_forbidden_quad
from round9_geometry import curve, evaluate, determinant


def bits(mask):
    while mask:
        bit=mask & -mask
        yield bit.bit_length()-1
        mask-=bit


def points(mask,n=8):
    return [(i%n,i//n) for i in bits(mask)]


def transform(mask,rotation,reflection):
    result=0
    for x,y in points(mask):
        if reflection:x=7-x
        for _ in range(rotation):x,y=7-y,x
        result |= 1<<(8*y+x)
    return result


def exact_cover(coverage,universe,essential):
    fixed=0
    for i in essential:fixed |= coverage[i]
    options={p:[i for i,c in enumerate(coverage) if c>>p&1] for p in bits(universe)}
    @lru_cache(None)
    def solve(missing):
        if missing==0:return ()
        p=min(bits(missing),key=lambda p:len(options[p]))
        best=None
        for i in sorted(options[p],key=lambda i:(coverage[i]&missing).bit_count(),reverse=True):
            answer=(i,*solve(missing & ~coverage[i]))
            if best is None or len(answer)<len(best):best=answer
        return best
    answer=tuple(sorted(essential))+solve(universe & ~fixed)
    assert len(set(answer))==len(answer)
    covered=0
    for i in answer:covered|=coverage[i]
    assert covered & universe==universe
    return answer,solve.cache_info().currsize


def main():
    root=Path(__file__).resolve().parents[3]
    source=root/'research/verification/round4_b371.bin'
    raw=source.read_bytes()
    words=struct.unpack('<'+'Q'*(len(raw)//8),raw)
    masks=words[1:]
    assert words[0]==len(masks)==len(set(masks))==408
    known=set(masks)
    groups=defaultdict(list)
    stabilizers=Counter()
    for mask in masks:
        images=[transform(mask,r,f) for r in range(4) for f in range(2)]
        assert all(t in known for t in images)
        groups[min(images)].append(mask)
        stabilizers[sum(t==mask for t in images)]+=1
    assert len(groups)==51 and all(len(v)==8 for v in groups.values())
    board=[(x,y) for y in range(8) for x in range(8)]
    allrows=[]; essential_hist=Counter(); deletion_hist=Counter(); cover_hist=Counter()
    independent_quad_checks=0; independent_cover_checks=0
    for index,(mask,orbit) in enumerate(sorted(groups.items())):
        stones=points(mask)
        assert len(stones)==8
        for member in orbit:
            ps=points(member)
            for q in combinations(ps,4):
                assert not is_forbidden_quad(q)
                independent_quad_checks+=1
        triples=list(combinations(range(8),3))
        cc=[curve([stones[i] for i in t]) for t in triples]
        assert len(set(cc))==56
        coverage=[0]*56
        empties=[p for p in range(64) if not mask>>p&1]
        private={}
        coverers={}
        for p in empties:
            indices=[]
            for j,c in enumerate(cc):
                flag=evaluate(c,board[p])==0
                direct=determinant([*(stones[i] for i in triples[j]),board[p]])==0
                assert flag==direct
                independent_cover_checks+=1
                if flag:coverage[j]|=1<<p;indices.append(j)
            assert indices
            coverers[p]=indices
            if len(indices)==1:private.setdefault(indices[0],p)
        essential=set(private)
        essential_hist[len(essential)]+=len(orbit)
        assert len(essential)>=13
        legal_after=[]
        for removed in range(8):
            legal=[p for p in empties if all(removed in triples[j] for j in coverers[p])]
            # Include re-placement on the just removed stone.
            count=len(legal)+1
            assert count>=3
            deletion_hist[count]+=len(orbit)
            legal_after.append({'removed':stones[removed],'legal_count_including_removed':count,
                                'newly_legal_original_empty_points':[board[p] for p in legal]})
        chosen,states=exact_cover(coverage,((1<<64)-1)^mask,essential)
        cover_hist[len(chosen)]+=len(orbit)
        allrows.append({'mask':mask,'stones':stones,'orbit_size':len(orbit),
                        'essential_curve_count':len(essential),
                        'private_point_certificate':[{'triple':[stones[t] for t in triples[i]],
                                                       'curve':cc[i],'private_empty_point':board[p]}
                                                      for i,p in sorted(private.items())],
                        'minimum_cover_size':len(chosen),
                        'minimum_cover_triples':[[stones[t] for t in triples[i]] for i in chosen],
                        'cover_dp_states':states,'one_deletions':legal_after})
        print('orbit',index,'essential',len(essential),'minimum cover',len(chosen),flush=True)
    # B379 only needs one exact witness; certify its complete n9 maximality.
    source_mask=2200198721792
    assert source_mask in known
    old=points(source_mask)
    embedded=[(x,y+1) for x,y in old]
    added=(8,0)
    target=[*embedded,added]
    assert all(not is_forbidden_quad(q) for q in combinations(target,4))
    cs=[(t,curve(t)) for t in combinations(target,3)]
    blockers=[]
    for y in range(9):
        for x in range(9):
            p=(x,y)
            if p in target:continue
            triple,c=next((t,c) for t,c in cs if evaluate(c,p)==0)
            assert is_forbidden_quad([*triple,p])
            blockers.append({'empty_point':p,'blocking_triple':triple})
    assert len(blockers)==72
    seven=json.loads((root/'research/verification/data/s8_exact.json').read_text(encoding='utf-8'))
    seven_run=next(z for z in seven['runs'] if z['n']==8 and z['k']==7)
    assert seven_run['complete'] and not seven_run['found']
    result={'B376':'REFUTED','B377':'SUPPORTED','B379':'SUPPORTED',
            'input_source':str(source.relative_to(root)),'source_sha256':sha256(raw).hexdigest(),
            'source_maximal_sets':len(masks),'d4_orbits':len(groups),
            'stabilizer_order_histogram':dict(stabilizers),
            'essential_curve_count_histogram_all_sets':dict(sorted(essential_hist.items())),
            'minimum_cover_size_histogram_all_sets':dict(sorted(cover_hist.items())),
            'one_deletion_legal_count_histogram':dict(sorted(deletion_hist.items())),
            'independent_quad_checks':independent_quad_checks,
            'independent_cover_checks_on_representatives':independent_cover_checks,
            'B377_zero_legal_dependency':{'source':'data/s8_exact.json',
                    'sha256':sha256((root/'research/verification/data/s8_exact.json').read_bytes()).hexdigest(),
                    'complete':True,'found_seven_stone_maximal':False},
            'orbits':allrows,
            'B379_witness':{'source_mask':source_mask,'source_points':old,'embedding_translation':[0,1],
                            'removed':[],'added':[added],'target':target,'blockers':blockers}}
    path=root/'research/verification/round10_small_saturation.json'
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('essential',dict(sorted(essential_hist.items())),'minimum cover',dict(sorted(cover_hist.items())),flush=True)
    print(path,flush=True)


if __name__=='__main__':main()
