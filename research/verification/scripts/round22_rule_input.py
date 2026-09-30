"""Prepare B228/B252 exact scans from the already independently audited geometry."""
from pathlib import Path
import hashlib
import json


def write_cases(root, stem, geometry, cases):
    quads = geometry['quad_masks']
    lines = [f"{len(geometry['point_order'])} {len(quads)} {len(cases)}", ' '.join(map(str, quads))]
    lines += [f"{case['name']} {len(case['kept_indices'])} "
              + ' '.join(map(str, case['kept_indices'])) for case in cases]
    (root / f'{stem}_input.txt').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    (root / f'{stem}_cases.json').write_text(json.dumps(cases, indent=2)+'\n', encoding='utf-8')


def main():
    source = Path(__file__).resolve()
    root = source.parents[1]
    geometry = json.loads((root / 'round20_b224_geometry.json').read_text(encoding='utf-8'))
    groups = geometry['groups']
    all_indices = set(range(len(geometry['quad_masks'])))
    cases = []
    for threshold in (9, 8, 6, 5, 4):
        kept_groups = [g for g in groups if g['kind'] == 'line'
                       or len(g['point_indices']) >= threshold]
        cases.append({'name': f'B228_threshold_{threshold}', 'circle_threshold': threshold,
                      'kept_group_ids': [g['group_id'] for g in kept_groups],
                      'kept_indices': sorted(q for g in kept_groups for q in g['quad_indices'])})
    for group in groups:
        if group['kind'] == 'circle' and len(group['point_indices']) > 4:
            if group['d4_orbit_representative'] != group['group_id']:
                continue
            cases.append({'name': f'B252_circle_{group["group_id"]}',
                          'removed_group_id': group['group_id'],
                          'removed_indices': group['quad_indices'],
                          'kept_indices': sorted(all_indices-set(group['quad_indices']))})
    write_cases(root, 'round22_rules', geometry, cases)
    metadata = {'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                'geometry_sha256': hashlib.sha256((root / 'round20_b224_geometry.json').read_bytes()).hexdigest()}
    (root / 'round22_rule_inputs_metadata.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
    print('cases:', len(cases))


if __name__ == '__main__':
    main()
