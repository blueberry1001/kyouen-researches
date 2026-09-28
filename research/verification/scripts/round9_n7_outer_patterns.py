"""B382: complete first-external-layer templates for all sixteen n7 maxima."""
from pathlib import Path
from itertools import combinations
from collections import Counter
import struct
import json

from round9_geometry import curve,evaluate
from kyouen_core import is_forbidden_quad


def transform(p,rotation,reflection):
    x,y=p
    if reflection:x=6-x
    for _ in range(rotation):x,y=6-y,x
    return x,y


def main():
    root=Path(__file__).resolve().parents[3]
    masks=struct.unpack('<16Q',(root/'night-research/maxsafe_n7_K14.bin').read_bytes())
    configurations=[frozenset((i%7,i//7) for i in range(49) if m>>i&1) for m in masks]
    templates={'A':(configurations[0],{(7,8)}),'B':(configurations[1],{(8,-2),(8,6)})}
    records=[]
    for index,stones in enumerate(configurations):
        phase='A' if (3,3) in stones else 'B'
        base,outer=templates[phase]
        transforms=[(rotation,reflection) for rotation in range(4) for reflection in range(2)
                    if frozenset(transform(p,rotation,reflection) for p in base)==stones]
        assert len(transforms)==1
        rotation,reflection=transforms[0]
        expected={transform(p,rotation,reflection) for p in outer}
        cc=[curve(t) for t in combinations(stones,3)]
        layers=[]
        for radius in (1,2):
            frame=[(x,y) for x in range(-radius,7+radius) for y in range(-radius,7+radius)
                         if max(0,-x,x-6,-y,y-6)==radius]
            legal=[]
            for p in frame:
                actual=all(evaluate(c,p) for c in cc)
                independent=not any(is_forbidden_quad([*t,p]) for t in combinations(stones,3))
                assert actual==independent
                if actual:legal.append(p)
            layers.append({'radius':radius,'points_checked':len(frame),'legal':legal})
        assert not layers[0]['legal'] and set(layers[1]['legal'])==expected
        records.append({'index':index,'phase':phase,'mask':masks[index],
                        'rotation':rotation,'reflection':reflection,'layers':layers})
    orbit_counts=Counter()
    for row in records:
        for x,y in row['layers'][1]['legal']:
            orbit_counts[tuple(sorted((abs(x-3),abs(y-3))))]+=1
    result={'B382':'SUPPORTED','B381_reconfirmed':True,'complete':True,
            'number_of_maxima':16,'templates':{p:{'stones':sorted(s),'first_legal_outer_points':sorted(o)}
                                                for p,(s,o) in templates.items()},
            'point_orbit_counts':{str(k):v for k,v in sorted(orbit_counts.items())},
            'total_external_point_tests':sum(z['points_checked'] for r in records for z in r['layers']),
            'records':records}
    target=root/'research/verification/round9_n7_outer_patterns.json'
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print({k:v for k,v in result.items() if k not in ('records','templates')})
    print(target)


if __name__=='__main__':main()
