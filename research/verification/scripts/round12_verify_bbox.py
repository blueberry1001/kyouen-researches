"""Independent small-board triple census and direct B454 witness verification.

The width-161 exclusion is the C++ exhaustive computation, not this small check.
This script tests that implementation against an independently generated census
on all boards of side 2..7 and verifies every published minimum witness using
Python's arbitrary-precision arithmetic and math.isqrt.
"""
from collections import Counter
from itertools import combinations
from math import gcd, isqrt
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'research/verification'


def q_of(a, d, e):
    return 2*a // gcd(2*a, gcd(d, e))


def family(q):
    return 'power2' if q & (q-1) == 0 else 'odd' if q%2 else None


def points_on(a, d, e, f):
    discr = d*d + e*e + 4*a*f
    r = isqrt(discr)
    points = set()
    for x in range(-(-(d-r)//(2*a)), (d+r)//(2*a)+1):
        rem = discr-(2*a*x-d)**2
        h = isqrt(rem)
        if h*h != rem:
            continue
        for num in {e-h, e+h}:
            if num % (2*a) == 0:
                points.add((x, num//(2*a)))
    return sorted(points)


def span(points):
    return max(max(p[j] for p in points)-min(p[j] for p in points) for j in (0,1))


def triple_circle(p, q, r):
    x, y = p
    u, v = q[0]-x, q[1]-y
    s, t = r[0]-x, r[1]-y
    a = u*t-v*s
    if not a:
        return None
    d = (u*u+v*v)*t-(s*s+t*t)*v+2*a*x
    e = u*(s*s+t*t)-s*(u*u+v*v)+2*a*y
    f = a*(x*x+y*y)-d*x-e*y
    if a < 0:
        a, d, e, f = -a, -d, -e, -f
    g = gcd(gcd(a,d),gcd(e,f))
    return a//g,d//g,e//g,f//g


def independent_small(w):
    grid = [(x,y) for x in range(w+1) for y in range(w+1)]
    triples = Counter(triple_circle(*t) for t in combinations(grid,3))
    canonical = {}
    for key, count in triples.items():
        if key is None or count < 4:
            continue
        a,d,e,f = key
        fam = family(q_of(a,d,e))
        if fam is None:
            continue
        ps = points_on(*key)
        if len(ps) < 4 or span(ps) > w:
            continue
        x,y = min(ps)
        anchored = a,d-2*a*x,e-2*a*y
        canonical[anchored] = fam,len(ps),span(ps)
    counts = Counter((fam,m) for fam,m,s in canonical.values())
    minima = {}
    for fam,m,s in canonical.values():
        minima[fam,m] = min(minima.get((fam,m),s),s)
    return counts,minima


def direct_norm_witness(row):
    norm, q = row['M'],row['q']
    rx,ry = row['residue']
    assert gcd(gcd(rx,ry),q) == 1
    ps = []
    for u in range(-isqrt(norm),isqrt(norm)+1):
        if (u-rx)%q:
            continue
        v = isqrt(norm-u*u)
        if v*v != norm-u*u:
            continue
        for z in sorted({v,-v}):
            if (z-ry)%q == 0:
                ps.append(((u-rx)//q,(z-ry)//q))
    assert sorted(ps) == sorted(map(tuple,row['points']))
    assert len(ps) == row['m'] and span(ps) == row['span']
    return {'family':row['family'],'m':len(ps),'span':span(ps),'q':q,'M':norm,
            'residue':[rx,ry],'complete_points':sorted(ps)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--executable',type=Path,default=ROOT/'scratchpad/round12_circle_bbox.exe')
    args = ap.parse_args()
    checks = []
    for w in range(1,7):
        cpp = json.loads(subprocess.check_output([str(args.executable),str(w)],text=True))
        counts,minima = independent_small(w)
        cpp_counts = {(r['family'],r['m']):r['complete_anchored_count'] for r in cpp['minima']}
        cpp_min = {(r['family'],r['m']):r['span'] for r in cpp['minima']}
        assert dict(counts) == cpp_counts, (w,counts,cpp_counts)
        assert minima == cpp_min
        # Exercise the optimized determinant filter separately.
        filtered = json.loads(subprocess.check_output([str(args.executable),str(w),'power2'],text=True))
        assert filtered['minima'] == [r for r in cpp['minima'] if r['family']=='power2']
        checks.append({'span':w,'board_side':w+1,'anchored_circles':sum(counts.values()),'match':True})
        print('small board',w+1,'matched',sum(counts.values()),flush=True)
    files = ['round12_circle_bbox_w32.json','round12_circle_bbox_w64.json',
             'round12_circle_bbox_w161_power2.json']
    records_checked = 0
    datasets = {}
    for name in files:
        d = json.loads((OUT/name).read_text(encoding='utf-8-sig'))
        datasets[name] = d
        for row in d['minima']:
            a,b,c = row['circle_A_D_E']
            ps = points_on(a,b,c,0)
            assert ps == sorted(map(tuple,row['points']))
            assert len(ps) == row['m'] and span(ps) == row['span']
            assert q_of(a,b,c) == row['q']
            assert gcd(gcd(a,b),c) == 1
            records_checked += 1
    large = datasets[files[-1]]
    assert large['selection'] == 'power2' and large['coordinate_span_limit'] == 161
    assert not any(r['m']==11 for r in large['minima'])
    candidates = json.loads((OUT/'round12_circle_candidates.json').read_text())['minima']
    witness_rows = [r for r in candidates if r['m']==11 or (r['family']=='odd' and r['m']==7)]
    witnesses = [direct_norm_witness(r) for r in witness_rows]
    odd11 = next(r for r in witnesses if r['family']=='odd' and r['m']==11)
    shifted = sorted((x+81,y+79) for x,y in odd11['complete_points'])
    assert all((11*x-881)**2+(11*y-865)**2==801125 for x,y in shifted)
    assert min(x for x,y in shifted)==0 and max(x for x,y in shifted)==161
    assert min(y for x,y in shifted)==0 and max(y for x,y in shifted)==160
    small = {(r['family'],r['m']):r['span'] for r in datasets[files[1]]['minima']}
    assert ('odd',7) not in small
    small['odd',7] = next(r['span'] for r in witnesses if r['family']=='odd' and r['m']==7)
    comparisons = []
    for m in range(4,11):
        a,b = small['power2',m],small['odd',m]
        assert a <= b
        comparisons.append({'m':m,'power2_min_span':a,'odd_min_span':b})
    hashes = {name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in files}
    hashes['scripts/round12_circle_bbox.cpp'] = hashlib.sha256((OUT/'scripts/round12_circle_bbox.cpp').read_bytes()).hexdigest()
    result = dict(small_board_independent_checks=checks,minimum_witnesses_checked=records_checked,
                  exact_norm_witnesses=witnesses,odd11_points_on_162_board=shifted,
                  point_counts_4_through_10=comparisons,input_sha256=hashes,
                  B454='REFUTED by exact finite enumeration plus explicit complete-circle witness',
                  power2_m11_min_span_lower_bound=162,odd_m11_min_span_upper_bound=161,
                  power2_m11_min_span_upper_bound=366,
                  limitations='The full width-161 exclusion is supplied by the C++ census; its whole run is not duplicated by the Python small-board comparison.')
    (OUT/'round12_circle_bbox_verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('verified records',records_checked,'B454 finite counterexample verified')


if __name__ == '__main__':
    main()
