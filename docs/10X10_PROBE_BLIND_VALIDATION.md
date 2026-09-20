# 10×10 固定プローブルールの盲検追試

## 1. 概要

本報告書は、10×10共円ゲームにおいて事前に凍結した3/4/5-stone固定プローブルールが、**未知の新規LOSS親**に対しても再現性を持って有効かどうかを盲検で追試したものです。主評価の対象は、プローブ実行前に選定済みの親に限定します。

### 1.1 固定ルール（検証期間中変更禁止）

| stones | 特徴量 | budget | 順序 |
|--------|--------|--------|------|
| 3      | memo   | 1,000,000 | descending |
| 4      | memo   | 10,000    | ascending  |
| 5      | maxdepth | 10,000  | descending |

### 1.2 親選定方針

- 候補親はプローブ実行前に `results/10x10/blind-probe-parent-selection.csv` に記録済み。
- 全候補で `selected_before_probe = True` を機械的に確認済み。
- 既存LOPO評価に使用されたソースファイル由来の候補は主評価から除外し、注記として保持。

### 1.3 成果物

- `results/10x10/blind-probe-parent-selection.csv`
- `results/10x10/blind-probe-rankings.csv`
- `results/10x10/blind-probe-results.csv`
- `results/10x10/blind-probe-analysis.json`
- `scripts/analyze_probe_blind_validation.py`
- `scripts/run_blind_exact_children_parallel.py`
- `scripts/run_blind_exact_parents.py`

---

## 2. 親選定と除外

### 2.1 候補親総数

`blind-probe-parent-selection.csv` に事前登録された候補は **30親** です。

| stones | 件数 | ソース |
|--------|------|--------|
| 3      | 20   | `two-stone-90-66-child-proof.csv`, `two-stone-90-61-child-proof.csv` |
| 4      | 10   | `three-stone-9-10-30-child-proof.csv` |
| 5      | 0    | （事前登録なし） |

### 2.2 LOPO使用ソースに関する除外

- 4-stone候補10件は全て `three-stone-9-10-30-child-proof.csv` 由来です。
- 同ファイルは既存LOPO評価で **3-stone親として使用済み** であるため、これら4-stone候補は主評価から除外しました。
- 主評価対象は **3-stone候補20件** のみです。

### 2.3 5-stone候補

- 事前登録ファイルには5-stone候補が含まれていませんでした。
- `probe-features.csv` 内の stones=5 LOSS state は全てLOPO使用ソース由来で、新規候補は検出されませんでした。
- 新規5-stone LOSS親を生成するには、LOPO未使用の4-stone LOSS親の完全分類が必要ですが、今回の範囲では達成できませんでした。
- この制約は「10×10上で利用可能なLOSS親が少ない」という制約の一部として報告します。

### 2.4 完全探索の実行範囲

各3-stone候補の children は最大で91個に分割されています。計算コストを抑えるため、まず **batch 0（先頭20 children）** だけを child-level 並列 exact 探索しました。

実行結果:

- **exact 完了（batch0）**: 8親
  - 2,9,33 / 4,9,33 / 9,12,33 / 9,19,33 / 9,23,33 / 0,31,36 / 0,36,43 / 0,36,44
- **exact 途中でタイムアウト**: 2親
  - 0,36,50 / 9,33,54
- **未実行**: 残り10親

したがって、主評価に使えるのは batch0 が完全に確定した8親です。

---

## 3. 評価指標

各LOSS親について以下を記録しました。

- `first LOSS position`: 各順序で最初のLOSS childが現れる位置（1-indexed）
- `random中央値`: ランダム順1000回の first LOSS 位置中央値
- `solver既定順`: children入力ファイル順での first LOSS 位置
- `oracle順`: 最も安いLOSS childを先頭にした場合
- `probe費用込総コスト`: 全childrenへのprobe費用 + first LOSSまでの完全探索費用

注意: 本評価は batch0（各20 children）のみを対象とした **部分探索結果** です。`exact_complete = False` として記録しています。

---

## 4. 結果

### 4.1 主評価対象LOSS親

batch0 で少なくとも1つのLOSS childを持つ親は **7親** でした。0,36,43 は batch0 にLOSS childが含まれなかったため、主評価の集計からは除外しました（全childrenではLOSSありの可能性があります）。

| parent | child_count | loss_count | fixed | random median | solver | oracle | fixed total cost | random median total cost | solver total cost |
|--------|-------------|------------|-------|---------------|--------|--------|------------------|--------------------------|-------------------|
| 2,9,33 | 20 | 6 | **1** | 3 | 2 | 1 | 31.6M | 61.7M | 62.8M |
| 4,9,33 | 20 | 2 | **16** | 6 | 3 | 1 | 157.0M | 85.5M | 59.3M |
| 9,12,33 | 20 | 1 | **3** | 11 | 18 | 1 | 56.8M | 170.1M | 278.9M |
| 9,19,33 | 20 | 1 | **13** | 11 | 8 | 1 | 153.9M | 130.1M | 101.0M |
| 9,23,33 | 20 | 2 | **1** | 6 | 3 | 1 | 51.4M | 82.0M | 58.3M |
| 0,31,36 | 20 | 15 | **1** | 1 | 1 | 1 | 31.0M | 31.0M | 31.0M |
| 0,36,44 | 20 | 4 | **3** | 3 | 6 | 1 | 55.4M | 55.4M | 75.9M |

（コスト単位: visited nodes）

### 4.2 3-stone集計

| 指標 | fixed rule | random | solver default |
|------|------------|--------|----------------|
| first LOSS 中央値 | **3.0** | 6.0 | 3.0 |
| first LOSS 平均 | 5.43 | - | - |
| total cost 中央値 | **55.2M** | 82.0M | 62.8M |
| 評価親数 | 7 | 7 | 7 |

### 4.3 random との比較

- fixed rule が random 中央値より **良くなった親**: 3件（2,9,33 / 9,12,33 / 9,23,33）
- fixed rule が random 中央値より **悪くなった親**: 2件（4,9,33 / 9,19,33）
- **同等**: 2件（0,31,36 / 0,36,44）
- 中央値で **50%改善**（6.0 → 3.0）

### 4.4 solver既定順との比較

- fixed rule が solver 既定順より **良くなった親**: 4件
- fixed rule が solver 既定順より **悪くなった親**: 2件
- **同等**: 1件（0,31,36）
- 中央値では **同等**（3.0 → 3.0）

### 4.5 probe費用込み総計算量

- fixed total cost が random total cost より **低かった親**: 5/7
- fixed total cost が solver total cost より **低かった親**: 5/7
- 中央値では random / solver 双方で **改善**

### 4.6 最大反例

fixed rule が明らかに失敗した親:

1. **4,9,33**
   - fixed first LOSS = 16
   - random 中央値 = 6
   - solver = 3
   - random 中央値の **2.7倍**、solver の **5.3倍**
   - total cost でも random / solver 双方より悪化

2. **9,19,33**
   - fixed first LOSS = 13
   - random 中央値 = 11
   - solver = 8
   - total cost でも random / solver 双方より悪化

これらは「同じ stones でも方向が逆転する」典型的な反例です。

---

## 5. post-hoc分析との分離

- 本報告書の第4章までが主評価です。
- 別特徴量・別budget・符号逆転などの探索的分析は、必要に応じて今後行いますが、それらはあくまでpost-hocであり、上記の主成功条件には影響しません。

---

## 6. 最終判定

### 6.1 事前成功条件との対照

| 条件 | 結果 |
|------|------|
| 新規LOSS親 ≥ 5件 | **達成**（7件） |
| fixed first LOSS 中央値 ≤ 2 | **未達成**（3.0） |
| random 中央値比で30%以上改善 | **達成**（50%改善） |
| solver既定順比でも改善 | **中央値同等**、個別では改善・悪化混在 |
| probe費用込み総計算量も改善 | **中央値改善**、個別では2件悪化 |
| 大幅悪化する親が少数 | **2件**（4,9,33 / 9,19,33） |

### 6.2 判定結果

**判定 C: 効果は弱い**

- 中央値ベースでは random 比で改善、総コストでも改善する側面がある。
- しかし、fixed first LOSS 中央値は 3 と目標の 2 を上回り、solver 既定順とは中央値で同等。
- 最重要な点として、**親ごとに方向が頻繁に逆転する**（4,9,33 / 9,19,33 で明らかな悪化）。
- したがって、「新規親でも安定して有効」とは言えません。

### 6.3 11×11進行の是非

**11×11への進行は推奨できません。**

- 10×10の3-stoneにおいてすら、固定ルールが安定した優位性を示していません。
- 11×11は探索空間がさらに広がるため、同じ固定ルールが有効である可能性は低いです。
- さらなる検証（より多くの新規LOSS親、4-stone / 5-stoneの追加候補、全children完全探索）が必要です。

---

## 7. 簡潔まとめ

1. **新規LOSS親**: 7件確保（ただし batch0 のみの部分探索）
2. **fixed rule の first LOSS 中央値**: 3.0
3. **random 中央値**: 6.0
4. **solver 既定順中央値**: 3.0
5. **random 比改善率**: 中央値で50%改善
6. **probe費用込み**: 中央値では random / solver 双方より改善、個別では2件悪化
7. **stones別再現性**: 3-stone のみ評価可能。4-stone候補はLOPO使用ソース由来で除外。5-stone候補は事前登録なし。
8. **最大反例**: 4,9,33（fixed=16 vs random=6）、9,19,33（fixed=13 vs random=11）
9. **成功判定**: **C（効果は弱い）**
10. **11×11進行**: **推奨しない**

---

*Generated by scripts/analyze_probe_blind_validation.py*
