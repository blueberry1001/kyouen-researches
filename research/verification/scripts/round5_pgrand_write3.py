from pathlib import Path

p = Path(r"D:\ghq\github.com\yuubinnkyoku\kyouen-researches\research\verification\round5-batch-pgrand.md")
text = p.read_text(encoding="utf-8")
add = r'''
---

## まとめ（p_rand 残余 / B504–B530）

### 判定集計

| ラベル | 件数 | ID |
|---|---:|---|
| **REFUTED** | 3 | B512, B513, B519 |
| **SUPPORTED** | 3 | B521, B527, B529 |
| **PARTIAL** | 7 | B504, B505, B507, B508, B514, B522, B524 |
| **INCONCLUSIVE** | 5 | B510, B520, B523, B528, B530 |

決着（REFUTED/SUPPORTED）: **6 件**。前進（PARTIAL 強化）: **7 件**。

### 主要な新事実

1. **δ_K(7) = 2**（B512 REFUTED / B513 REFUTED）
   7×7 の 14 石最大集合 16 本への被覆数が厳密に 2。
   対角の 2 角 {(0,0),(6,6)} または反対角 {(6,0),(0,6)} を消すと K≤13。
   「δ_K(n)≥3 (n≥4)」と「δ_K(7)=3」はいずれも偽。

2. **最小反転削除集合は禁止四点を含まないことがある**（B519 REFUTED）
   n=4 でサイズ 4 の最小反転集合 76 個のうち 48 個が禁止四点非包含。

3. **空族に 1 四点禁止を足すだけで必ず勝者が反転する**（B527 SUPPORTED）
   空族 g=0、単一禁止で g=1。臨界核は 4 点（F=194 に対して十分局所）。

4. **最小勝敗保持禁止族に共通四点なし**（B529 SUPPORTED）
   最小 g=0 族 10 個（サイズ 2 と 4）を列挙、共通四点が空。

### 実装バグの記録

`round5_b401_del3.json` は**無効**。
`board_square_minus` は `(x,y)` 座標列を要求するが、当該スクリプトは
整数 ID（0..15）を渡しており、点が一切削除されていなかった。
よって `n_K_drops=0, n_winner_flips=0` は「同じ盤の 560 回再計算」であり、
B518 の pure_triple_flips=12 と矛盾していた。
本バッチ `scripts/round5_pgrand_fast.py` は座標変換 `xy(i,n)=(i%n, i//n)` を
行い、n=4 の 2・3 点を正しく再計算した（K_drops=0 は**正しい**が、
winner_flips は 2 点で 12、3 点で 140、うち pure3 が 12）。

### データ

- `round5_pgrand.json` — 本バッチの厳密計算結果
- `round5_b501_prand_n7.json`（既存、n=7 p_rand）— B504/B505/B507/B508/B510 の n=7 側
- `round5_b401_prand_stats.json`（既存）— B504/B505/B508/B510 の n=5 統計
- `night-research/maxsafe_n7_K14.bin` — B513 の 16 最大集合

### 残った障害（次の一手）

1. n=5,6 の δ_K（B512 の全称は既に崩れたが、分布は未知）
2. 70 四点束の最小性（B523/B524 の分岐）
3. 空族→標準の完全 194 手追加順の反転頻度（B528/B530）
4. n=7-minus の勝敗 DP（B520 の W 保全）— n≥7 全計算禁止のため専任待ち

'''
p.write_text(text + add, encoding="utf-8")
print("wrote summary, total", len(text + add))
