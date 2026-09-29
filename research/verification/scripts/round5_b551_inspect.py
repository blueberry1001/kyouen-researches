import json

with open('research/verification/round2_b561.json', encoding='utf-8') as f:
    d = json.load(f)

for key in ['b581','b582','b583','b584','b585','b586','b587','b588','b589','b590']:
    print('='*60)
    print('KEY:', key)
    v = d[key]
    if isinstance(v, dict):
        for k2, v2 in v.items():
            if isinstance(v2, (list, dict)) and len(str(v2)) > 400:
                print(f'  {k2}: <{type(v2).__name__} len={len(v2)}> sample={str(v2)[:300]}')
            else:
                print(f'  {k2}: {v2}')
    elif isinstance(v, list):
        print(f'  list len={len(v)} sample={str(v[:3])[:400]}')
    else:
        print(f'  {v}')
