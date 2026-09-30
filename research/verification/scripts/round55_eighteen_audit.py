"""Audit the eighteen-stone construction transcribed from Monaka's image.

The construction is credited to its published source. This certificate
proves K9 >= 18 and refutes B081; it does not prove a matching upper bound.
"""
from itertools import combinations
from collections import Counter
from pathlib import Path
import hashlib
import json
from round25_forced_verify import curve, det4, geometry, bits

ROOT = Path(__file__).resolve().parents[1]
COORDINATES = [(5,0),(6,0),(8,0),(0,1),(2,1),(0,2),(6,2),(4,3),(8,4),
               (2,5),(5,5),(7,5),(0,6),(1,6),(7,7),(1,8),(3,8),(7,8)]


def main():
    points, quads, curves = geometry(9)
    ids = sorted(x+9*y for x,y in COORDINATES)
    assert len(ids) == len(set(ids)) == 18 and all(0 <= p < 81 for p in ids)
    mask = sum(1 << p for p in ids)
    determinants = [det4(q) for q in combinations(COORDINATES,4)]
    assert len(determinants) == 3060 and all(determinants)
    assert all(mask&q != q for q in quads)
    assert all((mask&c).bit_count() <= 3 for c in curves)
    # Independently recover each triple's integer circle/line, then scan all
    # 81 points. A fourth occupied point would contradict safety.
    blocking = {}
    for triple in combinations(COORDINATES,3):
        a,b,c,d = curve(triple)
        on = [p for p,(x,y) in enumerate(points) if a*(x*x+y*y)+b*x+c*y+d == 0]
        assert sum(p in ids for p in on) == 3
        for p in on:
            if p not in ids:
                blocking.setdefault(p,[]).append(list(triple))
    legal = [p for p in range(81) if p not in ids and p not in blocking]
    assert not legal
    images = set()
    for reflected in (False,True):
        for rotations in range(4):
            image = []
            for x,y in COORDINATES:
                if reflected:
                    x = 8-x
                for _ in range(rotations):
                    x,y = 8-y,x
                image.append(x+9*y)
            images.add(tuple(sorted(image)))
    assert len(images) == 8
    files = ['scripts/round55_eighteen_audit.py','scripts/round25_forced_verify.py',
             'scripts/round55_maximum_sat.py','round55_n9_atleast18.json']
    unknown = json.loads((ROOT/files[-1]).read_text())
    assert unknown['status'] == 'UNKNOWN' and unknown['safe_set_witness'] is None
    result = {'B081_original_verdict':'REFUTED','proved_lower_bound_K9':18,
              'matching_upper_bound_independently_proved':False,
              'source':{'author':'モナカ','date':'2026-08-20',
                        'article':'https://note.com/monaka0707/n/n06891c936d02',
                        'image':'https://assets.st-note.com/img/1787159703-v78LSNbwuBqZHXIG6DRhjsoc.png?width=1200',
                        'coordinate_convention':'x left-to-right, y top-to-bottom; both zero-based'},
              'ids':ids,'coordinates':COORDINATES,'mask':mask,
              'quadruples_checked':3060,'forbidden_quadruples':0,
              'board_forbidden_quadruples':len(quads),'board_curves':len(curves),
              'maximal':True,'legal_points':legal,'d4_orbit_size':len(images),
              'empty_point_triple_cover_histogram':dict(sorted(Counter(map(len,blocking.values())).items())),
              'first_blocking_triple_by_empty_point':{str(p):t[0] for p,t in sorted(blocking.items())},
              'separate_sat_attempt_status':'UNKNOWN',
              'sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}}
    (ROOT/'round55_eighteen_verified.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS eighteen safe stones, all 3060 quadruples; B081 refuted, upper bound not claimed')


if __name__ == '__main__':
    main()
