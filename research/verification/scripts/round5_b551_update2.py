from pathlib import Path
p = Path('research/verification/round5-batch-b551-b600.md')
text = p.read_text(encoding='utf-8')

# Update B588 今回の範囲
old = '''- 今回の範囲: n=4 全安全集合（|S|≤8）で、R(S) の 2 点辺グラフがちょうど 2 成分・
  両成分が同一抽象型の配置を全数抽出。g(S) と g(部品1)⊕g(部品2) を比較。
  さらに高階残余（3・4 点辺）が成分を跨ぐかを検査。
  スクリプト: `scripts/round5_b551_b585_b588.py`、データ: `round5_b551_b600.json` → b588。'''
new = '''- 今回の範囲: n=4 全安全集合（|S|≤8）と n=5 全安全集合（|S|≤5）で、R(S) の 2 点辺グラフが
  ちょうど 2 成分・両成分が同一抽象型の配置を全数抽出。g(S) と g(部品1)⊕g(部品2) を比較。
  さらに高階残余（3・4 点辺）が成分を跨ぐかを検査。
  スクリプト: `scripts/round5_b551_b585_b588.py`, `scripts/round5_b551_n5scan.py`、
  データ: `round5_b551_b600.json` → b588, b588_n5_sample。'''
if old in text:
    text = text.replace(old, new)
    print('updated B588 scope')
else:
    print('B588 scope not found')

# Update B587 今回の範囲
old2 = '''- 今回の範囲: B588 の計算と併せて連結構成を探索。n=4 で P_3×P_3 の同型 2 成分は未発見、
  P_2×P_2 と P_4×2 の結合で g が xor から外れる例を発見（B588 参照）。'''
new2 = '''- 今回の範囲: B588 の計算と併せて連結構成を探索。n=4 で P_3×P_3 は未発見、
  n=5（|S|≤5）で P_3×P_3 を 16 例発見。P_2×P_2 と P_4×2 の結合も確認（B588 参照）。'''
if old2 in text:
    text = text.replace(old2, new2)
    print('updated B587 scope')
else:
    print('B587 scope not found')

p.write_text(text, encoding='utf-8')
print('done')
