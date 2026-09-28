import json,sys,re
p=sys.argv[1] if len(sys.argv)>1 else '/tmp/r4_sec1.json'
raw=open(p,encoding='utf-8').read()
raw=re.sub(r',(\s*[}\]])', r'\1', raw)
d=json.loads(raw)
tr=d.get('two_row',{})
print("m  g0 states maxg K | maximal_hist | same all | transfail")
for m,v in tr.items():
    print(m, v['g_empty'], v['n_states'], v['max_g'], v['K'], v['maximal_hist'],
          v['B542_same_col'], v['B542_all_cols'], v['trans_fail'],'/',v['trans_checked'],
          '| gh=',v['g_hist'])
for key in ('three_row','three_row_variants','row_spacing_013','ap_construction','two_row_combinatorial'):
    if key in d and d[key]:
        print("==",key,"==")
        for m,v in d[key].items():
            print(' ',m,v)
