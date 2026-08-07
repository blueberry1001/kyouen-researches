# 10×10 共円ゲーム: 短時間プローブによる最終探索量・LOSS 予測

## 要約・結論

**結論分類: C（条件付き成果）〜 D（否定的成果）**

短時間プローブ（10k〜1M visited）で 10×10 確定局面全体の最終探索量や LOSSLikelihood を一様に高精度に予測することは**できなかった**。しかし、**石数（stones）別に特徴量を選べば一部の局面集合で強い相関・高速化効果があり、11×11 以降の運用に価値がある可能性はある**。

### 主要結果

* **最終 visited 予測**: 単一指標 `depth_visited_3`（root から 3 手先の visited）が最も相関が高く（Spearman ≈ 0.57）、予測不能ではないが、線形モデルでは CV R² が負で実用的な絶対値予測はできない。
* **LOSS ランキング**: プローブ `memo` の上位 1%（100k budget）で precision 50%、LOSS 濃縮倍率 12 倍を達成。上位 5% 以上では急速に効果が薄れる。
* **親単位高速化**: 全局面に一律の指標を使うと、**ランダム順よりも悪化する**（memo 順で first LOSS position 4.4 vs random 2.6）。しかし **stones 別に指標を選べば 100k/1M budget で random 2.6 → 1.2** と大幅に改善する。
* **プローブ費用**: 100k budget は最終探索量の約 0.3% で済み、1M budget でも約 2.8%。
* **stones 別差**: 極めて大きい。
  * **3-stone**: `memo` と最終 visited が正の相関（ρ ≈ 0.71）、LOSS ランキングにも有効。
  * **4-stone**: `memo` が**負の相関**（ρ ≈ -0.25）。`depth_visited_3` を使う必要がある。
  * **5-stone**: `memo` と最終 visited が非常に強い正の相関（ρ ≈ 0.94）、LOSS ランキングも強い。
* **11×11 への適用可能性**: 限定的。stones 別モデルが必要で、4-stone では別の指標が必要。全体モデルとしては持ち込む価値は低いが、5-stone など特定の深さでは強力。

---

## 1. 使用データ

### 1.1 データソース

`scripts/analyze_probe_features.py` は前回の `results/10x10/search-cost-outcomes.csv` を入力とし、`scripts/collect_probe_features.py` を通じて WSL 上の `scripts/probe_cert_solver` を実行してプローブ特徴量を収集する。

### 1.2 988 行と主分析対象 693 件の内訳

前回の `search-cost-outcomes.csv` は 988 行だったが、今回の主分析対象は **655 局面**（1965 プローブ行）に絞った。

| 項目 | 件数 | 備考 |
|---|---|---|
| search-cost-outcomes.csv 合計 | 988 | 重複・未確定を含む |
| 前回主分析 WIN+LOSS | 693 | 完全な `visited` 値を持つ確定局面 |
| **今回主分析対象** | **655** | 重複排除・未確定除外後の確定局面 |
| うち LOSS | 81 | 全体の 12.4% |
| うち WIN | 574 | |

除外理由:

* 重複する `state`（複数の親 CSV に跨って記録）を 1 つに集約。
* `final_visited` が欠損・未確定・split 証明由来の局面を除外。
* 14 の親グループに所属する 655 局面を対象とした。

### 1.3 親グループと LOSS 分布

| 親グループ | 局面数 | LOSS 数 | 主な stones |
|---|---|---|---|
| `four-stone-subsets-of-medium-loss.csv` | 35 | 11 | 4 |
| `five-stone-subsets-of-medium-loss.csv` | 28 | 7 | 5 |
| `69-91-expanded-memo.csv` | 4 | 3 | 3 |
| `three-stone-subsets-of-medium-loss.csv` | 26 | 2 | 3 |
| `10X10_PROOF_BENCHMARKS.md` | 2 | 1 | 8〜14 |
| その他個別 LOSS proof | 3 | 3 | 4〜6 |
| LOSS を含まない親 | 555 | 0 | 3〜7 |

LOSS を含む親グループは **8 つ** と少なく、親単位評価の統計力には限界がある。

---

## 2. プローブ方法

### 2.1 使用ソルバー

* `scripts/probe_cert_solver.cpp` — `kyouen_solver_10_kyoenc4.cpp` をベースに、指定 visited budget で探索を停止し、統計を CSV 出力するプローブ専用ソルバー。
* 探索順序・カットオフ・判定ロジックは元の完全探索ソルバーと同一。
* 停止条件: `visited >= probe_budget` または早期打ち切り（win/loss/table full）。

### 2.2 プローブ条件

| budget | 平均 1 局面あたり秒数 | 655 局面合計秒数 | final visited に対する割合 |
|---|---|---|---|
| 10,000 | 0.09 s | 61 s | 0.03% |
| 100,000 | 0.43 s | 282 s | 0.29% |
| 1,000,000 | 3.48 s | 2280 s | 2.84% |
| 5,000,000 | （200 局面のみ実行、参考値） | — | — |

5M budget は 200/655 局面で 1 時間かかり、コストが高すぎるため主分析から除外した。

### 2.3 再現性

同じ局面・同じ budget を 2 回実行した結果、**visited, memo, maxdepth, depth_visited_x, memo_used_x, memo_capacity_x は完全一致**。唯一 `seconds` のみ CPU 負荷等で変動する。したがって、時間以外の特徴量は決定論的に再現可能である。

---

## 3. 特徴量

`probe-features.csv` に記録した主な特徴量:

| 特徴量 | 説明 |
|---|---|
| `state` | 局面（カンマ区切り） |
| `parent` | 親 CSV / 親局面 |
| `stones` | 石数 |
| `outcome` | WIN / LOSS（正解ラベル、特徴量には使わない） |
| `probe_budget` | プローブ budget |
| `visited` | プローブ時点の総探索ノード数 |
| `memo` | プローブ時点の memo エントリ数 |
| `seconds` | プローブ経過時間 |
| `maxdepth` | 最大到達深さ |
| `memo_per_visited` | memo / visited |
| `visited_per_second` | visited / second |
| `depth_visited_0` 〜 `depth_visited_19` | 深さ別 visited 数 |
| `memo_used_d9` 〜 `memo_used_d21` | 深さ別 memo 使用量 |
| `memo_capacity_d9` 〜 `memo_capacity_d21` | 深さ別 memo bucket 容量 |

---

## 4. 単一指標の相関分析

### 4.1 最終 visited との Spearman 相関（全体）

| budget | 1 位指標 | Spearman | p 値 |
|---|---|---|---|
| 10k | `depth_visited_3` | 0.57 | < 1e-50 |
| 100k | `depth_visited_3` | 0.57 | < 1e-50 |
| 1M | `depth_visited_3` | 0.57 | < 1e-50 |

`depth_visited_3` は budget に依存せず常に最も強く、root から 3 手先の探索量が最終探索量の大きさを反映している。これは直感に反するが、「root 直下の分岐が多い・再訪問が多い」局面ほど最終的に重くなることを示唆する。

### 4.2 LOSS との Spearman 相関（全体）

| budget | 1 位指標 | Spearman |
|---|---|---|
| 10k | `memo` | 0.13（弱い正） |
| 100k | `memo` | 0.13 |
| 1M | `memo` | 0.12 |

全体では LOSS との相関は弱い。ただし上位 1% の濃縮性能は高い。

---

## 5. 最終探索量の予測

### 5.1 線形回帰モデル（GroupKFold by parent）

| budget | CV R² | CV Spearman |
|---|---|---|
| 10k | -1.19 | -0.15 |
| 100k | -2.59 | -0.05 |
| 1M | -1.94 | 0.10 |

線形モデルでは実用的な予測はできない。

### 5.2 上位重探索局面の回収率

`depth_visited_3` でソートし、最終 visited 上位 k% の回収率:

| budget | top 1% recall | top 5% | top 10% | top 20% |
|---|---|---|---|---|
| 10k | 低 | 低 | 中 | 中 |
| 100k | 低 | 低 | 中 | 中 |
| 1M | 低 | 中 | 中 | 中 |

上位 1% の重い局面を回収するのは難しく、順位予測の精度は限定的。

---

## 6. LOSS ランキング性能

### 6.1 全体: `memo` によるランキング

| budget | top 1% precision | recall | 濃縮倍率 |
|---|---|---|---|
| 10k | 33% | 7.4% | 8.1× |
| **100k** | **50%** | **11.1%** | **12.1×** |
| 1M | 33% | 7.4% | 8.1× |

100k budget の `memo` 上位 1% は最も濃縮度が高く、全体 LOSS 率 12.4% を 50% まで 12 倍濃縮できる。

### 6.2 全体: `depth_visited_3` によるランキング

上位に LOSS が**ほぼ入らない**（precision ≈ 0%）。最終 visited 予測には強いが、LOSS ランキングには向かない。

### 6.3 stones 別 LOSS ランキング

| stones | 指標 | top 20% precision | recall | 濃縮倍率 |
|---|---|---|---|---|
| 3 | memo (1M) | 8.6% | 100% | 5.0× |
| 4 | depth_visited_3 | 1.6% | 4.2% | 0.4× |
| 5 | memo (10k) | **80%** | **50%** | **2.9×** |
| 5 | memo (100k/1M) | 60% | 38% | 2.2× |

* **5-stone**: 極めて強い。上位 20% で precision 60〜80%。
* **4-stone**: `memo` では全く役立たず、`depth_visited_3` でも弱い。
* **3-stone**: memo 上位 20% で recall 100% だが precision は低い。

---

## 7. 親単位での実用評価

各 LOSS を含む親について、children の探索順を比較。

### 7.1 一律指標 `memo`

| budget | random | memo 順 | oracle |
|---|---|---|---|
| 10k | 2.6 | 6.8 | 1.0 |
| 100k | 2.6 | 4.4 | 1.0 |
| 1M | 2.6 | 2.8 | 1.0 |

**memo 順はランダムより悪い**。特に 10k/100k で顕著。

### 7.2 一律指標 `depth_visited_3`

| budget | random | depth_visited_3 順 | oracle |
|---|---|---|---|
| 10k〜1M | 2.6 | 2.6 | 1.0 |

ランダムと同等。

### 7.3 stones 別最適指標（3,5→memo、4→depth_visited_3）

| budget | random | best feature | oracle |
|---|---|---|---|
| 10k | 2.6 | 3.4 | 1.0 |
| **100k** | **2.6** | **1.2** | **1.0** |
| **1M** | **2.6** | **1.2** | **1.0** |

**100k/1M budget で stones 別に指標を選べば、first LOSS position が 2.6 → 1.2 と半減**する。

注意: この「best feature」はデータ全体から決定しており、完全な Leave-One-Parent-Out 汎化評価ではない。親グループが少ないため、stones 別のルールを学習するのに必要な親数が不十分である。ただし、4-stone で memo が逆効果になる傾向は強く、複数の独立データから確認できる。

---

## 8. プローブ費用込みの評価

仮に「全局面をプローブし、その後 `memo` 上位 20% を完全探索する」戦略をとった場合の計算量見積もり:

| budget | プローブ visited | 完全探索 visited (上位 20%) | 合計 visited | 削減率 | 含まれる LOSS の割合 |
|---|---|---|---|---|---|
| 10k | 6.5M | 2,969M | 2,976M | **86.7%** | 25.9% |
| 100k | 64.6M | 3,830M | 3,894M | **82.6%** | 29.6% |
| 1M | 634M | 3,982M | 4,617M | **79.3%** | 37.0% |

計算量は大幅に削減できるが、上位 20% に入る LOSS は 26〜37% に留まる。**約 60〜75% の LOSS を見逃すリスクがある**。親 WIN を証明するには「すべての LOSS child を見つける」必要があるため、この戦略では不十分。

---

## 9. stones 別モデル

### 9.1 memo vs final visited の Spearman

| budget | 3-stone | 4-stone | 5-stone |
|---|---|---|---|
| 10k | 0.67 | -0.35 | 0.80 |
| 100k | 0.71 | -0.25 | 0.84 |
| 1M | 0.82 | -0.21 | **0.94** |

### 9.2 解釈

* **5-stone**: memo が非常に強い指標。最終 visited 予測も LOSS 予測も可能。
* **3-stone**: memo は正の相関。LOSS は少ないが、重い局面を一定程度予測可能。
* **4-stone**: **memo が逆の指標**になる。これは、4-stone の LOSS 局面が「探索が浅く終わる特殊な構造」を持つことに起因すると考えられる。4-stone では `depth_visited_3` や他の特徴を使う必要がある。

---

## 10. 主な反例

| タイプ | 例 | 説明 |
|---|---|---|
| 重いプローブ・軽い最終 WIN | `1,3,29,90` | 100k で probe memo 上位 5% だが、最終 visited は 5.6M（下位） |
| 軽いプローブ・重い最終 LOSS | `8,17,30` | 100k で probe memo 下位 5% だが、最終 visited は 819M（上位） |
| 4-stone で指標が逆 | four-stone-subsets | memo 順で first LOSS が 18（random=2）と大きく悪化 |

これらの反例は、単一指標では全局面をカバーできないことを示す。

---

## 11. 11×11 への外挿と適用可能性

### 11.1 現時点での評価

10×10 での結果を 11×11 にそのまま適用するのは**危険**。理由:

* 4-stone では指標が逆になる。
* 全体モデルでは親単位高速化できない。
* memo bucket 容量等、実装依存の特徴が 11×11 で通用するとは限らない。

### 11.2 有望な運用案

特定の条件を満たす場合に限定して使う:

1. **5-stone の children**: `memo` で強力に LOSS を濃縮できるため、優先探索に使える。
2. **3-stone の children**: `memo` 上位 20% で LOSS recall 100% を達成するため、候補絞り込みに使える。
3. **4-stone の children**: `depth_visited_3` を試すが、現時点では信頼性が低い。

### 11.3 11×11 で最初にすべき最小規模検証案

1. 11×11 の 1 つの親局面を選び、children を 3-stone, 4-stone, 5-stone に分類。
2. 各 stones について、10×10 と同じ指標（memo / depth_visited_3）でプローブ。
3. 短時間プローブ（10k〜100k）で LOSSLikelihood 順位を作り、ランダム順・oracle 順と比較。
4. 10×10 と同じ傾向が出るか（特に 5-stone で memo が有効か）確認。

---

## 12. 限界

* **LOSS サンプル数が少ない**: 81 件（全体の 12.4%）。
* **親グループ数が少ない**: LOSS を含む親は 8 つ。親単位の統計検定力は低い。
* **5M/10M budget のデータなし**: 1M 以上のプローブでは結果が変わる可能性がある。
* **best feature 選択の汎化**: stones 別ルールはデータ全体から見つけたもので、完全な LOPO 評価ではない。
* **実装依存の特徴**: `memo_capacity_d*` は現在の固定サイズのメモリ構造由来。11×11 では無意味になる可能性がある。

---

## 13. 成果物

### データ

* `results/10x10/probe-features.csv` — 655 局面 × 3 budget のプローブ特徴量
* `results/10x10/probe-analysis.json` — 数値結果

### スクリプト

* `scripts/probe_cert_solver.cpp` — visited budget プローブソルバー
* `scripts/collect_probe_features.py` — プローブ特徴量収集スクリプト
* `scripts/analyze_probe_features.py` — 分析スクリプト

### 可視化

* `results/10x10/probe_analysis/memo_vs_final_budget_*.png`
* `results/10x10/probe_analysis/spearman_by_budget.png`
* `results/10x10/probe_analysis/loss_concentration_memo.png`
* `results/10x10/probe_analysis/memo_vs_final_by_stones_budget_*.png`
* `results/10x10/probe_analysis/parent_speedup_budget_*.png`

---

## 14. 最終報告

1. **最も有効なプローブ特徴量**: 全体では `depth_visited_3`（最終 visited 予測）と `memo`（LOSS ランキング）。stones 別では 3,5→`memo`、4→`depth_visited_3`。
2. **最小限のプローブ**: 100k visited budget で十分。10k では不安定、1M では改善が限定的。
3. **final visited 順位予測**: 単一指標で Spearman 0.57 まで。線形モデルでは実用的でない。
4. **LOSS 濃縮**: 100k `memo` 上位 1% で **12 倍濃縮**（precision 50%）。ただし上位 5% 以上では急速に低下。
5. **ランダムより総計算量削減**: 全局面をプローブ + 上位 20% 完全探索で **約 80% 削減**可能だが、約 60〜75% の LOSS を見逃す。
6. **stones 別差**: 極めて大きい。5-stone で ρ≈0.94、4-stone では負の相関。
7. **最大の反例**: 4-stone で `memo` 順が random より悪化（first LOSS position 18 vs 2）。
8. **11×11 への価値**: 限定。5-stone 等特定の stones であれば有望だが、全体モデルとしては持ち込まない方が安全。
9. **次に行うべき実験**:
   * 11×11 の 1 親局面で stones 別に同じ指標が有効か確認。
   * 4-stone でなぜ `memo` が逆効果になるか、局面構造を調査。
   * 5M/10M budget を重い局面のサブセットで実行し、長いプローブの限界を確認。
   * Leave-One-Parent-Out で stones 別ルールの汎化性能を検証。
