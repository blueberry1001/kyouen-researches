import json
d=json.load(open(r'D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round2_b381.json'))
print('B401 details:', d.get('B401',{}).get('details',[]))
print('B404 n7:')
for e in d.get('B404',{}).get('n7',[]):
    print('  idx=%d pairs=%d hamming=%d phase=%s' % (e['idx'], e['n_pairs'], e['min_hamming'], e['phase']))
print('B402 relpos:', d.get('B402',{}).get('relpos_types'))
b382=d.get('B382',{})
print('B382 A:')
for e in b382.get('A',[]):
    print('  idx=%d r=%s n_first=%d types=%s' % (e['idx'], e['r'], e['n_first'], e['types']))
print('B382 B:')
for e in b382.get('B',[]):
    print('  idx=%d r=%s n_first=%d types=%s' % (e['idx'], e['r'], e['n_first'], e['types']))
b386=d.get('B386',{})
print('B386 max_shared:', b386.get('max_shared'), 'dist:', b386.get('shared_dist'))
print('B403:', d.get('B403'))
print('B409 details:', d.get('B409',{}).get('details',[]))
print('B385:', d.get('B385'))
print('B387:', d.get('B387'))
