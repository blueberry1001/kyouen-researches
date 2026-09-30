"""Second SAT engine for round46's generated, identical DIMACS formula."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=int,default=600)
    parser.add_argument('--pysat-path',default=str(Path(tempfile.gettempdir())/'kyouen-round46-pysat'))
    args=parser.parse_args();sys.path.insert(0,args.pysat_path)
    import pysat
    from pysat.formula import CNF
    from pysat.solvers import Cadical195
    path=Path(tempfile.gettempdir())/'kyouen-round46-sat'/'n9_atmost8.cnf'
    formula=CNF(from_file=str(path));assert len(formula.clauses)==166810 and formula.nv==46113
    started=time.monotonic();chunks=0;result=None;witness=None
    with Cadical195(bootstrap_with=formula.clauses) as solver:
        while time.monotonic()-started<args.seconds and result is None:
            solver.conf_budget(50000);result=solver.solve_limited();chunks+=1
            print('CaDiCaL chunk',chunks,'seconds',round(time.monotonic()-started,2),'status',result,flush=True)
        statistics=solver.accum_stats()
        if result is True:
            model=set(solver.get_model());witness=[p for p in range(81) if p+1 in model]
    out={'n':9,'stone_count_bound':8,'status':'UNSAT' if result is False else 'SAT' if result is True else 'UNKNOWN',
         'solver':'CaDiCaL195','python_sat_version':pysat.__version__,
         'wall_seconds':time.monotonic()-started,'conflict_budget_per_chunk':50000,'chunks':chunks,
         'witness_ids':witness,'solver_statistics':statistics,
         'formula_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
         'proof_kind':'independent SAT engine; no DRAT proof checked',
         'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (ROOT/'round46_cadical_atmost8.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(out['status'],witness,flush=True)


if __name__=='__main__':main()
