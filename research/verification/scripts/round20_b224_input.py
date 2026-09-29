"""Build complete geometric circle/line bundles on the full 5x5 board."""
from collections import defaultdict
from pathlib import Path
import hashlib
import json

from round20_b255_n5 import Board, members
from round18_local_geometry import curve, on_curve


def main():
    board = Board(5)
    groups = defaultdict(list)
    for i, quad in enumerate(board.quads):
        ids = list(members(quad))
        groups[curve([board.points[j] for j in ids[:3]])].append(i)
    keys = sorted(groups)
    qgroup = {}
    records = []
    for gi, key in enumerate(keys):
        indices = groups[key]
        points = [p for p, point in enumerate(board.points) if on_curve(key, point)]
        union = set().union(*(set(members(board.quads[i])) for i in indices))
        assert union == set(points)
        for i in indices:
            qgroup[i] = gi
        records.append({"group_id": gi, "coefficients": key, "point_indices": points,
                        "quad_indices": indices, "kind": "line" if key[0] == 0 else "circle"})
    winning = [p for p, (x, y) in enumerate(board.points)
               if (x+y) % 2 == 0 and (x, y) not in [(0, 0), (0, 4), (4, 0), (4, 4)]]
    target = sum(1 << p for p in winning)
    mask_to_group = {sum(1 << p for p in r['point_indices']): r['group_id'] for r in records}
    orbit_representatives = []
    for record in records:
        images = []
        for reflect in (False, True):
            for rotation in range(4):
                transformed = 0
                for p in record['point_indices']:
                    x, y = board.points[p]
                    if reflect:
                        x = 4-x
                    for _ in range(rotation):
                        x, y = 4-y, x
                    transformed |= 1 << (x+5*y)
                images.append(mask_to_group[transformed])
        record['d4_orbit_representative'] = min(images)
        orbit_representatives.append(min(images))
    root = Path(__file__).resolve().parents[1]
    lines = [f'25 {len(board.quads)} {len(keys)} {target}']
    lines += [f'{q} {qgroup[i]}' for i, q in enumerate(board.quads)]
    lines += [str(gi) for gi in orbit_representatives]
    (root / 'round20_b224_input.txt').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    source = Path(__file__)
    out = {"n": 5, "point_order": board.points, "quad_masks": board.quads, "groups": records,
           "target_winning_first_moves": winning,
           "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
           "dependencies_sha256": {name: hashlib.sha256(source.with_name(name).read_bytes()).hexdigest()
                                   for name in ['round20_b255_n5.py', 'round18_local_geometry.py', 'kyouen_core.py']}}
    (root / 'round20_b224_geometry.json').write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('complete geometric bundles:', len(keys), 'target W:', winning)


if __name__ == '__main__':
    main()
