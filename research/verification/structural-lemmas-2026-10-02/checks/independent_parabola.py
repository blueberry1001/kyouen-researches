"""Verify all published parabola witnesses with an independent determinant.

Only witness coordinates are read; SAT clauses and search results are not trusted.
"""
import argparse
from itertools import combinations
from pathlib import Path
import json
from independent_geometry import circle_det, is_prime

parser = argparse.ArgumentParser()
parser.add_argument('data', nargs='?', type=Path,
                    default=Path(__file__).with_name('parabola_half_bound.json'))
args = parser.parse_args()
records = json.loads(args.data.read_text(encoding='utf-8'))
expected = [p for p in range(5, 128) if is_prime(p)]
assert [r['p'] for r in records] == expected
counts = []
for row in records:
    p = row['p']
    ts = row['parameters']
    coords = [tuple(x) for x in row['coordinates']]
    assert len(ts) == len(set(ts)) == (p+3)//2
    assert all(0 <= t < p for t in ts)
    assert coords == [(t, t*t % p) for t in ts]
    count = 0
    for q in combinations(coords, 4):
        assert circle_det(q) != 0, (p, q)
        count += 1
    counts.append({'p': p, 'size': len(ts), 'quadruples': count})

p = 23
bad = [(t, t*t % p) for t in [0,4,9,10]]
assert circle_det(bad) == 0
repaired = [t for t in range(13) if t != 4] + [19]
assert all(circle_det([(t,t*t%p) for t in q]) != 0
           for q in combinations(repaired,4))
out = {'method': 'Bareiss determinant on all witness quadruples, independent of SAT',
       'prime_count': len(counts), 'checks': sum(r['quadruples'] for r in counts),
       'witnesses': counts, 'p23_counterexample': bad,
       'p23_repaired_parameters': repaired}
Path(__file__).with_suffix('.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
print(json.dumps({k:v for k,v in out.items() if k!='witnesses'}))
