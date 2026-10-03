#!/usr/bin/env python3
"""Verify an infinite Pell family of four-row eight-point lattice circles."""
from __future__ import annotations

from itertools import combinations
import json
from pathlib import Path

from q48_exact_threshold import chord_patterns


def det4(points: tuple[tuple[int, int], ...]) -> int:
    (x0, y0), *rest = points
    rows = [( (x-x0)**2 + (y-y0)**2, x-x0, y-y0) for x,y in rest]
    (a,b,c),(d,e,f),(g,h,i) = rows
    return a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g)


def main() -> None:
    u, v = 1, 0
    records = []
    for n in range(1, 11):
        u, v = 19*u + 60*v, 6*u + 19*v
        assert u*u - 10*v*v == 1
        differences = [9*v-u, 3*u-v, 3*u+v, u+9*v]
        pairs = [(u,9*v), (5*v-u,2*u+4*v),
                 (4*v-u,2*u+5*v), (0,u+9*v)]
        points = [(x,y) for y,pair in enumerate(pairs) for x in pair]
        coefficients = (1,-(u+9*v),-3*(u*v+1),9*u*v)
        a,b,c,d = coefficients
        assert all(0 <= left < right <= u+9*v for left,right in pairs)
        assert [right-left for left,right in pairs] == differences
        assert all(a*(x*x+y*y)+b*x+c*y+d==0 for x,y in points)
        assert all(det4(q)==0 for q in combinations(points,4))
        xs = sorted(x for x,y in points)
        min_7_span = min(xs[-1]-xs[1], xs[-2]-xs[0])
        records.append({'n':n, 'u':u, 'v':v, 'chord_differences':differences,
                        'row_pairs':pairs, 'circle_coefficients':coefficients,
                        'minimum_length_for_8_points':u+9*v+1,
                        'minimum_length_for_7_points':min_7_span+1})
    assert chord_patterns(72) == [(1,3,3,1)]
    assert chord_patterns(117) == [(1,3,3,1),(35,51,63,73),(73,63,51,35)]
    assert records[0]['minimum_length_for_8_points']==74
    assert records[0]['minimum_length_for_7_points']==69
    result = {'claim':'Pell family, not a classification of all four-row circles',
              'pell_equation':'u^2 - 10 v^2 = 1',
              'recurrence':['u_next = 19*u + 60*v','v_next = 6*u + 19*v'],
              'first_nonlocal_8_point_length':74,
              'first_nonlocal_7_point_length':69,
              'verified_instances':records, 'four_point_minors_per_instance':70}
    destination=Path(__file__).resolve().parents[1]/'q48_pell_family.json'
    destination.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
