"""Finite exact checks supporting the separate general asymptotic proofs.

No finite table here is used as a proof of an asymptotic claim.
"""
from collections import Counter
from itertools import combinations, permutations, product
from math import comb, prod
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'research/verification'


def det4(a):
    ans=0
    for p in permutations(range(4)):
        sign=(-1)**sum(p[i]>p[j] for i in range(4) for j in range(i+1,4))
        ans+=sign*prod(a[i][p[i]] for i in range(4))
    return ans


def check_five_point_matrices():
    quads=list(combinations(range(5),4))
    dets=Counter()
    cases=[]
    for choices in product(range(3),repeat=5):
        rows=[]
        for Q,choice in zip(quads,choices):
            a,b,c,d=Q
            plus,minus=[((a,b),(c,d)),((a,c),(b,d)),((a,d),(b,c))][choice]
            row=[0]*4
            for i in plus:
                if i:row[i-1]+=1
            for i in minus:
                if i:row[i-1]-=1
            rows.append(row)
        found=None
        for omitted in range(5):
            d=det4([r for i,r in enumerate(rows) if i!=omitted])
            if d:
                found={'choices':choices,'omitted_row':omitted,'determinant':d}
                dets[d]+=1
                break
        assert found is not None
        cases.append(found)
    return {'systems':len(cases),'rank4':len(cases),'minor_determinant_hist':dict(dets),'certificates':cases}


def forbidden(Q):
    x0,y0=Q[0]
    v=[(x-x0,y-y0,(x-x0)**2+(y-y0)**2) for x,y in Q[1:]]
    a,b,c=v
    d=a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0])
    return d==0


def small_hypergraph(n):
    pts=[(x,y) for x in range(n) for y in range(n)]
    edges=[tuple(Q) for Q in combinations(range(n*n),4) if forbidden([pts[i] for i in Q])]
    incidence=[None]+[Counter(t for E in edges for t in combinations(E,j)) for j in (1,2,3)]
    overlaps=Counter(len(set(E)&set(F)) for E,F in combinations(edges,2))
    eset={frozenset(E) for E in edges}
    r_hist=Counter()
    for Q in combinations(range(n*n),5):
        r=sum(frozenset(E) in eset for E in combinations(Q,4))
        assert r in (0,1,5)
        r_hist[r]+=1
    g5=r_hist[5]
    assert overlaps[3]==10*g5
    assert r_hist[0]==comb(n*n,5)-len(edges)*(n*n-4)+4*g5
    # Count pairs by their shared triples, as a second route.
    assert sum(comb(v,2) for v in incidence[3].values())==overlaps[3]
    assert len(edges)=={3:14,4:194,5:826}[n]
    return {'n':n,'forbidden_quads':len(edges),'max_codegrees':{j:max(incidence[j].values()) for j in (1,2,3)},
            'edge_pair_intersections':dict(overlaps),'five_set_edge_histogram':dict(r_hist),
            'G5':g5,'A3':overlaps[3],'p5_coefficient':4*g5,'identities_pass':True}


def asymmetric(Q):
    a,b,c,d=Q
    def parallel(a,b,c,d):
        return (b[0]-a[0])*(d[1]-c[1])-(b[1]-a[1])*(d[0]-c[0])==0
    return not (parallel(a,b,c,d) or parallel(a,c,b,d) or parallel(a,d,b,c))


def rich_circles():
    source=OUT/'round3_b451_census.json'
    boards=json.loads(source.read_text())['boards']
    checks=[]
    for ns,data in boards.items():
        quad_count=0
        asym_count=0
        for row in data['rows_m_ge5']:
            pts=row['pts'];m=len(pts)
            assert m==row['m'] and m>=5
            a=sum(asymmetric(Q) for Q in combinations(pts,4))
            assert comb(m,4)<=5*a,(ns,row,a)
            quad_count+=comb(m,4)
            asym_count+=a
        assert quad_count==sum(comb(int(m),4)*count for m,count in data['m_hist'].items() if int(m)>=5)
        assert quad_count+data['m_hist'].get('4',0)==data['n_concyclic_quads']
        checks.append({'n':int(ns),'rich_circles':len(data['rows_m_ge5']),
                       'quad_contribution':quad_count,'asymmetric_quad_contribution':asym_count,
                       'each_circle_bound_pass':True})
    return {'source':source.name,'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'boards':checks}


def main():
    mats=check_five_point_matrices()
    print('all',mats['systems'],'integer systems have rank 4',flush=True)
    small=[small_hypergraph(n) for n in (3,4,5)]
    print('small hypergraph identities passed',flush=True)
    rich=rich_circles()
    print('rich circle inequalities passed',len(rich['boards']),'boards',flush=True)
    result={'five_point_lemma':mats,'small_hypergraphs':small,'rich_circle_catalog_check':rich,
            'scope':'finite cross-checks only; asymptotic proofs are in the two round13 markdown files',
            'external_inputs':[
                {'authors':'Ghosal, Goenka, Keevash','url':'https://link.springer.com/article/10.1007/s00454-026-00853-7',
                 'used':['Theorem 1.3: C_n=Theta(n^5)','Lemma 4.1: asymmetric count O_epsilon(n^(4+18/29+epsilon))']},
                {'authors':'Arratia, Goldstein, Gordon','year':1989,'theorem':1,
                 'url':'https://dornsife.usc.edu/larry-goldstein/wp-content/uploads/sites/221/2023/06/AGG.pdf'}]}
    (OUT/'round13_asymptotic_checks.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
