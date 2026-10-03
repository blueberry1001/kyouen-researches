#!/usr/bin/env python3
"""Exact small-board checks of the odd-q fixed-point-free reflection theorem."""
from __future__ import annotations
from functools import lru_cache
from itertools import combinations
import json
from pathlib import Path

from q48_exact_threshold import through_three


def curves(points: list[tuple[int,int]], q: int) -> list[int]:
    keys={through_three(*triple) for triple in combinations(points,3)}
    result=[]
    for a,b,c,d in keys:
        mask=sum(1<<i for i,(x,y) in enumerate(points) if a*(x*x+y*y)+b*x+c*y+d==0)
        if mask.bit_count()>=q:result.append(mask)
    return result


def board_check(name: str, points: list[tuple[int,int]], mates: list[int], q: int, exact_grundy: bool) -> dict:
    assert q%2==1
    n=len(points)
    assert all(mates[i]!=i and mates[mates[i]]==i for i in range(n))
    pairs=[(i,mates[i]) for i in range(n) if i<mates[i]]
    cm=curves(points,q)
    full=(1<<n)-1
    def safe(s: int) -> bool:return all((s&c).bit_count()<q for c in cm)
    @lru_cache(None)
    def grundy(s: int) -> int:
        seen=set()
        for i in range(n):
            if not s>>i&1 and safe(s|(1<<i)):seen.add(grundy(s|(1<<i)))
        g=0
        while g in seen:g+=1
        return g
    if exact_grundy:assert grundy(0)==0
    symmetric_safe=responses=0
    for chosen in range(1<<len(pairs)):
        s=sum((1<<a)|(1<<b) for j,(a,b) in enumerate(pairs) if chosen>>j&1)
        if not safe(s):continue
        symmetric_safe+=1
        if exact_grundy:assert grundy(s)==0
        for i in range(n):
            if s>>i&1 or not safe(s|(1<<i)):continue
            assert not s>>mates[i]&1
            assert safe(s|(1<<i)|(1<<mates[i]))
            responses+=1
    return {'board':name,'q':q,'points':n,'forbidden_curves':len(cm),
            'symmetric_safe_positions':symmetric_safe,'legal_reflection_responses':responses,
            'exact_grundy_checked':exact_grundy,'g_empty':0 if exact_grundy else None,
            'safe_states_in_grundy_search':grundy.cache_info().currsize if exact_grundy else None}


def failures_outside_scope() -> list[dict]:
    circle=[(1,0),(2,0),(0,1),(3,1),(0,2),(3,2),(1,3),(2,3)]
    pairs_removed={(1,0),(1,3)}
    before=[p for p in circle if p not in pairs_removed]
    assert len(before)==6
    # A single 8-point circle: 6 -> 7 is safe, 7 -> 8 is not.
    even={'case':'even q does not admit the theorem','q':8,
          'symmetric_position':before,'first_move':[1,0],'mirror_reply':[1,3],
          'first_move_safe':True,'reply_safe':False}
    points=[(12,7),(13,12),(12,17),(-12,-7),(-13,-12),(-12,-17),(5,0),(-5,0)]
    cm=curves(points,5)
    safe=lambda s:all((s&c).bit_count()<5 for c in cm)
    assert safe((1<<6)-1) and safe((1<<7)-1) and not safe((1<<8)-1)
    rotation={'case':'central inversion is insufficient even for odd q','q':5,
              'centrally_symmetric_position':points[:6],'first_move':points[6],
              'rotated_reply':points[7],'first_move_safe':True,'reply_safe':False,
              'new_forbidden_circle_coefficients':[1,0,-24,-25]}
    return [even,rotation]


def main() -> None:
    records=[]
    for w,m in [(2,4),(2,5),(3,4),(4,4),(4,5)]:
        points=[(x,y) for y in range(w) for x in range(m)]
        # Reflect across a half-integer axis perpendicular to an even side.
        if w%2==0:mates=[(w-1-y)*m+x for x,y in points]
        else:mates=[y*m+(m-1-x) for x,y in points]
        for q in (5,7,9):
            records.append(board_check(f'{w}x{m}',points,mates,q,exact_grundy=(w*m<=16)))
    points=[(1,0),(2,0),(0,1),(3,1),(0,2),(3,2),(1,3),(2,3),(-1,0),(-1,3),(4,1),(4,2)]
    mates=[points.index((x,3-y)) for x,y in points]
    records.append(board_check('irregular reflection-invariant board',points,mates,5,True))
    result={'theorem':'For odd q, every safe reflection-invariant position on a finite reflection-invariant board with no fixed point is a P position.',
            'checks':records,'outside_scope_counterexamples':failures_outside_scope()}
    destination=Path(__file__).resolve().parents[1]/'q48_odd_q_reflection.json'
    destination.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
