"""Exact standalone audits for the 2026-10-03 extension/local-optimum note.

Default: only Python's standard library, explicit safety/blocker certificates,
and a consistency audit of completed C++ search records. --rerun-exact also
compiles the two local enumerators with g++ and repeats all three searches.
The latter is required to reproduce the computational nonexistence claims;
merely reading their result flags is not an independent absence proof.
"""
from itertools import combinations, permutations
from math import comb, gcd
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
T = [0,7,8,14,16,20,21,31,35,42,47,67,69,70,73,82,89,93,99]
U = [2,6,16,18,21,25,32,35,40,59,62,67,74,77,78,80,81,83,97,99]
Q = [25,59,62,83]
S21 = [2,6,17,19,23,27,35,38,44,68,73,81,84,85,88,89,91,106,108,110,120]


def det(points):
    rows = [(x*x+y*y,x,y,1) for x,y in points]
    result = 0
    for p in permutations(range(4)):
        term = (-1)**sum(p[i] > p[j] for i in range(4) for j in range(i+1,4))
        for i,j in enumerate(p):
            term *= rows[i][j]
        result += term
    return result


def curve(points):
    (x,y),(u,v),(r,s) = points
    u -= x; v -= y; r -= x; s -= y
    a = u*s-v*r
    if a:
        fx = (u*u+v*v)*s-(r*r+s*s)*v
        fy = u*(r*r+s*s)-r*(u*u+v*v)
        c = [a,-2*a*x-fx,-2*a*y-fy,a*(x*x+y*y)+fx*x+fy*y]
    else:
        c = [0,-v,u,v*x-u*y]
    c = [z//gcd(*c) for z in c]
    if next(z for z in c if z) < 0:
        c = [-z for z in c]
    return tuple(c)


def contains(c, p):
    a,b,c_,d = c
    x,y = p
    return a*(x*x+y*y)+b*x+c_*y+d == 0


def completion_audit(points, domain):
    """Every blocked point gets one exact triple/circle-or-line certificate."""
    occupied = set(points)
    triples = list(combinations(points,3))
    curves = [curve(t) for t in triples]
    assert len(set(curves)) == len(curves)
    certificates, legal = [], []
    for p in sorted(set(domain)-occupied):
        i = next((i for i,c in enumerate(curves) if contains(c,p)), None)
        if i is None:
            legal.append(p)
        else:
            assert det([*triples[i],p]) == 0
            certificates.append({'point':p,'triple':triples[i],'curve':curves[i]})
    return {'legal_additions':legal,'blocked_points':len(certificates),
            'blocking_certificates':certificates}


def board(n):
    return [(x,y) for y in range(n) for x in range(n)]


def coords(n, ids):
    return [(p % n,p//n) for p in ids]


def audit(n, points):
    assert len(set(points)) == len(points) and set(points) <= set(board(n))
    determinants = [det(q) for q in combinations(points,4)]
    assert all(determinants)
    coverage = completion_audit(points,board(n))
    assert coverage['legal_additions'] == []
    return {'n':n,'k':len(points),'ids':sorted(x+n*y for x,y in points),
            'coordinates':sorted(points),'safe_quadruples_checked':len(determinants),
            'minimum_absolute_determinant':min(map(abs,determinants)),**coverage}


def exact_records(rerun):
    records = json.loads((HERE/'saturation_20261003_extra_exact_results.json').read_text())
    for key,seed,nodes in [('T_neighborhood',T,364429603),
                           ('U_minus_25_neighborhood',[p for p in U if p != 25],426848807)]:
        r = records[key]
        assert r['n'] == 10 and r['target'] == 20 and r['seed_ids'] == seed
        assert r['found'] is False and r['local_complete'] is True
        assert r['complete_deletion_radius'] == 9 and r['witness_ids'] == []
        assert r['subsets_examined'] == sum(comb(19,r) for r in range(1,10)) == 262143
        assert r['extension_nodes'] == nodes
    r = records['U_intersection_layer']
    assert r['n'] == 10 and r['target'] == 20 and r['universe_ids'] == U
    assert r['found'] is False and r['complete'] is True and r['witness_ids'] == []
    assert r['required_point'] == 25 and r['intersection_layer'] == 10
    assert r['unsafe_subsets_skipped'] == comb(16,6) == 8008
    assert r['subsets_examined'] == comb(19,9)-comb(16,6) == 84370
    assert r['extension_nodes'] == 50552292
    if rerun:
        with tempfile.TemporaryDirectory(prefix='saturation-extra-') as d:
            binaries = {}
            for kind in ['nineteen','union']:
                source = HERE/f'saturation_20261003_extra_{kind}_neighborhood.cpp'
                binary = str(Path(d)/kind)
                subprocess.run(['g++','-O3','-std=c++17',str(source),'-o',binary],check=True)
                binaries[kind] = binary
            jobs = [('T_neighborhood',[binaries['nineteen'],'0']),
                    ('U_minus_25_neighborhood',[binaries['nineteen'],'0',
                       ','.join(map(str,[p for p in U if p != 25]))]),
                    ('U_intersection_layer',[binaries['union'],'0'])]
            for key,command in jobs:
                print('Repeating exact search:',key,flush=True)
                actual = json.loads(subprocess.check_output(command,text=True))
                expected = records[key]
                assert {k:v for k,v in actual.items() if k != 'seconds'} == {
                    k:v for k,v in expected.items() if k != 'seconds'}
    return {'records':records,'absence_trust_boundary':
            'C++ exhaustive search; Python default audits consistency only',
            'full_exact_search_replay_option':'--rerun-exact'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rerun-exact',action='store_true')
    args = parser.parse_args()
    bad = [list(q) for q in combinations(U,4) if det(coords(10,q)) == 0]
    assert bad == [Q]
    assert curve(coords(10,Q[:3])) == (1,-11,-11,48)
    # The four 19-subsets are witnesses attaining the restricted optimum.
    family = [audit(10,coords(10,[p for p in U if p != q])) for q in Q]
    t = audit(10,coords(10,T))
    f = coords(10,[p for p in U if p != 59])
    extension11 = completion_audit(f,board(11))
    assert extension11['legal_additions'] == [(0,10),(10,10)]
    p21 = coords(11,S21)
    assert set(p21) == set(f) | {(0,10),(10,10)}
    a21 = audit(11,p21)
    translated21 = [(x+1,y) for x,y in p21]
    extension12 = completion_audit(translated21,board(12))
    assert extension12['legal_additions'] == [(0,11)]
    p22 = translated21+[(0,11)]
    a22 = audit(12,p22)
    # Two complete exterior shells, not merely the four bounding sides.
    shell1 = [(x,y) for x in range(-1,13) for y in range(-1,13)
              if not (0 <= x < 12 and 0 <= y < 12)]
    shell2 = [(x,y) for x in range(-2,14) for y in range(-2,14)
              if not (-1 <= x < 13 and -1 <= y < 13)]
    exterior1 = completion_audit(p22,shell1)
    exterior2 = completion_audit(p22,shell2)
    assert len(shell1) == 52 and exterior1['legal_additions'] == []
    assert len(shell2) == 60 and exterior2['legal_additions'] == [(-2,13),(12,-2)]
    a24 = audit(16,[(x+2,y+2) for x,y in p22+[(-2,13),(12,-2)]])
    results = {'definitions':{'board':'{0,...,n-1}^2','point_id':'x+n*y',
                  'safe':'all four-point circle/line determinants nonzero'},
               'almost_safe_U':{'ids':U,'unique_bad_quadruple':Q,'curve':[1,-11,-11,48]},
               'nineteen_point_witnesses':{'T':t,'K4_family':family},
               'n11_k21':a21,'n12_k22':a22,'n16_k24':a24,
               'F_to_n11':extension11,'translated_n11_to_n12':extension12,
               'exterior_shell_1':exterior1,'exterior_shell_2':exterior2,
               'local_optimum_search':exact_records(args.rerun_exact)}
    sources = [Path(__file__),HERE/'saturation_20261003_extra_nineteen_neighborhood.cpp',
               HERE/'saturation_20261003_extra_union_neighborhood.cpp',
               HERE/'saturation_20261003_extra_exact_results.json']
    results['source_sha256'] = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    target = HERE/'saturation_20261003_extra_verified.json'
    target.write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
    print('Verified explicit maximal sets of sizes 21, 22 and 24 on boards 11, 12 and 16.')
    print('Verified all exterior-shell certificates and local-search record consistency.')
    if args.rerun_exact:
        print('All three complete C++ searches were repeated with matching node counts.')
    print('Wrote',target)


if __name__ == '__main__':
    main()
