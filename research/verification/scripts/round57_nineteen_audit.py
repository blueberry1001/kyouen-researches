"""Independently verify K10 >=19 and record a bounded local obstruction."""
from pathlib import Path
from itertools import combinations
from math import comb
from collections import Counter
import hashlib
import json
from round25_forced_verify import bits,curve,det4,geometry
from round55_eighteen_audit import COORDINATES

ROOT=Path(__file__).resolve().parents[1]


def main():
    points,quads,curves=geometry(10)
    embeddings=[]
    for dx,dy in [(0,0),(0,1),(1,0),(1,1)]:
        s=[(x+dx,y+dy) for x,y in COORDINATES]
        triples=list(combinations(s,3))
        legal=[p for p,point in enumerate(points) if point not in s and all(det4((*t,point)) for t in triples)]
        embeddings.append({'offset':[dx,dy],'legal_ids':legal})
    assert [r['legal_ids'] for r in embeddings]==[[],[9],[],[0]]
    ids=sorted([x+10*(y+1) for x,y in COORDINATES]+[9])
    selected=[points[p] for p in ids]
    mask=sum(1<<p for p in ids)
    assert len(ids)==len(set(ids))==19
    assert all(det4(q) for q in combinations(selected,4))
    assert all(mask&q != q for q in quads)
    assert all((mask&c).bit_count()<=3 for c in curves)
    triples=list(combinations(selected,3))
    blocks={}
    for p,point in enumerate(points):
        if p in ids:
            continue
        blocked=[t for t in triples if det4((*t,point))==0]
        assert blocked
        blocks[str(p)]=list(blocked[0])
    local=json.loads((ROOT/'round57_n10_neighborhood.json').read_text())
    assert local['seed_ids']==ids and local['found'] is False
    assert local['local_complete'] is True and local['complete_deletion_radius']==8
    assert local['subsets_examined']==sum(comb(19,r) for r in range(1,9))==169765
    src=ROOT/'scripts/round57_n10_nineteen_neighborhood.cpp'
    assert local['source_sha256']==hashlib.sha256(src.read_bytes()).hexdigest()
    # Verify the row-pair accounting used for the general 2.5n upper bound.
    rowcounts=Counter(y for x,y in selected)
    sums=[]
    for y in range(10):
        xs=[x for x,yy in selected if yy==y]
        assert len(xs)<=3
        assert comb(len(xs),2)>=2*len(xs)-3
        sums.extend(a+b for a,b in combinations(xs,2))
    assert len(sums)==len(set(sums)) and all(1<=s<=17 for s in sums)
    files=['scripts/round57_nineteen_audit.py','scripts/round57_n10_nineteen_neighborhood.cpp',
           'scripts/round25_forced_verify.py','scripts/round55_eighteen_audit.py',
           'round55_eighteen_verified.json','round57_n10_neighborhood.json']
    output={'B082_original_verdict':'PARTIAL','K10_bounds':[19,23],
            'nineteen_stone_ids':ids,'nineteen_stone_coordinates':selected,
            'quadruples_checked':comb(19,4),'maximal':True,
            'blocking_triple_by_empty_id':blocks,'all_four_embeddings':embeddings,
            'local_complete_deletion_radius':8,
            'any_twenty_stone_safe_set_overlap_with_this_seed_at_most':10,
            'local_exclusion_is_not_a_global_upper_bound':True,
            'row_pair_sums':sorted(sums),
            'sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}}
    (ROOT/'round57_nineteen_verified.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    print('PASS independent nineteen safe stones; 19<=K10<=23; complete local deletion radii 1..8')


if __name__=='__main__':
    main()
