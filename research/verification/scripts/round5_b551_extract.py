import re, os, sys

path = 'research/hypothesis-bank-round2-2026-09-27.md'
with open(path, encoding='utf-8') as f:
    lines = f.readlines()

ids = ['B555','B556','B560','B563','B564','B565','B569','B570','B572','B575',
       'B578','B579','B580','B581','B582','B585','B587','B588','B589','B590',
       'B591','B592','B593','B597','B598','B599']

print('=== HYPOTHESIS BANK ===')
for i, l in enumerate(lines):
    for bid in ids:
        if f'**{bid}' in l:
            print(f'{i+1}: {l.rstrip()}')
            break

print()
print('=== SECTION HEADERS (context) ===')
for i, l in enumerate(lines):
    if l.startswith('## '):
        print(f'{i+1}: {l.rstrip()[:120]}')

print()
print('=== PREVIOUS VERDICT FILES ===')
vdir = 'research/verification'
for fn in sorted(os.listdir(vdir)):
    if not fn.endswith('.md'):
        continue
    fp = os.path.join(vdir, fn)
    with open(fp, encoding='utf-8') as f:
        text = f.read()
    found = [bid for bid in ids if bid in text]
    if found:
        print(fn, ':', ' '.join(found))
