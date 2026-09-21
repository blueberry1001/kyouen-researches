"""Search the full board at floor 12, optionally forbidding the catalyst corner."""
from collections import deque
from itertools import combinations
import argparse
import json
import time
from cycle8_lib import forbidden_quads, RES
from discover_static_barrier import instance


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--forbid', type=int, default=48)
    parser.add_argument('--max-states', type=int, default=500000)
    parser.add_argument('--exhaust', action='store_true')
    args = parser.parse_args()
    cells,a,b,_ = instance()
    a = sum(1 << p for i,p in enumerate(cells) if a >> i & 1)
    b = sum(1 << p for i,p in enumerate(cells) if b >> i & 1)
    triples = {}
    for q in forbidden_quads(7):
        qm = sum(1 << p for p in q)
        for p in q:
            key = qm ^ (1 << p)
            triples[key] = triples.get(key,0) | (1 << p)
    allowed = (1 << 49)-1
    if args.forbid >= 0:
        allowed ^= 1 << args.forbid
    previous = {a:None}
    todo = deque([a])
    t0 = time.monotonic()
    found = False
    capped = False
    processed = 0
    while todo:
        m = todo.popleft()
        processed += 1
        if m == b:
            found = True
            if not args.exhaust:
                break
        bits = [1 << p for p in range(49) if m >> p & 1]
        blocked = 0
        for x,y,z in combinations(bits,3):
            blocked |= triples.get(x|y|z,0)
        neighbors = []
        if len(bits)>12:
            neighbors.extend(m ^ bit for bit in bits)
        available = allowed & ~m & ~blocked
        while available:
            bit = available & -available
            available ^= bit
            neighbors.append(m | bit)
        for other in neighbors:
            if other not in previous:
                previous[other] = m
                todo.append(other)
        if len(previous)>=args.max_states:
            capped = True
            break
        if processed % 10000 == 0:
            print('processed',processed,'reached',len(previous),'seconds',round(time.monotonic()-t0,1),flush=True)
    path = None
    if found:
        path=[]
        m=b
        while m is not None:
            path.append(m)
            m=previous[m]
        path.reverse()
    data=dict(forbidden_cell=args.forbid,floor=12,found=found,complete=not capped,
              processed=processed,reached=len(previous),path=path,
              auxiliary_cells=sorted({p for m in path for p in range(49) if m >> p & 1}-set(cells)) if path else None,
              closed_set=sorted(previous) if not todo and not capped else None,
              spanning_tree=list(previous.items()) if not todo and not capped else None,
              reachable_14_sets=sorted(m for m in previous if m.bit_count()==14))
    out=RES/f'discovery_full_board_forbid_{args.forbid}.json'
    out.write_text(json.dumps(data,indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k:v for k,v in data.items() if k not in ('path','closed_set','spanning_tree')},indent=2),flush=True)


if __name__ == '__main__':
    main()
