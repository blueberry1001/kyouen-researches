"""Explore a static certificate for the Cycle 42 open corridor question."""
from itertools import combinations
from collections import Counter, defaultdict
import json
from cycle8_lib import load_n7, det4, stones, RES


def instance():
    sets = load_n7()
    _, a, b = min(((x ^ y).bit_count(), x, y) for x in sets if x >> 24 & 1
                  for y in sets if not y >> 24 & 1)
    cells = stones(a | b, 49)
    local = lambda s: sum(1 << i for i, p in enumerate(cells) if s >> p & 1)
    a, b = local(a), local(b)
    quads = []
    for inds in combinations(range(len(cells)), 4):
        pts = [(cells[i] % 7, cells[i] // 7) for i in inds]
        if det4([[x*x+y*y, x, y, 1] for x, y in pts]) == 0:
            quads.append(sum(1 << i for i in inds))
    return cells, a, b, quads


def main():
    cells, a, b, quads = instance()
    pa, pb, common = a & ~b, b & ~a, a & b
    safe = []
    table = defaultdict(lambda: -1)
    counts = Counter()
    for m in range(1 << len(cells)):
        if any(m & q == q for q in quads):
            continue
        p, q, c = ((m & x).bit_count() for x in (pa, pb, common))
        table[p,q] = max(table[p,q], c)
        counts[p,q,c] += 1
        if m.bit_count() >= 12:
            safe.append(m)
    remaining = set(safe)
    components = []
    while remaining:
        seed = min(remaining)
        remaining.remove(seed)
        comp = [seed]
        for m in comp:
            for i in range(len(cells)):
                other = m ^ (1 << i)
                if other in remaining:
                    remaining.remove(other)
                    comp.append(other)
        components.append(comp)
    data = dict(cells=cells, a=a, b=b, quads=quads,
                capacity_table=[[table[p,q] for q in range(6)] for p in range(6)],
                components=[dict(size=len(c), a=a in c, b=b in c,
                                 signatures=sorted(set(((m & pa).bit_count(), (m & pb).bit_count(), (m & common).bit_count()) for m in c))) for c in components])
    (RES / 'discovery_static_barrier_exploration.json').write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(data, indent=2))


if __name__ == '__main__':
    main()
