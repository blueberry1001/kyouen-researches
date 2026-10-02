"""Independent checks for private passes forbidden at ordinary terminal states.

F(G,a,b) is the mex of the relative-state option DAG. No assertion is made
about disjunctive sums with private resources.

Theorem 1: F(G,a+r,b+r)=F(G,a,b).
Theorem 2: at ordinary terminal states the current player loses. Else:
 a>b: current player wins;
 a=b: ordinary outcome;
 a<b: current player wins iff some ordinary move reaches a terminal state.
"""
from functools import lru_cache
from itertools import combinations, product
from pathlib import Path
import hashlib
import json
import random


def mex(xs):
    xs=set(xs)
    i=0
    while i in xs: i+=1
    return i


def analyze(options, max_rights=5):
    @lru_cache(None)
    def ordinary(v):
        return mex(ordinary(w) for w in options[v])

    @lru_cache(None)
    def extended(v,a,b):
        if not options[v]: return 0
        values=[extended(w,b,a) for w in options[v]]
        if a: values.append(extended(v,b,a-1))
        return mex(values)

    winner_checks=cancellation_checks=0
    for v in options:
        terminal=not options[v]
        immediate=any(not options[w] for w in options[v])
        for a in range(max_rights+1):
            for b in range(max_rights+1):
                expected=(False if terminal else
                    (ordinary(v)!=0 if a==b else (True if a>b else immediate)))
                assert bool(extended(v,a,b))==expected,(v,a,b,expected)
                winner_checks+=1
                if a<max_rights and b<max_rights:
                    assert extended(v,a+1,b+1)==extended(v,a,b),(v,a,b)
                    cancellation_checks+=1
    return dict(vertices=len(options),winner_checks=winner_checks,
                cancellation_checks=cancellation_checks), ordinary, extended


def det3(a,b,c):
    return (a[0]*(b[1]*c[2]-b[2]*c[1])
           -a[1]*(b[0]*c[2]-b[2]*c[0])
           +a[2]*(b[0]*c[1]-b[1]*c[0]))


def forbidden(n):
    points=[(i%n,i//n) for i in range(n*n)]
    result=[]
    for ids in combinations(range(n*n),4):
        base=points[ids[-1]]
        base_norm=base[0]**2+base[1]**2
        rows=[(points[i][0]-base[0],points[i][1]-base[1],
               points[i][0]**2+points[i][1]**2-base_norm) for i in ids[:-1]]
        if det3(*rows)==0:
            result.append(sum(1<<i for i in ids))
    return result


def board_graph(n):
    q=forbidden(n)
    all_masks=range(1<<(n*n))
    safe={mask for mask in all_masks if not any(mask&quad==quad for quad in q)}
    options={mask:tuple(mask|(1<<i) for i in range(n*n)
                       if not mask>>i&1 and mask|(1<<i) in safe) for mask in safe}
    return q,options


def main():
    exhaustive={}; totals=dict(winner_checks=0,cancellation_checks=0)
    def accumulate(stats):
        for key in totals: totals[key]+=stats[key]
    for n in range(1,6):
        count=0
        for masks in product(*(range(1<<i) for i in range(n))):
            options={i:tuple(j for j in range(i) if masks[i]>>j&1) for i in range(n)}
            stats,_,_=analyze(options)
            accumulate(stats); count+=1
        exhaustive[str(n)]=count
    rng=random.Random(20261003)
    for _ in range(200):
        options={i:tuple(j for j in range(i) if rng.randrange(5)==0) for i in range(40)}
        stats,_,_=analyze(options)
        accumulate(stats)
    boards={}; witness=None
    for n in range(1,5):
        q,options=board_graph(n)
        stats,g,f=analyze(options)
        accumulate(stats)
        boards[str(n)]={**stats,"forbidden_quadruples":len(q)}
        if n==2:
            witness={"board_n":2,"index_convention":"id=x+2*y",
                     "rights_current_opponent":[0,1],"states":[]}
            for mask in (0,3):
                witness["states"].append(dict(
                    stones=[i for i in range(4) if mask>>i&1],
                    ordinary_mex=g(mask),pass_mex=f(mask,0,1),
                    legal_moves=[(child^mask).bit_length()-1 for child in options[mask]],
                    move_to_terminal=any(not options[child] for child in options[mask])))
    result=dict(
        rule="ordinary terminal states end immediately; passing there is forbidden",
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        exhaustive_dag_counts_by_vertices=exhaustive,
        random_dags=dict(count=200,vertices=40,seed=20261003),
        rights_tested=list(range(6)),boards=boards,
        totals=totals,failures=0,minimal_board_counterexample=witness,
        novelty_scope="additional statements not located in the inspected repository; no claim of academic priority")
    Path(__file__).with_suffix('.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
