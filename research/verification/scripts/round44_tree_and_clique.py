"""Exact tree residual witnesses and an infinite three-stone clique family."""
from itertools import combinations
from pathlib import Path
import hashlib
import json
from round25_forced_verify import geometry,bits,det4
from round43_b350_minimum import game,antichains

ROOT=Path(__file__).resolve().parents[1]


def residual(n,sids):
    points,quads,curves=geometry(n);s=sum(1<<p for p in sids);full=(1<<(n*n))-1
    assert all(s&q!=q for q in quads)
    L=full^s
    for c in curves:
        if (s&c).bit_count()==3:L&=~c
    raw={q&~s for q in quads if not(q&~s)&~L}
    R=sorted(e for e in raw if not any(f!=e and f&e==f for f in raw))
    return points,quads,curves,s,L,R


def tree_witness(n,sids):
    points,quads,curves,s,L,R=residual(n,sids);ids=list(bits(L));m=len(ids)
    es=[sum(1<<i for i,p in enumerate(ids) if e>>p&1) for e in R];P=[e for e in es if e.bit_count()==2]
    assert len(P)==m-1
    reached=1
    while True:
        new=reached
        for e in P:
            if e&reached:new|=e
        if new==reached:break
        reached=new
    assert reached==(1<<m)-1
    a,ac,fg=game(m,es);b,bc,ag=game(m,P);assert a!=b
    records=[]
    for t in range(1<<m):
        occupied=s|sum(1<<p for i,p in enumerate(ids) if t>>i&1)
        safe=not any(t&e==e for e in es);approx=not any(t&e==e for e in P)
        assert safe==all(occupied&q!=q for q in quads)
        assert safe==all((occupied&c).bit_count()<=3 for c in curves)
        assert safe==all(det4([points[p] for p in four])!=0 for four in combinations(list(bits(occupied)),4))
        records.append({'extension':t,'full_safe':safe,'pair_safe':approx,
                        'full_g':fg(t) if safe else None,'pair_g':ag(t) if approx else None})
    return {'n':n,'S_ids':sids,'L_ids':ids,'R_ids':[list(bits(e)) for e in R],
            'full_g':a,'pair_only_g':b,'full_child_g':ac,'pair_child_g':bc,'all_extensions':records}


def coloring(ids,edges,count):
    adjacency={p:{q for q in ids if q!=p and ((1<<p)|(1<<q)) in edges} for p in ids}
    order=sorted(ids,key=lambda p:(-len(adjacency[p]),p));assigned={}
    def visit(i):
        if i==len(order):return True
        p=order[i];used={assigned[q] for q in adjacency[p] if q in assigned}
        for c in range(count):
            if c in used:continue
            assigned[p]=c
            if visit(i+1):return True
            del assigned[p]
        return False
    return assigned.copy() if visit(0) else None


def main():
    tiny=tree_witness(4,[9,11,13,14]);board_min=tree_witness(3,[0,1,6])
    assert len(tiny['L_ids'])==4 and tiny['full_g']==2 and tiny['pair_only_g']==1
    assert board_min['full_g']==0 and board_min['pair_only_g']==3
    tree_small=[]
    for m in range(1,5):
        candidates=value_changes=winner_changes=0
        for P,R in antichains(m):
            if len(P)!=m-1:continue
            reached=1
            while True:
                new=reached
                for e in P:
                    if reached&e:new|=e
                if new==reached:break
                reached=new
            if reached!=(1<<m)-1:continue
            candidates+=1;a,_,_=game(m,R);b,_,_=game(m,P)
            value_changes+=a!=b;winner_changes+=bool(a)!=bool(b)
        assert winner_changes==0
        tree_small.append({'legal_size':m,'tree_residual_antichains':candidates,
                           'value_changes':value_changes,'winner_changes':winner_changes})
    small=[]
    for n in (1,2):
        hits=0;safe_count=0
        for s in range(1<<(n*n)):
            if s.bit_count()==4:continue
            points,quads,curves,_,L,R=residual(n,list(bits(s)))
            safe_count+=1;ids=list(bits(L));m=len(ids)
            es=[sum(1<<i for i,p in enumerate(ids) if e>>p&1) for e in R]
            P=[e for e in es if e.bit_count()==2]
            if m<=1 or len(P)!=m-1:continue
            a,_,_=game(m,es);b,_,_=game(m,P);hits+=a!=b
        assert hits==0 and safe_count=={1:2,2:15}[n]
        small.append({'n':n,'all_safe_sets':safe_count,'tree_value_change_hits':0})
    points,quads,curves,s,L,R=residual(4,[0,1,2]);ids=list(bits(L));P={e for e in R if e.bit_count()==2}
    clique=[4,7,8,11,13,14]
    assert all((1<<a|1<<b) in P for a,b in combinations(clique,2))
    colors=coloring(ids,P,6);assert colors is not None
    clique_record={'n':4,'S_ids':[0,1,2],'L_ids':ids,
                  'pair_edges':[list(bits(e)) for e in sorted(P)],'clique_ids':clique,'six_coloring':colors}
    small_chromatic=[]
    for n in (2,3):
        tested=0
        for sids in combinations(range(n*n),3):
            _,_,_,s,L,R=residual(n,list(sids));P={e for e in R if e.bit_count()==2}
            assert coloring(list(bits(L)),P,3) is not None;tested+=1
        small_chromatic.append({'n':n,'all_three_stone_sets':tested,'all_chromatic_numbers_at_most':3})
    family=[]
    for M in range(1,9):
        radius=1
        for a in range(2,M+2):radius*=a*a+1
        S=[(0,radius),(radius,radius),(2*radius,radius)]
        clique_points=[]
        for a in range(2,M+2):
            scale=radius//(a*a+1);x=(a*a-1)*scale;y=2*a*scale
            for sx,sy in [(1,1),(1,-1),(-1,1),(-1,-1)]:
                clique_points.append((radius+sx*x,radius+sy*y))
        assert len(set(clique_points))==4*M
        assert all((x-radius)**2+(y-radius)**2==radius*radius for x,y in clique_points)
        assert all(det4(S+[p])!=0 for p in clique_points)
        assert all(det4([S[0],S[2],p,q])==0 for p,q in combinations(clique_points,2))
        family.append({'M':M,'n':2*radius+1,'radius':radius,'S_coordinates':S,
                       'induced_clique_size':4*M,'legal_clique_points':clique_points})
    files=['scripts/round44_tree_and_clique.py','scripts/round43_b350_minimum.py','scripts/round25_forced_verify.py']
    out={'B062_original_verdict':'REFUTED','B062_stronger_statement':'Three occupied stones have unbounded competition chromatic number.',
         'B062_minimum_counterexample_board':4,'B062_exact_chromatic_six':clique_record,
         'small_chromatic_exclusions':small_chromatic,'infinite_clique_family_samples':family,
         'B064_original_verdict':'SUPPORTED','B064_minimum_legal_size_for_winner_change':5,
         'tree_minimum_legal_size_for_value_change':4,'B064_minimum_board':3,
         'all_small_tree_antichains':tree_small,
         'tree_minimum_legal_witness':tiny,'tree_minimum_board_witness':board_min,'small_tree_exclusions':small,
         'B344_original_verdict':'PARTIAL','B344_partial_result':'Unique minimum connecting tree is K1,3 with triple on all leaves; broader parity classification not proved.',
         'sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}}
    (ROOT/'round44_tree_clique_verified.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS B062 chi6 minboard4 and unbounded chi with3 stones; B064 winner minlegal5 minboard3; value minlegal4')


if __name__=='__main__':main()
