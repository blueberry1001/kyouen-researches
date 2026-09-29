import json
with open('research/verification/round5_b551_b600.json',encoding='utf-8') as f:
    d=json.load(f)
b588=d['b588']
seen=set()
print('=== B588 xor-violation witnesses (unique) ===')
for r in b588['with_cross_higher']:
    if r['g_xor'] is not None and r['g_total']!=r['g_xor']:
        comps_t = tuple(tuple(tuple(p) for p in c) for c in r['comps'])
        key=(comps_t, r['g_total'])
        if key in seen: continue
        seen.add(key)
        print('S_size',r['S_size'],'types',r['types'],'g',r['g_total'],'xor',r['g_xor'],'cross',r['cross_higher_count'])
        print('  comps',r['comps'])
print('unique mismatch configs:',len(seen))

print()
print('=== no-cross xor-ok cases ===')
for r in b588['same_type_pairs']:
    if r['cross_higher_count']==0 and r['g_xor'] is not None:
        print(' ',r['types'],'g',r['g_total'],'xor',r['g_xor'])
        print('   comps',r['comps'])
