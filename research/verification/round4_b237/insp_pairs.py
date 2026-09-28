import json, itertools
D = r'research\verification\batch09_pairs_n4.json'
d = json.load(open(D, encoding='utf-8'))
print('n_pairs', d['n_pairs'], 'n_flip_pair', d['n_flip_pair'],
      'n_K_drop', d['n_K_drop'], 'additive', d['n_K_loss_additive'],
      'g_combo', d['n_g_combo_effect'])
w = d['B204_witnesses']
print('witness type', type(w), 'len', len(w))
print(json.dumps(w, ensure_ascii=False)[:1500])
r = d['rows']
print('rows len', len(r))
print('row0', json.dumps(r[0], ensure_ascii=False))
