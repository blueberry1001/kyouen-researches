"""Exact integer geometry and sharp half-size subsets of a modular parabola.

The universal upper bound is geometric: two complete +/- parameter pairs
form an isosceles trapezoid, so at most one such pair can be selected.
SAT search only constructs matching lower bounds for the recorded primes.
"""
from itertools import combinations
from pathlib import Path
import json
from quadratic_modular_barrier import det4,prime


def forbidden(p):
    pts=[(t,t*t%p) for t in range(p)]
    edges=[]
    # A zero integer determinant must be zero modulo p; Vandermonde then
    # requires i+j+k+l == 0 modulo p. This enumerates each candidate once.
    candidates=0
    for i,j,k in combinations(range(p),3):
        l=(-i-j-k)%p
        if l>k:
            candidates+=1
            if det4([pts[t] for t in (i,j,k,l)])==0:
                edges.append((i,j,k,l))
    return pts,edges,candidates


def clauses_for_pair(p,edges,double):
    out=[]
    for edge in edges:
        requirements={}
        impossible=False
        for t in edge:
            if t==0 or min(t,p-t)==double:
                continue
            v=min(t,p-t)
            sign=t>p//2
            if v in requirements and requirements[v]!=sign:
                impossible=True
                break
            requirements[v]=sign
        if not impossible:
            # Required sign must be violated by at least one selected side.
            out.append(tuple(-v if sign else v for v,sign in requirements.items()))
    return tuple(set(out))


def solve(clauses,assignment=None,counter=None):
    if assignment is None: assignment={}
    if counter is None: counter=[0]
    counter[0]+=1
    while True:
        rem=[]
        unit=None
        for clause in clauses:
            if any(abs(lit) in assignment and assignment[abs(lit)]==(lit>0) for lit in clause):
                continue
            c=tuple(lit for lit in clause if abs(lit) not in assignment)
            if not c: return None
            rem.append(c)
            if len(c)==1: unit=c[0]
        if not rem:return assignment
        if unit is None:break
        assignment=dict(assignment)
        assignment[abs(unit)]=unit>0
        clauses=rem
    counts={}
    for c in rem:
        for lit in c:counts[abs(lit)]=counts.get(abs(lit),0)+1/(2**len(c))
    v=max(counts,key=counts.get)
    for sign in (False,True):
        a=dict(assignment);a[v]=sign
        r=solve(rem,a,counter)
        if r is not None:return r
    return None


def search(p):
    pts,edges,candidates=forbidden(p)
    h=(p-1)//2
    prefix_bad=[e for e in edges if max(e)<=h+1]
    record={'p':p,'upper_bound':h+2,'forbidden_quadruples':len(edges),
        'candidate_quadruples':candidates,'prefix_bad_count':len(prefix_bad),'prefix_first_bad':prefix_bad[:1]}
    for d in range(h,0,-1):
        clauses=clauses_for_pair(p,edges,d)
        counter=[0]
        solution=solve(clauses,counter=counter)
        if solution is not None:
            ts=[0,d,p-d]+[p-i if solution.get(i,False) else i for i in range(1,h+1) if i!=d]
            ts.sort()
            assert len(ts)==h+2 and len(set(ts))==h+2
            selected=set(ts)
            assert not any(set(e)<=selected for e in edges)
            # Verification intentionally ignores the SAT clauses.
            for inds in combinations(ts,4):
                assert det4([pts[i] for i in inds])!=0
            record.update({'maximum_proved':h+2,'double_pair':d,'parameters':ts,
                'coordinates':[pts[i] for i in ts],'sat_calls':counter[0],
                'clauses':len(clauses)})
            return record
    record['upper_bound_attainable']=False
    return record


def main():
    rows=[]
    for p in range(5,128):
        if not prime(p):continue
        rec=search(p);rows.append(rec)
        print(p,rec.get('maximum_proved'),rec['prefix_bad_count'],rec.get('sat_calls'),flush=True)
        Path(__file__).with_suffix('.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
