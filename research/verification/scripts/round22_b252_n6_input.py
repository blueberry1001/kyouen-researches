"""Prepare complete-circle removal candidates on the full n x n square."""
import argparse
from collections import Counter
from itertools import combinations
from pathlib import Path
import json

from round21_b224_verify import regenerate
from round22_rule_input import write_cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--n', type=int, default=6)
    parser.add_argument('--min-circle-points', type=int, default=5)
    parser.add_argument('--stem', default='round22_b252_n6')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    n = args.n
    assert 4 <= n <= 7
    points, groups, quads = regenerate(n)
    mask_ids = {sum(1 << p for p in group['point_indices']): gi
                for gi, group in enumerate(groups)}
    quad_ids = {q: qi for qi, q in enumerate(quads)}
    for gi, group in enumerate(groups):
        group['group_id'] = gi
        group['quad_indices'] = sorted(quad_ids[sum(1 << p for p in ids)]
                                      for ids in combinations(group['point_indices'], 4))
        images = []
        for reflect in (False, True):
            for rotation in range(4):
                mask = 0
                for p in group['point_indices']:
                    x, y = points[p]
                    if reflect:
                        x = n-1-x
                    for _ in range(rotation):
                        x, y = n-1-y, x
                    mask |= 1 << (x+n*y)
                images.append(mask_ids[mask])
        group['d4_orbit_representative'] = min(images)
    geometry = {'n': n, 'point_order': points, 'groups': groups, 'quad_masks': quads}
    (root / f'{args.stem}_geometry.json').write_text(json.dumps(geometry, indent=2)+'\n', encoding='utf-8')
    all_indices = set(range(len(quads)))
    cases = [{'name': f'standard_n{n}', 'kept_indices': sorted(all_indices)}]
    for group in sorted(groups, key=lambda g: (-len(g['point_indices']), g['group_id'])):
        if group['kind'] != 'circle' or len(group['point_indices']) < args.min_circle_points:
            continue
        if group['group_id'] != group['d4_orbit_representative']:
            continue
        cases.append({'name': f'B252_n{n}_circle_{group["group_id"]}',
                      'removed_group_id': group['group_id'],
                      'removed_indices': group['quad_indices'],
                      'kept_indices': sorted(all_indices-set(group['quad_indices']))})
    write_cases(root, args.stem, geometry, cases)
    print('geometry:', len(groups), 'quads:', len(quads),
          'histogram:', Counter((g['kind'], len(g['point_indices'])) for g in groups), flush=True)
    print('cases:', len(cases), flush=True)


if __name__ == '__main__':
    main()
