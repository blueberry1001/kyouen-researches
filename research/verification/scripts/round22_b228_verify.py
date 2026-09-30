"""Independent complete-state B228 verification via whole-curve occupancy."""
from pathlib import Path
import hashlib
import json
import time

from round21_b224_verify import regenerate, solve


def main():
    start = time.perf_counter()
    source = Path(__file__).resolve()
    root = source.parents[1]
    points, groups, quads = regenerate(5)
    geometry_bytes = (root / 'round20_b224_geometry.json').read_bytes()
    geometry = json.loads(geometry_bytes)
    assert quads == geometry['quad_masks']
    for gi, (new, old) in enumerate(zip(groups, geometry['groups'], strict=True)):
        assert old['group_id'] == gi
        assert all(old[key] == value for key, value in new.items())
    scan_bytes = (root / 'round22_rules_scan.json').read_bytes()
    scan = {case['name']: case for case in json.loads(scan_bytes)['cases']}
    records = []
    for threshold in (9, 8, 6, 5, 4):
        selected_ids = [gi for gi, g in enumerate(groups)
                        if g['kind'] == 'line' or len(g['point_indices']) >= threshold]
        selected = [groups[gi] for gi in selected_ids]
        expected = sorted(q for gi in selected_ids for q in geometry['groups'][gi]['quad_indices'])
        result = solve(25, selected)
        case = scan[f'B228_threshold_{threshold}']
        assert expected == case['kept_indices']
        assert bool(result['g0']) == bool(case['outcome']) and case['outcome'] >= 0
        records.append({'circle_threshold': threshold, 'kept_group_ids': selected_ids,
                        'kept_circles': sum(g['kind'] == 'circle' for g in selected),
                        'kept_lines': sum(g['kind'] == 'line' for g in selected),
                        'kept_quads': len(expected), **result})
        print('threshold', threshold, 'g0', result['g0'], 'states', result['safe_states'], flush=True)
    outcomes = [bool(record['g0']) for record in records]
    flips = sum(a != b for a, b in zip(outcomes, outcomes[1:]))
    assert flips >= 2
    assert [record['kept_circles'] for record in records] == [0, 5, 17, 25, 217]
    assert all(record['kept_lines'] == 16 for record in records)
    assert all(set(a['kept_group_ids']) < set(b['kept_group_ids'])
               for a, b in zip(records, records[1:]))
    output = {'n': 5, 'winner_flips': flips, 'line_rule': 'All standard lines retained throughout',
              'records': records, 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'dependency_sha256': hashlib.sha256(source.with_name('round21_b224_verify.py').read_bytes()).hexdigest(),
              'geometry_sha256': hashlib.sha256(geometry_bytes).hexdigest(),
              'scan_sha256': hashlib.sha256(scan_bytes).hexdigest(),
              'seconds': time.perf_counter()-start}
    (root / 'round22_b228_verified.json').write_text(json.dumps(output, indent=2)+'\n', encoding='utf-8')
    print('PASS: exact winner flips', flips, flush=True)


if __name__ == '__main__':
    main()
