from pathlib import Path
p = Path('research/verification/round5-batch-b551-b600.md')
text = p.read_text(encoding='utf-8')
add = r'''
## B569 [統計] 拡張複体の穴の数は最善手の少なさに結びつく
- 判定: **INCONCLUSIVE**（前回: INCONCLUSIVE → 今回: INCONCLUSIVE。**比較対象の不在を再確認**）
- 前回の一手: 非零 Betti 複体は 7×7 最大集合複体（β_3=6）のみで統計比較不能
  （`round2-batch-b561.md`）。
- 今回の範囲: 既存ホモロジー結果の圧縮。n=6 最大集合複体（464 個）の Betti は計算資源の
  制約（n=7 の 16 頂点神経と異なり 464 頂点で面数が爆発）で未着手。
- 証拠: 既知の非零 Betti 複体は依然 1 つ（7×7, β_3=6）。比較には同一 (n,k,|L|,h) で
  Betti が異なる複体が必要だが、n=4,5 の最大集合複体は 3〜4 点で退化的。
- 残った障害: n=6 最大集合複体の Betti 計算と、層別必勝手比率との対応表。
  統計命題で標本 1 では決着不能。NOT-CHECKED ではなく INCONCLUSIVE としたのは
  「比較対象を特定したが揃わない」ため。

## B570 [存在] 変形障壁は安全複体のホモロジーだけからは復元できない
- 判定: **INCONCLUSIVE**（前回: INCONCLUSIVE → 今回: INCONCLUSIVE。**証明方針の整理のみ**）
- 前回の一手: 同一 Betti・同一最大サイズで連結低下が異なる盤の対を探索したが、
  手元の複体は Betti が一致せず（`round2-batch-b561.md`）。
- 今回の範囲: 既存結果の圧縮と証明方針の整理。部分盤系列（角を落とした盤など）で
  Betti と低下の対を測る計画は有効だが、本回では実行せず。
- 証拠: 既知の低下は n=6 で 2（G_9 連結）、n=7 で 3（G_12 が 8 成分）だが
  最大サイズ自体が違う（11 vs 14）ため比較対象にならない。証明には
  「Betti が等しい 2 盤で低下が異なる」証人 1 対が必要。
- 残った障害: 証人の探索。部分盤系列で Betti を揃えつつ低下を変える構成が未作成。
'''
p.write_text(text + add, encoding='utf-8')
print('appended B569-B570')
