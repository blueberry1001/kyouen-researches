import os

# Read specific files with focus on target IDs
files = {
 'research/verification/round3-batch-b542-b560.md': None,
 'research/verification/round3-batch-b591-b592.md': None,
 'research/verification/round5-batch-b401-b600.md': None,
 'research/verification/round5-workplan.md': None,
}

ids = ['B555','B556','B560','B563','B564','B565','B569','B570','B572','B575',
       'B578','B579','B580','B581','B582','B585','B587','B588','B589','B590',
       'B591','B592','B593','B597','B598','B599']

for fp in files:
    print('='*80)
    print(fp)
    print('='*80)
    with open(fp, encoding='utf-8') as f:
        text = f.read()
    # print sections around each target ID
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        l = lines[i]
        matched = None
        for bid in ids:
            if f'**{bid}' in l or l.strip().startswith(f'## {bid}') or f'## {bid} ' in l:
                matched = bid
                break
        if matched:
            # print until next ## or 80 lines
            j = i
            while j < len(lines) and j < i+80:
                if j > i and lines[j].startswith('## ') and not lines[j].startswith(f'## {matched}'):
                    break
                print(lines[j])
                j += 1
            print('---')
            i = j
        else:
            i += 1
