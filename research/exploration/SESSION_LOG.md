# 探索セッション記録 — research/explore-unknown-facts-20260925-0034

非自明な事実の探索ログ。発見の本体は `research/findings.md` の F-K 以降を参照。

## 実施した探索

| # | 主題 | 成果 |
|---|---|---|
| 1 | 既知棚卸し | night-research CYCLE1–9、K_n、勝敗列、最大配置 |
| 2 | 禁止4点組の線/円分解 | forbidden = Σ C(\|L\|,4)+Σ C(\|C\|,4) が公開値と一致 (F-L) |
| 3 | 円上格子点の数論 | 2平方和の奇表現数で説明、n=12–24 で 16 点の高原 (F-K) |
| 4 | 暫定公式の反例 | 4(⌊n/4⌋+1) は n=16 で偽 (F-N) |
| 5 | 共線の方向分解 | n≤6 は軸+対角のみ、n=7 から傾き ±2 (F-L) |
| 6 | 密度スケール則 | dens·n²≈定数、forbidden≈0.054 n^6 (F-O, F-T) |
| 7 | 証明書 witness 鎖 | 先手必勝盤は空盤 WIN→1石 LOSS の 2 ノード (F-M) |
| 8 | 最適対局長 | n≤6 で終局石数、n=5,6 で複数長 (F-Q) |
| 9 | 極大スペクトル | n=3..6 完全分布、CYCLE5 の maximum=maximal 混同を訂正 (F-R, F-P, F-U) |
| 10 | 5×5 サイズ5極大 | 棒状 4 個、単一 D4 軌道 (F-S) |
| 11 | 状態の正規化 | KYOENC3 は D4 正規形で保存 (noncanonical=0) |

## 実装

- `scripts/analysis/explore_*.py` — 各探索
- `night-research/maximal_spectrum_enum.cpp` — 極大全数列挙
- `night-research/list_maximal_size.cpp` — 指定サイズ極大の一覧
- `research/exploration/exploration_report*.json` — 生データ

## 未完了・次にやること

1. n=7 の極大スペクトル (C++ で node limit を上げる)
2. n=6 サイズ 6 極大 8 個の幾何分類
3. 0.054 の理論的導出
4. K_9 が 17 か 18+ か (128-bit maxsafe)
5. n=5 で 5 石極大が負け初手後にしか現れないか
6. 証明書 n=8,9 の witness 鎖・対局長
7. 空盤 Nimber の n=7 以降

## 検証の対応表 (実装交差)

| 量 | Python | C++ | 既知 |
|---|---|---|---|
| n=3 極大 | {5:56} | — | CYCLE1 56 |
| n=4 極大 | {5:176,6:688,7:64} | — | CYCLE1 928 |
| n=5 極大 | {5:4,6:1136,7:11280,8:4340,9:100} | 一致 | CYCLE1 16860 |
| n=6 最大 | — | 464@11 | CYCLE5 464 |
| forbidden n=2..7 | 一致 | 一致 | 公開表 |
