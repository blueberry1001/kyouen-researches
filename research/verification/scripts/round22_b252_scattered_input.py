"""Search same-size scattered removals disjoint from the central 8-point circle."""
from collections import Counter
from pathlib import Path
from random import Random
import json

from round22_rule_input import write_cases


def main():
    root = Path(__file__).resolve().parents[1]
    geometry = json.loads((root / 'round22_b252_n4_all_geometry.json').read_text(encoding='utf-8'))
    central = next(g for g in geometry['groups'] if g['coefficients'] == [1, -3, -3, 2])
    assert len(central['point_indices']) == 8 and len(central['quad_indices']) == 70
    central_indices = set(central['quad_indices'])
    all_indices = set(range(len(geometry['quad_masks'])))
    pool = sorted(all_indices-central_indices)
    group_of = {qi: g['group_id'] for g in geometry['groups'] for qi in g['quad_indices']}
    rng = Random(220252)
    cases = []
    for attempt in range(20):
        removed = sorted(rng.sample(pool, 70))
        counts = Counter(group_of[qi] for qi in removed)
        assert len(counts) >= 20 and max(counts.values()) < 15
        cases.append({'name': f'B252_scattered_{attempt}', 'seed': 220252,
                      'removed_indices': removed, 'removed_curve_count': len(counts),
                      'maximum_quads_removed_on_one_curve': max(counts.values()),
                      'kept_indices': sorted(all_indices-set(removed))})
    write_cases(root, 'round22_b252_scattered', geometry, cases)
    print('20 scattered 70-quad removals, all disjoint from the circle removal', flush=True)


if __name__ == '__main__':
    main()
