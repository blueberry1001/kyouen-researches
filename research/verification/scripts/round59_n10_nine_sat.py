"""Witness search for n10 maximal sets with at most nine stones; UNSAT remains unchecked."""
import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
from round25_forced_verify import geometry,bits

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=int,default=600)
    parser.add_argument('--pysat-path',default=str(Path(tempfile.gettempdir())/'kyouen-round46-pysat'))
    args=parser.parse_args();sys.path.insert(0,args.pysat_path)
    import pysat,pysolvers
    from pysat.card import CardEnc,EncType
    from pysat.solvers import Glucose4
    points,quads,curves=geometry(10);V=100;assert len(quads)==54441
    completion=defaultdict(int)
    for q in quads:
        for p in bits(q):completion[q^(1<<p)]|=1<<p
    assert sum(c.bit_count() for c in completion.values())==217764
    assert max(c.bit_count() for c in completion.values())==9
    clauses=[[-(p+1) for p in bits(q)] for q in quads]
    blocker_variables={t:V+1+i for i,t in enumerate(sorted(completion))};covering=[[] for p in range(V)]
    for t,z in blocker_variables.items():
        for p in bits(t):clauses.append([-z,p+1])
        for p in bits(completion[t]):covering[p].append(z)
    for p in range(V):clauses.append([p+1]+covering[p])
    card=CardEnc.atmost(lits=list(range(1,V+1)),bound=9,top_id=V+len(completion),encoding=EncType.seqcounter)
    clauses.extend(card.clauses)
    folder=Path(tempfile.gettempdir())/'kyouen-round59-sat';folder.mkdir(exist_ok=True)
    formula=folder/'n10_atmost9.cnf'
    with formula.open('w',encoding='ascii',newline='\n') as f:
        f.write(f'p cnf {card.nv} {len(clauses)}\n')
        for clause in clauses:f.write(' '.join(map(str,clause))+' 0\n')
    print('fresh integer geometry, clauses',len(clauses),'variables',card.nv,'; solving atmost9',flush=True)
    with Glucose4(bootstrap_with=clauses) as solver:
        timer=threading.Timer(args.seconds,solver.interrupt);timer.start();started=time.monotonic()
        try:result=solver.solve_limited(expect_interrupt=True)
        finally:timer.cancel();timer.join()
        elapsed=time.monotonic()-started;statistics=solver.accum_stats()
        witness=None
        if result is True:
            model=set(solver.get_model());ids=[p for p in range(V) if p+1 in model]
            s=sum(1<<p for p in ids);assert len(ids)<=9 and all(s&q!=q for q in quads)
            assert all(any((q&~(1<<p))&s==q&~(1<<p) for q in quads if q>>p&1) for p in range(V) if p not in ids)
            witness=ids
    files=['scripts/round59_n10_nine_sat.py','scripts/round25_forced_verify.py','../../scripts/analysis/fact_kmin_cover_bound.cpp']
    out={'n':10,'stone_count_bound':9,'status':'UNSAT_UNCHECKED' if result is False else 'SAT' if result is True else 'UNKNOWN',
         'solver':'Glucose4','python_sat_version':pysat.__version__,'wall_seconds':elapsed,
         'variables':card.nv,'clauses':len(clauses),'quad_count':len(quads),
         'triple_completion_incidence':217764,'max_completion':9,'witness_ids':witness,
         'solver_statistics':statistics,'formula_sha256':hashlib.sha256(formula.read_bytes()).hexdigest(),
         'proof_kind':'SAT witnesses independently verified; UNSAT and UNKNOWN are not absence certificates',
         'solver_extension_sha256':hashlib.sha256(Path(pysolvers.__file__).read_bytes()).hexdigest(),
         'sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}}
    (ROOT/'round59_n10_atmost9.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(out['status'],witness,'seconds',elapsed,flush=True)


if __name__=='__main__':main()
