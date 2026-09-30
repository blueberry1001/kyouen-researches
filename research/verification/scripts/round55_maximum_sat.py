"""Exact cardinality SAT for large safe sets; every SAT witness rechecked.

UNSAT is recorded as a solver claim until its saved DRAT proof is checked.
Do not infer maximality, a maximum, or absence from an interrupted run.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
from itertools import combinations
from round25_forced_verify import bits, curve, det4, geometry

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--n', type=int, default=9)
    parser.add_argument('--atleast', type=int, default=18)
    parser.add_argument('--seconds', type=int, default=300)
    args = parser.parse_args()
    sys.path.insert(0, str(Path(tempfile.gettempdir())/'kyouen-round46-pysat'))
    import pysat
    from pysat.card import CardEnc, EncType
    from pysat.solvers import Glucose4
    points, quads, curves = geometry(args.n)
    V = args.n*args.n
    assert 0 <= args.atleast <= V
    clauses = [[-(p+1) for p in bits(q)] for q in quads]
    card = CardEnc.atleast(lits=list(range(1, V+1)), bound=args.atleast,
                          top_id=V, encoding=EncType.seqcounter)
    clauses.extend(card.clauses)
    work = Path(tempfile.gettempdir())/'kyouen-round55-capacity'
    work.mkdir(exist_ok=True)
    prefix = f'n{args.n}_atleast{args.atleast}'
    cnf = work/(prefix+'.cnf')
    with cnf.open('w', encoding='ascii', newline='\n') as f:
        f.write(f'p cnf {card.nv} {len(clauses)}\n')
        for clause in clauses:
            f.write(' '.join(map(str, clause))+' 0\n')
    print('Glucose4 safe-set capacity', args.n, args.atleast, 'clauses', len(clauses), 'variables', card.nv, flush=True)
    proof_lines = None
    witness = None
    with Glucose4(bootstrap_with=clauses, with_proof=True) as solver:
        timer = threading.Timer(args.seconds, solver.interrupt)
        timer.start()
        started = time.monotonic()
        try:
            result = solver.solve_limited(expect_interrupt=True)
        finally:
            timer.cancel()
            timer.join()
        elapsed = time.monotonic()-started
        statistics = solver.accum_stats()
        if result is True:
            model = set(solver.get_model())
            ids = [p for p in range(V) if p+1 in model]
            assert len(ids) >= args.atleast
            s = sum(1 << p for p in ids)
            assert all(s&q != q for q in quads)
            assert all((s & c).bit_count() <= 3 for c in curves)
            chosen = [points[p] for p in ids]
            for four in combinations(chosen, 4):
                assert det4(four) != 0
                assert all(curve(four[:3]) != curve([four[0], four[1], four[3]]) for _ in [0])
            witness = {'ids': ids, 'coordinates': chosen, 'k': len(ids),
                       'all_four_point_subsets_checked': len(list(combinations(ids, 4)))}
        elif result is False:
            proof_lines = solver.get_proof()
    proof = None
    if proof_lines is not None:
        path = work/(prefix+'.drat')
        path.write_text('\n'.join(proof_lines)+'\n', encoding='ascii')
        proof = {'path': str(path), 'clauses': len(proof_lines), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                 'independently_checked': False}
    files = ['scripts/round55_maximum_sat.py', 'scripts/round25_forced_verify.py']
    out = {'n': args.n, 'minimum_stone_count': args.atleast,
           'status': 'SAT' if result is True else 'UNSAT_UNCHECKED' if result is False else 'UNKNOWN',
           'solver': 'Glucose4', 'python_sat_version': pysat.__version__, 'wall_seconds': elapsed,
           'variables': card.nv, 'clauses': len(clauses), 'quad_count': len(quads),
           'formula_path': str(cnf), 'formula_sha256': hashlib.sha256(cnf.read_bytes()).hexdigest(),
           'solver_statistics': statistics, 'safe_set_witness': witness, 'drat_proof': proof,
           'sha256': {f: hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}}
    (ROOT/f'round55_{prefix}.json').write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(out['status'], 'witness', witness, 'seconds', elapsed, flush=True)


if __name__ == '__main__':
    main()
