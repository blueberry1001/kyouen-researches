"""Exact D4 orbit reduction of single forbidden-quad removals."""
from pathlib import Path
import argparse
import json

from round21_b224_verify import regenerate, members


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--n', type=int, default=6)
    args = parser.parse_args()
    n = args.n
    assert 2 <= n <= 7
    root = Path(__file__).resolve().parents[1]
    points, _, quads = regenerate(n)
    quad_id = {q: qi for qi, q in enumerate(quads)}
    orbits = {}
    for qi, q in enumerate(quads):
        images = []
        for reflect in (False, True):
            for rotations in range(4):
                transformed = 0
                for p in members(q):
                    x, y = points[p]
                    if reflect:
                        x = n-1-x
                    for _ in range(rotations):
                        x, y = n-1-y, x
                    transformed |= 1 << (x+n*y)
                images.append(quad_id[transformed])
        rep = min(images)
        orbits.setdefault(rep, set()).add(qi)
        assert set(images) >= {rep, qi}
    assert sorted(qi for orbit in orbits.values() for qi in orbit) == list(range(len(quads)))
    out = {'n': n, 'point_order': points, 'quad_masks': quads,
           'orbits': [{'representative': rep, 'members': sorted(orbit)} for rep, orbit in sorted(orbits.items())]}
    stem = f'round23_b251_n{n}'
    (root / f'{stem}_geometry.json').write_text(json.dumps(out, indent=2)+'\n', encoding='utf-8')
    lines = [f'{n*n} {len(quads)} {len(orbits)}', ' '.join(map(str, quads)),
             ' '.join(map(str, orbits))]
    (root / f'{stem}_input.txt').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(n, 'quad count', len(quads), 'D4 orbit count', len(orbits), flush=True)


if __name__ == '__main__':
    main()
