import json
with open('research/verification/round5_b551_b600.json', encoding='utf-8') as f:
    d = json.load(f)

b588 = d['b588']
print('=== B588 detail ===')
print('same-type pairs:', len(b588['same_type_pairs']))
print('with cross higher:', len(b588['with_cross_higher']))
print('type_pair_counts:', b588['type_pair_counts'])

# check xor for cross-higher cases
cross = b588['with_cross_higher']
mismatch = [r for r in cross if r['g_xor'] is not None and r['g_total'] != r['g_xor']]
match = [r for r in cross if r['g_xor'] is not None and r['g_total'] == r['g_xor']]
print(f'cross-higher: xor match={len(match)}, mismatch={len(mismatch)}')
for r in mismatch[:5]:
    print('  MISMATCH:', r)
print()
print('sample cross-higher match:')
for r in match[:3]:
    print(' ', r['types'], 'g=', r['g_total'], 'xor=', r['g_xor'], 'cross=', r['cross_higher_count'])

print()
print('=== B585 detail ===')
b585 = d['b585']
print('single:', b585['single_comp_min_cost'])
print('double same:', b585.get('double_comp_min_cost'))
print('double mixed:', b585.get('double_mixed_min_cost'))
print('savings:', b585['savings'])
print('two_comp_costs sample:', b585['two_comp_costs'][:3])
