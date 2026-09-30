"""B350: all small residual antichains and minimum legal-size geometric witness."""
from functools import cache
from itertools import combinations
from pathlib import Path
import hashlib
import json
from round25_forced_verify import geometry,bits,det4

ROOT=Path(__file__).resolve().parents[1]


def game(m,edges):
    edges=tuple(edges)
    @cache
    def g(s):
        seen={g(s|1<<p) for p in range(m) if not s>>p&1 and not any((s|1<<p)&e==e for e in edges)}
        v=0
        while v in seen:v+=1
        return v
    return g(0),[g(1<<p) for p in range(m)],g


def subsets(items):
    for s in range(1<<len(items)):
        yield tuple(e for i,e in enumerate(items) if s>>i&1)


def antichains(m):
    by_rank={r:[sum(1<<p for p in c) for c in combinations(range(m),r)] for r in (2,3,4)}
    for P in subsets(by_rank[2]):
        allowed3=[e for e in by_rank[3] if not any(e&p==p for p in P)]
        for T in subsets(allowed3):
            allowed4=[e for e in by_rank[4] if not any(e&p==p for p in P+T)]
            for Q in subsets(allowed4):yield P,P+T+Q


def geometric(n,sids):
    points,quads,curves=geometry(n);s=sum(1<<p for p in sids);full=(1<<(n*n))-1
    assert all(s&q!=q for q in quads)
    L=full^s
    for c in curves:
        if (s&c).bit_count()==3:L&=~c
    ids=list(bits(L));m=len(ids)
    raw={q&~s for q in quads if not(q&~s)&~L}
    R=sorted(e for e in raw if not any(f!=e and f&e==f for f in raw))
    es=sorted(sum(1<<i for i,p in enumerate(ids) if e>>p&1) for e in R)
    pairs=[e for e in es if e.bit_count()==2]
    fullg,fullchildren,fg=game(m,es);approxg,approxchildren,ag=game(m,pairs)
    win=[p for p,g in zip(ids,fullchildren) if g==0];approxwin=[p for p,g in zip(ids,approxchildren) if g==0]
    assert pairs and fullg==approxg>0 and win!=approxwin
    records=[]
    for t in range(1<<m):
        extension=sum(1<<p for i,p in enumerate(ids) if t>>i&1);occupied=s|extension
        safe=not any(t&e==e for e in es);approx=not any(t&e==e for e in pairs)
        assert safe==all(occupied&q!=q for q in quads)
        assert safe==all((occupied&c).bit_count()<=3 for c in curves)
        assert safe==all(det4([points[p] for p in four])!=0 for four in combinations(list(bits(occupied)),4))
        records.append({'compressed_extension':t,'full_safe':safe,'pair_only_safe':approx,
                        'full_g':fg(t) if safe else None,'pair_only_g':ag(t) if approx else None})
    @cache
    def curve_value(t):
        occupied=s|t;legal=L&~t
        for c in curves:
            if (occupied&c).bit_count()==3:legal&=~c
        seen={curve_value(t|1<<p) for p in bits(legal)}
        v=0
        while v in seen:v+=1
        return v
    for r in records:
        if r['full_safe']:
            t=sum(1<<p for i,p in enumerate(ids) if r['compressed_extension']>>i&1)
            assert curve_value(t)==r['full_g']
    return {'n':n,'S_ids':sids,'L_ids':ids,'R_ids':[list(bits(e)) for e in R],
            'full_g':fullg,'pair_only_g':approxg,'full_child_g':dict(zip(map(str,ids),fullchildren)),
            'pair_only_child_g':dict(zip(map(str,ids),approxchildren)),
            'full_winning_moves':win,'pair_only_winning_moves':approxwin,'all_extensions':records}


def small_board_exclusion():
    results=[]
    for n in (1,2,3):
        points,quads,curves=geometry(n);full=(1<<(n*n))-1;safe_count=0;hits=0
        for s in range(1<<(n*n)):
            if any(s&q==q for q in quads):continue
            safe_count+=1;L=full^s
            for c in curves:
                if (s&c).bit_count()==3:L&=~c
            ids=list(bits(L));raw={q&~s for q in quads if not(q&~s)&~L}
            R=[e for e in raw if not any(f!=e and f&e==f for f in raw)]
            es=tuple(sorted(sum(1<<i for i,p in enumerate(ids) if e>>p&1) for e in R))
            P=tuple(e for e in es if e.bit_count()==2)
            a,ac,_=game(len(ids),es);b,bc,_=game(len(ids),P)
            hits+=a==b and [i for i,g in enumerate(ac) if g==0]!=[i for i,g in enumerate(bc) if g==0]
        assert hits==0 and safe_count=={1:2,2:15,3:298}[n]
        results.append({'n':n,'all_safe_states_checked':safe_count,'B350_hits':hits})
    return results


def bottom_up(m,edges):
    safe=[not any(s&e==e for e in edges) for s in range(1<<m)];g=[None]*(1<<m)
    for s in reversed(range(1<<m)):
        if not safe[s]:continue
        seen={g[s|1<<p] for p in range(m) if not s>>p&1 and safe[s|1<<p]}
        v=0
        while v in seen:v+=1
        g[s]=v
    return g[0],[i for i in range(m) if g[1<<i]==0]


def main():
    census=[]
    for m in range(1,6):
        total=hits=nontrivial_hits=0
        generated=set()
        for P,R in antichains(m):
            if m<=4:generated.add(tuple(sorted(R)))
            total+=1;a,ac,_=game(m,R);b,bc,_=game(m,P)
            if a==b and [i for i,g in enumerate(ac) if g==0]!=[i for i,g in enumerate(bc) if g==0]:
                assert a>0 and any(e.bit_count()>2 for e in R)
                hits+=1;nontrivial_hits+=bool(P)
        assert (hits==0) if m<5 else (nontrivial_hits==330)
        if m<=4:
            pool=[s for s in range(1<<m) if 2<=s.bit_count()<=4];independent=set()
            for R in subsets(pool):
                if any(a!=b and a&b==a for a in R for b in R):continue
                independent.add(tuple(sorted(R)))
                P=[e for e in R if e.bit_count()==2]
                a,aw=bottom_up(m,R);b,bw=bottom_up(m,P)
                assert a!=b or aw==bw
            assert independent==generated and len(independent)==total
        census.append({'legal_size':m,'all_rank_2_3_4_antichains':total,
                       'same_g_different_winning_moves':hits,'hits_with_pair_edge':nontrivial_hits})
        print(census[-1],flush=True)
    small=small_board_exclusion()
    minimum=geometric(5,[14,15,19,23,24]);assert len(minimum['L_ids'])==5
    smaller_board=geometric(4,[0,1,3,5])
    files=['scripts/round43_b350_minimum.py','scripts/round25_forced_verify.py','round2_b321.json']
    out={'original_verdict':'SUPPORTED','minimum_legal_size':5,'minimum_board_n':4,
         'all_small_abstract_families':census,'small_board_exclusions':small,
         'minimum_legal_size_witness':minimum,'minimum_board_witness':smaller_board,
         'sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}}
    (ROOT/'round43_b350_verified.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS B350 minimum legal5; minimum board4; winning',minimum['full_winning_moves'],minimum['pair_only_winning_moves'])


if __name__=='__main__':main()
