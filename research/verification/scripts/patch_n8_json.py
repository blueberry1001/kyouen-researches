import json
with open('/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/round5_prand_n8.json') as f:
    d = json.load(f)
d['levels'].append({'k': 15, 'size': 3368, 'n_P': 3368, 'n_N': 0, 'best_filter': 0.0, 'best_count': 0})
d['n_safe_subsets'] = 6700711937
d['max_safe_size'] = 15
d['n_P'] = d['n_P'] + 3368
d['note'] = 'P_max_filter_value is u32 fixed-point (SCALE=2^30); exact fraction requires big-int. Level 15 (terminal, 3368 states, all p=0) added post-scan.'
with open('/mnt/d/ghq/github.com/yuubinnkyoku/kyouen-researches/research/verification/round5_prand_n8.json', 'w') as f:
    json.dump(d, f, indent=2)
print('patched: n_P=', d['n_P'], 'n_safe=', d['n_safe_subsets'], 'K=', d['max_safe_size'])
