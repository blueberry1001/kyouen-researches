"""Build a small static capacity certificate and a width-11 witness."""
from itertools import combinations
from collections import Counter
import json
from discover_static_barrier import instance
from discover_corridor_auxiliary import path_at_floor
from cycle8_lib import RES


def main():
    cells, a, b, quads = instance()
    pa, pb = a & ~b, b & ~a
    candidates = []
    for k in range(13, 20):
        for inds in combinations(range(19), k):
            m = sum(1 << i for i in inds)
            if (m & pb).bit_count() - (m & pa).bit_count() in (2, 3):
                candidates.append(m)
    covers = [{i for i, m in enumerate(candidates) if m & q == q} for q in quads]
    uncovered = set(range(len(candidates)))
    chosen = []
    while uncovered:
        j = max(range(len(quads)), key=lambda j: len(covers[j] & uncovered))
        assert covers[j] & uncovered, 'A safe counterexample exists'
        chosen.append(j)
        uncovered -= covers[j]
    path, reached = path_at_floor(cells, a, b, quads, 11)
    assert path is not None
    data = dict(cells=cells, a=a, b=b, barrier_differences=[2,3],
                capacity_bound=12, candidate_count=len(candidates),
                candidate_sizes=dict(sorted(Counter(m.bit_count() for m in candidates).items())),
                covering_quads=[quads[j] for j in chosen], path_floor_11=path)
    out = RES / 'discovery_corridor_static_certificate.json'
    out.write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8', newline='\n')
    print('static certificate:', len(chosen), 'quads cover', len(candidates), 'candidates')
    print('union path:', len(path)-1, 'moves; minimum', min(m.bit_count() for m in path))


if __name__ == '__main__':
    main()
