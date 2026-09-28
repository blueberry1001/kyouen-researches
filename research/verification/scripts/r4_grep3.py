import re,sys
raw=open(sys.argv[1],encoding='utf-8').read()
for m in sys.argv[2:]:
    mm=re.search(r'"%s": (\{.*?\}),?\n'%m, raw, re.S)
    print(m, mm.group(1)[:1200] if mm else 'NOT FOUND')
    print()
