"""Exhaustively test each one-cell enlargement of the 19-cell corridor."""
from collections import deque
from itertools import combinations
import json
from cycle8_lib import det4, RES
from discover_static_barrier import instance


def path_at_floor(cells, a, b, quads, floor):
    by_cell = [[] for _ in cells]
    for q in quads:
        for i in range(len(cells)):
            if q >> i & 1:
                by_cell[i].append(q)
    prev = {a: None}
    todo = deque([a])
    while todo:
        m = todo.popleft()
        if m == b:
            path = []
            while m is not None:
                path.append(m)
                m = prev[m]
            return path[::-1], sorted(prev)
        for i in range(len(cells)):
            other = m ^ (1 << i)
            if other in prev or other.bit_count() < floor:
                continue
            if not m >> i & 1 and any(other & q == q for q in by_cell[i]):
                continue
            prev[other] = m
            todo.append(other)
    return None, sorted(prev)


def main():
    cells, a, b, quads = instance()
    rows = []
    closed_sets = []
    for p in range(49):
        if p in cells:
            continue
        extra = []
        for inds in combinations(range(19), 3):
            pts = [(cells[i] % 7, cells[i] // 7) for i in inds] + [(p % 7, p // 7)]
            if det4([[x*x+y*y, x, y, 1] for x,y in pts]) == 0:
                extra.append((1 << 19) | sum(1 << i for i in inds))
        path, reached = path_at_floor(cells+[p], a, b, quads+extra, 12)
        closed_set_id = None
        if path is None:
            if reached not in closed_sets:
                closed_sets.append(reached)
            closed_set_id = closed_sets.index(reached)
        rows.append(dict(extra_cell=p, xy=[p%7,p//7], connected=path is not None,
                         visited=len(reached), added_quads=len(extra), path=path,
                         closed_set_id=closed_set_id))
        print(p, path is not None, len(reached), flush=True)
    data = dict(cells=cells, a=a, b=b, floor=12, rows=rows, closed_sets=closed_sets)
    (RES / 'discovery_corridor_auxiliary.json').write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8', newline='\n')
    print('unlocking cells', [r['extra_cell'] for r in rows if r['connected']])
    for row in rows:
        if row['path']:
            cc = cells + [row['extra_cell']]
            print('path moves', len(row['path'])-1)
            for old, new in zip(row['path'], row['path'][1:]):
                i = (old ^ new).bit_length()-1
                print('+' if new >> i & 1 else '-', (cc[i]%7, cc[i]//7), new.bit_count())


if __name__ == '__main__':
    main()
