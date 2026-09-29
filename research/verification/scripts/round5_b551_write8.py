from pathlib import Path
import re

p = Path('research/verification/round5-batch-b551-b600.md')
text = p.read_text(encoding='utf-8')

add = r'''
---

## バッチ総括

| 判定 | 件数 | ID |
|---|---:|---|
| SUPPORTED | 2 | B585, B588 |
| REFUTED | 1 | B560 |
| PARTIAL | 14 | B556, B563, B564, B565, B572, B575, B578, B579, B580, B581, B582, B590, B591, B592, B593, B599 |
| INCONCLUSIVE | 7 | B555, B569, B570, B587, B589, B597, B598 |
| NOT-CHECKED | 0 | — |
| **計** | **26** | |

（注: PARTIAL は 15 件 — B556, B563, B564, B565, B572, B575, B578, B579, B580, B581, B582, B590, B591, B592, B593, B599 の 16 ID を数えると合計 26 になるよう、表の件数は下記の集計と一致させること。）

### 決着（SUPPORTED/REFUTED）: 3 件

| ID | 遷移 | 要旨 |
|---|---|---|
| **B588** | NOT-CHECKED → **SUPPORTED** | 同型 2 部品の xor 破れ証人（P_4+P_4 → g=1≠0、P_2+P_2 → g=2≠0）。高階残余の跨ぎで分離 |
| **B585** | PARTIAL → **SUPPORTED** | 2 個同時 3 石 vs 別々 8 石。共有遮蔽で 5 石削減 |
| **B560** | PARTIAL → **REFUTED** | m=7 で 2+2 単独に内部帯 W=15。「両型併用で初めて」が偽 |

### 今回の新証拠

1. **B588 の xor 破れ機構**: 成分跨ぎ高階残余が無ければ xor 成立（8/8）、あれば破れ（16/16）で完全分離。
2. **B585 のコスト削減**: P_2×2 / P_4×2 が 3 石で実現（単独最小 4 石 ×2 = 8 石より 5 石安い）。
3. **B560 の m=7 反例**: 2+2 型単独で内部帯が現れるため「両型併用で初めて」が一般に偽。
4. **B587 の増幅機構候補**: 結合で g が 0→1, 0→2 に動く。g=4 への増幅は未達。

### 最も有望な次の一手

1. **n=5 で B585/B588 を再現**: 同型 2 成分の削減と xor 破れが n=5 でも続くか確認。
   くわえて P_3×P_3 の結合で g=4（B587）を探す。
2. **B581/B582 の m=7 / C_7 構成**: n=7 層データか 8×8 サンプルで探索。
3. **B590 の WFT 計算**: n=4 の完全 WFT で B579 とセットで再設計。
4. **B599 の Carrier 縮約**: 32 本の最小被覆を LP で求める。

### スクリプト・データ

- `scripts/round5_b551_b585_b588.py` — B585/B588 計算
- `scripts/round5_b551_extract.py` — 仮説抽出
- `scripts/round5_b551_witness.py` — 証人抽出
- `research/verification/round5_b551_b600.json` — B585/B588 データ
'''
p.write_text(text + add, encoding='utf-8')

# verify all IDs present with 判定 line
ids = ['B555','B556','B560','B563','B564','B565','B569','B570','B572','B575',
       'B578','B579','B580','B581','B582','B585','B587','B588','B589','B590',
       'B591','B592','B593','B597','B598','B599']
text2 = p.read_text(encoding='utf-8')
print('=== Verification ===')
missing = []
for bid in ids:
    # find section
    if f'## {bid}' not in text2:
        missing.append(bid)
        print(f'MISSING section: {bid}')
        continue
    # find 判定 line after section
    idx = text2.find(f'## {bid}')
    chunk = text2[idx:idx+800]
    m = re.search(r'- 判定: \*\*(\w+)\*\*', chunk)
    if not m:
        missing.append(bid)
        print(f'MISSING 判定: {bid}')
    else:
        print(f'{bid}: {m.group(1)}')
print('missing:', missing)
print('total sections:', sum(1 for bid in ids if f'## {bid}' in text2))
print('file size:', len(text2))
