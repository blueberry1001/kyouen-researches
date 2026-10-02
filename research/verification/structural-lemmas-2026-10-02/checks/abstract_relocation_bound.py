"""Exhaustively classify the abstract four-point extremal switch.

On one fixed board the forbidden 4-set is shared. Pair constraints are
shared; only (minimal) triples can differ. Enumerate all such models on
four labelled legal points, including models not geometrically realizable.
"""
from itertools import combinations, permutations
from functools import lru_cache
from pathlib import Path
import json

def bitset(t):return sum(1<<i for i in t)
def bits(t):return [i for i in range(4) if t>>i&1]
def g(edges):
    @lru_cache(None)
    def solve(s):
        vals={solve(s|1<<p) for p in range(4) if not s>>p&1 and not any((s|1<<p)&e==e for e in edges)}
        v=0
        while v in vals:v+=1
        return v
    return solve(0)
def transform(e,p):return bitset(p[i] for i in bits(e))
def canonical(pairs,trip0,trip1):
    return min((tuple(sorted(transform(e,p) for e in pairs)),tuple(sorted(transform(e,p) for e in trip0)),tuple(sorted(transform(e,p) for e in trip1))) for p in permutations(range(4)))

pairs_all=[bitset(t) for t in combinations(range(4),2)]
triples_all=[bitset(t) for t in combinations(range(4),3)]
extremal=[]; models=0; pairwise_comparisons=0
for psel in range(1<<len(pairs_all)):
    pairs=[p for i,p in enumerate(pairs_all) if psel>>i&1]
    triples=[t for t in triples_all if not any(t&p==p for p in pairs)]
    for four in (False,True):
        forms=[]
        for tsel in range(1<<len(triples)):
            ts=[t for i,t in enumerate(triples) if tsel>>i&1]
            value=g(pairs+ts+([15] if four else []));models+=1
            forms.append((ts,value))
        for (ts,g0),(us,g1) in combinations(forms,2):
            pairwise_comparisons+=1
            assert abs(g0-g1)<=3
            if abs(g0-g1)==3:
                low,high=(ts,us) if g0<g1 else (us,ts)
                extremal.append(canonical(pairs,low,high))
classes=sorted(set(extremal))
assert classes==[((3,), (13,14), (13,)),((3,5), (14,), ())]
out={'labelled_models_including_redundant_shared_four_edge':models,'comparisons_with_shared_pairs_and_four_edge':pairwise_comparisons,'extremal_comparisons':len(extremal),'maximum_grundy_spread':3,'abstract_isomorphism_classes_with_spread_three':len(classes),'classes':[{'pairs':[bits(e) for e in p],'g0_triples':[bits(e) for e in lo],'g3_triples':[bits(e) for e in hi]} for p,lo,hi in classes],'note':'The possible shared four-edge is redundant in both extremal types. Only the second type is claimed as a pair of actual square-board states here.'}
Path(__file__).with_name('abstract_relocation_bound.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out))
