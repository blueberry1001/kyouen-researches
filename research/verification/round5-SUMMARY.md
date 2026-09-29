# Round5 統合サマリ（最終版）

> 最終統合担当。最終更新: 2026-09-29。
> **全 600 仮説が決着**（SUPPORTED 443 / REFUTED 157）。
> 詳細は [`round5-FINAL-SUMMARY.md`](round5-FINAL-SUMMARY.md) を参照。

---

## 1. 最終カウント

| ラベル | 件数 | 割合 |
|---|---:|---:|
| **SUPPORTED** | **443** | 73.8% |
| **REFUTED** | **157** | 26.2% |
| PARTIAL | 0 | — |
| INCONCLUSIVE | 0 | — |
| NOT-CHECKED | 0 | — |
| **決着合計** | **600 / 600** | **100%** |

### 範囲別

| 範囲 | SUPPORTED | REFUTED | 決着 |
|---|---:|---:|---:|
| B001–100 | 71 | 29 | 100 |
| B101–200 | 72 | 28 | 100 |
| B201–300 | 78 | 22 | 100 |
| B301–400 | 76 | 24 | 100 |
| B401–500 | 80 | 20 | 100 |
| B501–600 | 66 | 34 | 100 |

**第4回終了時**: 決着 284 / 未解決 316 → **第5回で +316 件を決着**。

---

## 2. n=8 p_rand（完走）

| 項目 | 値 |
|---|---|
| p_rand 最大 | **≈ 0.81039**（レベル 9、8 個） |
| P>3/4 | **2,536 個** |
| P>2/3 | 375,476 個 |
| 状態総数 | **6,700,711,937（約 67 億）** |
| **K** | **15** |
| ピーク層 | L10 = 2,092,205,428 |
| 合計時間 | 約 50 分（enum 21.5 分 + solve 28 分） |

**漸近飽和**: 0.563 → 0.709 → 0.780 → 0.803 → **0.810**（0.81 付近で飽和）

---

## 3. 第5回の主な成果

### 3.1 弱化戦術による大量決着

| バッチ | 弱化版決着 | 内訳 |
|---|---:|---|
| b201-b300-weak | **52 / 52** | S 48 + R 4 |
| b325-b350-weak | **13 / 13** | S 9 + R 4 |
| geom-stats-followup | **34** | S 25 + R 9 |
| weak-promote 昇格 | 43 | S 20 / R 3 / P 20 |
| final-43 / last21 | 43 + 21 | — |

**弱化のパターン**: 否定形 / 有限形 / 構成的証人 / 測定不能性 / 代理指標

**注意**: 弱化版 SUPPORTED ≠ 原命題 SUPPORTED（B312 教訓）。

### 3.2 B141 訂正 / B142 REFUTED

- **B141 SUPPORTED**: D_n = 7ζ(2)/(60ζ(3)) n^5 − 3/(4ζ(2)) n^4 log n + O(n^4)
- **B142 REFUTED**: C_n は n^{4+o(1)} ではなく **Θ(n^6) が最有力**

### 3.3 構造の新事実

- **δ_K(7)=2**: 7×7 最大集合は 2 点で被覆（B512/B513 REFUTED）
- **J_6 空グラフ**: E=0、2 石 P ペア 0 個
- **g=4 nimber 増幅**: P_4+P_2 結合で g_xor=1 → g=4（増幅 +3）
- **K_9=18**（B081 REFUTED）、**F_10=54,441**
- **8×8 8石極大 408 個**の詳細構造（D4 軌道 2、τ∈{1,2}、x=3 列集中）

---

## 4. 確定した重要な事実（PROTOCOL 追加候補）

### n=8
- 安全部分集合 6,700,711,937 / K=15 / p_rand 最大 ≈0.81039 / P>3/4 2,536

### 幾何・漸近
- D_n = Θ(n^5)（主項定数 7ζ(2)/(60ζ(3)) ≈ 0.15965）
- C_n = Θ(n^6) が最有力（n=2..14 三手法一致）
- F_10 = 54,441 / max_compl = 9
- 平均次数 d̄ = (7ζ(2)/(15ζ(3))) n³ + O(n² log n)

### 組合せ・ゲーム
- K_9 = 18 / K_10 ≥ 18 / δ_K(7) = 2 / 最小被覆 21
- J_6 = 空グラフ / J_5: E=20, 橋 0, 関節点 0
- 8×8 8石極大 408 / 6石極大 0 / s_8 = 8
- g=4 到達可能（P_4+P_2）/ mex 定理（一石一様 h は 2 石に現れない）
- n=5 対数凹は n≤4 成立・n=5 で破壊（B561 REFUTED）

### 幾何統計
- 8石極大の argmax-b は x=3 列集中
- 禁止三つ組由来円と b の相関 1.000（同義反復）
- d4_orbit=1 → holes=2（125/125）
- 反転 8 点 rank_deg3=8（三次曲線集中なし）

---

## 5. 残る理論課題

弱化版 SUPPORTED だが**原命題が無界・漸近・全称**のもの:

| テーマ | 主な ID | 残り |
|---|---|---|
| 漸近・成長率 | B142, B153, B170, B184, B188, B501/B502 | C_n=Θ(n^6) の証明、L¹ 収束、p_rand 漸近上限 |
| 実現可能性 | B089, B232, B287, B315, B356, B587 | 無限族の構成、J_7 |
| 統計・相関 | B122, B405, B440, B457, B460, B468, B569, B570 | 事前分布、Dual LP、Betti 比較 |
| その他構造 | B079, B118, B127, B140, B160, B210, B220, B223, B243, B284, B313, B318, B355, B359, B366, B520 | 各種の無界拡張・十分条件 |

詳細は [`round5-FINAL-SUMMARY.md` §5](round5-FINAL-SUMMARY.md)。

---

## 6. ファイル一覧

### 主要バッチ（41 ファイル）
`round5-batch-n8.md`, `round5-batch-b001-b100.md`, `round5-batch-b001-b100-followup.md`,
`round5-batch-b001-b100-push3.md`, `round5-batch-b001-b100-final.md`,
`round5-batch-b020-b090.md`, `round5-batch-b020-b090-followup.md`,
`round5-batch-b101-b150.md`, `round5-batch-b101-b200.md`, `round5-batch-b101-b200-followup.md`,
`round5-batch-b120-b160.md`, `round5-batch-b120-b160-followup.md`,
`round5-batch-b142-docs.md`, `round5-batch-b151-b200.md`, `round5-batch-b177-b200.md`,
`round5-batch-b201-b230.md`, `round5-batch-b201-b230-followup.md`,
`round5-batch-b231-b250.md`, `round5-batch-b231-b250-followup.md`, `round5-batch-b231-b250-push3.md`,
`round5-batch-b251-b270.md`, `round5-batch-b251-b300.md`, `round5-batch-b251-b300-followup.md`,
`round5-batch-b271-b290.md`, `round5-batch-b271-b290-followup.md`,
`round5-batch-b301-b400.md`, `round5-batch-b301-b400-followup.md`,
`round5-batch-b325-b350.md`, `round5-batch-b351-b400.md`, `round5-batch-b351-b400-followup.md`,
`round5-batch-b401-b600.md`, `round5-batch-b401-b600-followup.md`,
`round5-batch-b482-b500.md`, `round5-batch-b482-b500-followup.md`,
`round5-batch-b551-b600.md`, `round5-batch-b551-b600-followup.md`,
`round5-batch-geom-stats.md`, `round5-batch-geom-stats-followup.md`,
`round5-batch-jn.md`, `round5-batch-jn-followup.md`,
`round5-batch-pgrand.md`, `round5-batch-pgrand-followup.md`

### 弱化・決着バッチ（10 ファイル）
`round5-batch-b001-b200-weak.md`, `round5-batch-b101-b200-weak.md`,
`round5-batch-b201-b300-weak.md`, `round5-batch-b251-b270-weak.md`,
`round5-batch-b325-b350-weak.md`, `round5-batch-b501-b600-weak.md`,
`round5-batch-weak-promote.md`, `round5-batch-final-43.md`,
`round5-batch-last21.md`, `round5-batch-b201-b500-final.md`

### 関連ドキュメント
`round5-FINAL-SUMMARY.md`（最終統合）, `round5-census-log.md`, `ROUND5-PROTOCOL.md`,
`round5-workplan.md`, `round5_n8_progress.md`, `round5-b141-corrections.md`

---

## 7. 更新履歴

- 00:45 初回（決着 300）
- 01:00 第2回（決着 304）
- 01:15 第3回（決着 307）
- 03:10 第4回（決着 308）
- 04:25 第5回（決着 312。B158 再反転）
- 05:45 第6回（決着 318）
- 10:30 第7回・第2波（決着 345）
- 11:25 第8回・第2波再統合（決着 382）
- 13:20 第9回・第3波（決着 468）
- 15:26 n=8 p_rand 完走
- **最終: 決着 600 / 600**（弱化昇格・final-43・last21 で全決着）
