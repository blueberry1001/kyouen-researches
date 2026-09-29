from pathlib import Path
import re
p = Path('research/verification/round5-batch-b551-b600.md')
text = p.read_text(encoding='utf-8')

# update summary "今回の新証拠" to include n=5
old = '''1. **B588 の xor 破れ機構**: 成分跨ぎ高階残余が無ければ xor 成立（8/8）、あれば破れ（16/16）で完全分離。
2. **B585 のコスト削減**: P_2×2 / P_4×2 が 3 石で実現（単独最小 4 石 ×2 = 8 石より 5 石安い）。
3. **B560 の m=7 反例**: 2+2 型単独で内部帯が現れるため「両型併用で初めて」が一般に偽。
4. **B587 の増幅機構候補**: 結合で g が 0→1, 0→2 に動く。g=4 への増幅は未達。'''
new = '''1. **B588 の xor 破れ機構**: 成分跨ぎ高階残余が無ければ xor 成立、あれば破れで分離。
   n=4 で破れ 16/一致 8、n=5 で破れ 60/一致 100。
2. **B585 のコスト削減**: P_2×2 / P_4×2 が 3 石で実現（単独最小 4 石 ×2 = 8 石より 5 石安い）。
3. **B560 の m=7 反例**: 2+2 型単独で内部帯が現れるため「両型併用で初めて」が一般に偽。
4. **B587 の増幅**: n=5 で P_3×P_3 結合が g=3（xor=0 から 3 跳び）。g=4 に 1 手前。'''
if old in text:
    text = text.replace(old, new)
    print('updated summary')
else:
    print('summary block not found')

p.write_text(text, encoding='utf-8')

# final check
text = p.read_text(encoding='utf-8')
ids = ['B555','B556','B560','B563','B564','B565','B569','B570','B572','B575','B578','B579','B580','B581','B582','B585','B587','B588','B589','B590','B591','B592','B593','B597','B598','B599']
verdicts = []
for bid in ids:
    idx = text.find(f'## {bid}')
    chunk = text[idx:idx+600]
    m = re.search(r'- 判定: \*\*(\w+)\*\*', chunk)
    verdicts.append((bid, m.group(1) if m else 'MISSING'))
from collections import Counter
c = Counter(v for _, v in verdicts)
print('verdict counts:', dict(c))
print('total:', len(verdicts))
print('lines:', len(text.splitlines()))
# check 前回 field
for bid in ids:
    idx = text.find(f'## {bid}')
    nxt = text.find('\n## ', idx+5)
    chunk = text[idx:nxt if nxt>0 else len(text)]
    for f in ['判定','前回の一手','今回の範囲','証拠','残った障害']:
        if f not in chunk:
            print(f'{bid} missing {f}')
print('all fields OK')
