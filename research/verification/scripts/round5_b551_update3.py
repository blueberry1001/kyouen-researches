from pathlib import Path
p = Path('research/verification/round5-batch-b551-b600.md')
text = p.read_text(encoding='utf-8')

old = '''1. **n=5 で B585/B588 を再現**: 同型 2 成分の削減と xor 破れが n=5 でも続くか確認。
   くわえて P_3×P_3 の結合で g=4（B587）を探す。'''
new = '''1. **B587 の g=4 増幅**: n=5 で P_3×P_3 は g=3 まで到達。|S|=6 以上か n=6 で
   強い結合（g=4）を探す。B585 の n=5 コスト削減の確認も残る。'''
if old in text:
    text = text.replace(old, new)
    print('updated next-steps')
else:
    print('next-steps block not found')

p.write_text(text, encoding='utf-8')
print('final file lines:', len(text.splitlines()))
