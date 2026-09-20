# 10×10 共円ゲーム: stones別プローブ規則の Leave-One-Parent-Out 汎化検証

## 要約・結論

**結論分類: D（汎化しない）〜 C（一部stonesのみ条件付き汎化）**

先行研究で報告された「stones別最適指標により first LOSS 位置が 2.6 → 1.2 に改善」という結果は、**同じデータから後付けでルールを選んでいたため楽観的に見えていた**。厳密な Leave-One-Parent-Out（LOPO）評価では、**未知の親局面に対して stones別に最適特徴量を選ぶ手法はランダムより悪化する**。

| 指標 | Data-all 後付け | LOPO stones別選択 | 単純固定ルール |
|---|---|---|---|
| first LOSS 位置 平均 | **1.0** | **4.88** | **1.0** |
| first LOSS 位置 中央値 | 1.0 | 1.0 | 1.0 |
| ランダム中央値 平均 | — | 2.25 | 2.25 |

- **Data-all 後付け**: 全親を使って stones 別ルールを決めると、first LOSS 位置平均は 1.0（2.6 → 1.2 と同等の楽観値）。
- **LOPO stones別選択**: 未知の親で特徴量・budget・方向を学習データだけから選ぶと、first LOSS 位置平均は **4.88** とランダム期待値 2.61、ランダム中央値 2.25 を大幅に上回る。**改善した親: 12.5%、悪化: 25%、同等: 62.5%**。
- **単純固定ルール**: 全学習 fold で多数決したルール（3-stone→1M memo desc、4-stone→10k memo asc、5-stone→10k maxdepth desc）では first LOSS 位置平均 1.0 と再現するが、これは 3/4/5-stone それぞれ LOSS 親が 2 つしかなく、両方が偶然同じ方向を持っていることに依存しており、**サンプルが極めて少ないため不安定**。

**4-stone の逆相関**は、LOSS を含む唯一の親（`four-stone-subsets-of-medium-loss.csv`）では memo と最終 visited の相関がほぼゼロ（ρ≈0.00）であり、LOSS の有無との相関は強く負（ρ≈-0.57）だった。つまり「4-stone で memo が小さいほど最終探索が重い」という仮説 A は支持されず、現象は **仮説 B（少数親の偏り）と C（探索構造由来の見かけ）の混合** と考えられる。

**総コスト評価**も LOPO stones別選択ではランダムより悪化（平均で 69% 増）。これは `four-stone-subsets` で first LOSS が 19 番目に来るなど、プローブ順位が逆効果になったケースによる。

**最終判定**: 11×11 への stones別最適特徴量のそのままの投入は**見送るべき（D）**。ただし、**単純固定ルールは限定的ながら有望な兆候（C）を示しているため、10×10 で LOSS 親サンプルを増やして固定ルールの安定性を確認する実験には価値がある**。

---

## 1. 目的

先行研究（コミット `2b88131`、報告書 `docs/10X10_PROBE_PREDICTION.md`）では、stones 別にプローブ特徴量を選ぶことで first LOSS 発見位置が random 2.6 から 1.2 へ改善すると報告された。しかしこの「最適ルール」は全データを見てから決めた後付け選択であり、未知の親局面に対する汎化性能は不明だった。

本研究では以下を厳密に検証する。

1. **Leave-One-Parent-Out (LOPO) 評価**: 評価親を 1 つ丸ごと除外し、残りの親だけで stones 別ルールを決定して未知の親へ適用。
2. **データ漏洩の排除**: 評価親の情報を一切使わず、特徴量・probe budget・順位方向を学習親だけで決定。
3. **ランダム基準**: 各親について 1000 回シャッフルしたランダム順と比較。
4. **単純固定ルールの評価**: 学習 fold で安定して良かった単純ルールを作り、未知親で評価。
5. **4-stone 逆相関の再検証**: 未知の親でも memo と final visited が負の相関になるか確認。
6. **コスト評価**: probe 費用 + LOSS 発見までの完全探索コストを含めた評価。

---

## 2. 方法

### 2.1 データ

- 入力: `results/10x10/probe-features.csv`
- 局面数: 655（重複排除済み）
- 親局面（`parent`）数: 14
- 評価対象 probe budget: 10k / 100k / 1M（5M は先行研究と同じく除外）
- LOSS を含む親: 8（表 1）
- LOSS 局面数: 27（各 budget で 81 行）

表 1: LOSS を含む親局面とその stones

| 親局面 | 子局面数 | LOSS 数 | stones |
|---|---|---|---|
| `10X10_PROOF_BENCHMARKS.md` | 2 | 1 | 8, 14 |
| `69-91-expanded-memo.csv` | 4 | 3 | 3 |
| `five-stone-loss-proof-61-2-73-13-91.csv` | 1 | 1 | 5 |
| `five-stone-subsets-of-medium-loss.csv` | 28 | 7 | 5 |
| `four-stone-loss-proof-61-73-66-13.csv` | 1 | 1 | 4 |
| `four-stone-subsets-of-medium-loss.csv` | 35 | 11 | 4 |
| `six-stone-loss-proof-90-61-2-73-69-66.csv` | 1 | 1 | 6 |
| `three-stone-subsets-of-medium-loss.csv` | 26 | 2 | 3 |

重要な制約: 3-stone、4-stone、5-stone の LOSS 親はそれぞれ **2 つ** しかない。これにより LOPO で 1 つを除くと学習側には **1 つしか LOSS 親が残らず**、ルール選択の統計力が極めて低い。

### 2.2 LOPO プロトコル

各親 `P` を評価親とする fold で以下を実施。

1. `P` の全子局面を学習から完全除外。
2. 残りの親だけで、各 stones について最適な `(特徴量, probe budget, 方向)` を選択。
   - 選択指標: LOSS を含む学習親における **first LOSS 位置の平均**（小さい方が良）。
   - 同点時: 中央値 → top-20% LOSS recall。
3. 選ばれたルールを `P` の子局面に適用し、first LOSS 位置を計測。
4. ランダム順 1000 回、oracle 順（final_visited desc）、単純固定ルールともに比較。

機械的な検証: 同一 `state` が複数 `parent` に属することを assert。全 state は 1 つの親のみに属していた。

### 2.3 固定ルールの作り方

各 LOPO fold で学習側が選んだ stones 別ルールを記録し、各 stones について最も頻繁に選ばれた `(特徴量, budget, 方向)` を「固定ルール」とした。これを別途 LOPO 評価したため、評価親のデータは固定ルールの決定に使われていない。

---

## 3. 主結果

### 3.1 全体集計

表 2: first LOSS 位置の比較

| 手法 | 平均 | 中央値 | 25%点 | 75%点 | 最小 | 最大 |
|---|---|---|---|---|---|---|
| Data-all 後付け | 1.00 | 1.00 | 1.00 | 1.00 | 1 | 1 |
| **LOPO stones別選択** | **4.88** | **1.00** | **1.00** | **4.25** | **1** | **19** |
| ランダム中央値 | 2.25 | 1.00 | 1.00 | 2.25 | 1 | 8 |
| ランダム期待値 | 2.61 | 1.13 | 1.00 | 3.16 | 1 | 9 |
| Oracle | 1.00 | 1.00 | 1.00 | 1.00 | 1 | 1 |
| 単純固定ルール | 1.00 | 1.00 | 1.00 | 1.00 | 1 | 1 |

**LOPO stones別選択はランダム期待値 2.61、ランダム中央値 2.25 を大きく上回る 4.88** となった。先行研究の「2.6 → 1.2」は再現されなかった。

表 3: ランダム中央値との比較

| 比較 | 件数 | 割合 |
|---|---|---|
| 改善（probe < random 中央値） | 1 | 12.5% |
| 悪化（probe > random 中央値） | 2 | 25.0% |
| 同等 | 5 | 62.5% |

### 3.2 Data-all Baseline との比較

全親を使って stones 別ルールを選び、同じ親に適用するという「後付け」手続きでは、first LOSS 位置平均は **1.0** となった。これは先行研究の 2.6 → 1.2 と同じくらい楽観的な値であり、**LOPO と Data-all の差が大きいことで、後付け選択による情報漏洩の影響が大きいことを示している**。

---

## 4. stones 別結果

### 4.1 3-stone

| 手法 | 平均 first LOSS 位置 | ランダム中央値 | 評価親数 |
|---|---|---|---|
| LOPO stones別選択 | 7.50 | 4.50 | 2 |
| 固定ルール (1M memo desc) | 1.00 | 4.50 | 2 |

- `69-91-expanded-memo.csv`: LOPO でも固定ルールでも first LOSS 位置 1（成功）。
- `three-stone-subsets-of-medium-loss.csv`: LOPO は 10k budget を選び memo desc で位置 14 と大きく悪化。しかし 1M budget では memo desc が位置 1 となる。**budget の選択が不安定**。

### 4.2 4-stone

| 手法 | 平均 first LOSS 位置 | ランダム中央値 | 評価親数 |
|---|---|---|---|
| LOPO stones別選択 | 10.00 | 1.50 | 2 |
| 固定ルール (10k memo asc) | 1.00 | 1.50 | 2 |

- `four-stone-subsets-of-medium-loss.csv`: LOSS は低 memo 側に集中。LOPO は学習親が 1 つ（`four-stone-loss-proof...`）しかないため tie-break で memo desc を選び、**first LOSS 位置 19** と壊滅的に悪化。固定ルール memo asc では位置 1。
- `four-stone-loss-proof...`: LOPO でも固定ルールでも位置 1（自明）。

### 4.3 5-stone

| 手法 | 平均 first LOSS 位置 | ランダム中央値 | 評価親数 |
|---|---|---|---|
| LOPO stones別選択 | 1.00 | 2.00 | 2 |
| 固定ルール (10k maxdepth desc) | 1.00 | 2.00 | 2 |

5-stone は両親で LOPO も固定ルールも成功。ただし学習親が 2 つしかなく、かつ `five-stone-loss-proof...` は子が 1 つだけなので統計力は低い。

---

## 5. ルール選択の安定性

表 4: 各 stones で最も頻繁に選ばれたルール（学習 fold 内）

| stones | 最頻特徴 | 最頻 budget | 最頻方向 | 選択頻度 / 全 fold |
|---|---|---|---|---|
| 3 | memo | 1M | desc | 13/14 (92.9%) |
| 4 | memo | 10k | asc | 13/14 (92.9%) |
| 5 | maxdepth | 10k | desc | 13/14 (92.9%) |
| 6 | memo | 10k | desc | 13/13 |
| 8 | memo | 10k | desc | 13/13 |

**解釈**: 一見するとルール選択は非常に安定しているように見える。しかしこの「安定性」は、多くの fold で学習側の LOSS 親が 1 つしかなく、どのルールでも first LOSS 位置が 1 になるケースが多数あるため、**形式的な安定性**に過ぎない。実際に未知親へ適用すると方向を誤るケースが発生した（4-stone）。

---

## 6. 4-stone 逆相関の検証

### 6.1 仮説

- **仮説 A**: 4-stone 一般に、初期 memo 成長が遅い局面ほど最終探索が重い。
- **仮説 B**: 少数の親局面が全体相関を逆転させているだけ。
- **仮説 C**: 探索順序・memo 構造由来の見かけの現象。

### 6.2 結果

4-stone 子局面を持つ親は 3 つしかない（表 5）。

表 5: 4-stone 親別 memo 相関（budget 100k）

| 親局面 | n_children | n_loss | memo vs final visited ρ | memo vs LOSS ρ | LOSS median memo | WIN median memo |
|---|---|---|---|---|---|---|
| `three-stone-9-10-30-child-proof.csv` | 96 | 0 | -0.18 (p=0.075) | — | — | 99842 |
| `90-69-split-proof.csv` | 191 | 0 | -0.04 (p=0.54) | — | — | 99841 |
| `four-stone-subsets-of-medium-loss.csv` | 35 | 11 | **+0.00** (p=0.98) | **-0.57** (p<0.001) | 99525 | 99721 |

集計:

- memo vs final visited が負の親: 2/3（66.7%）
- 平均 ρ: -0.074
- LOSS を含む唯一の親では ρ≈0
- LOSS 局面の memo 中央値は WIN よりも低い（差約 200）

### 6.3 判定

**仮説 A は支持されない**。LOSS を含む親では memo と final visited は無相関であり、「memo が小さい → 探索が重い」という構造的関係は確認できなかった。ただし、LOSS 局面は memo が小さい傾向があり（memo vs LOSS ρ≈-0.57）、これは探索が早期に打ち切れる特殊構造を反映している可能性がある。

**仮説 B と C の混合**が最も妥当: WIN-only の 2 親で軽い負の相関が出ていること、LOSS 親では相関がゼロであることから、全体の負の相関は主に WIN-only 親の偏りと探索構造の影響と考えられる。

---

## 7. プローブ費用込み評価

評価指標: `全 child への probe 費用 + first LOSS 発見までの完全探索費用`（visited 相当）。

表 6: コスト比較（平均 / 中央値）

| 手法 | 平均コスト | 中央値コスト |
|---|---|---|
| LOPO probe + 完全探索 | 397,453,763 | 11,347,609 |
| Random + probe | 275,989,568 | 12,067,448 |
| Random probe なし | 275,362,009 | 11,922,448 |
| Oracle + probe | 193,466,842 | 13,234,638 |

- LOPO stones別選択はランダムより平均で **69% コスト増**（中央値では同程度）。
- これは `four-stone-subsets` で first LOSS が 19 番目に来るため、18 個の WIN を完全探索するコストが膨大になったため。
- probe 費用自体（平均 約 40 万 visited）は最終探索に対して小さいが、**順位が悪いとその効果を大きく上回る損失**を生む。

コスト改善率（random 総コストに対する削減率）:

- 平均: **-69%**（悪化）
- 中央値: 0%
- 改善した親: 2/8（25%）

---

## 8. 反例

### 8.1 最大の悪化例

| 親 | stones | LOPO first LOSS 位置 | random 中央値 | 選ばれたルール | 悪化幅 |
|---|---|---|---|---|---|
| `four-stone-subsets-of-medium-loss.csv` | 4 | 19 | 2 | 10k memo desc | +17 |
| `three-stone-subsets-of-medium-loss.csv` | 3 | 14 | 8 | 10k memo desc | +6 |

`four-stone-subsets` では、学習側が 1 つの LOSS 親しかなかったため tie-break で memo desc が選ばれたが、実際の LOSS は低 memo 側にあった。結果として first LOSS が最下位近くまで追いやられ、完全探索コストが約 2.77 億 visited に達した。

### 8.2 符号が逆転する例

- 4-stone: 学習親 `four-stone-loss-proof...`（1 LOSS）では memo asc/desc どちらでも first LOSS 位置 1 となり、方向が決まらない。実際の未知親 `four-stone-subsets` では正しい方向は asc だったが LOPO は desc を選択。
- 3-stone: `69-91-expanded-memo` と `three-stone-subsets` では同じ memo desc 方向だが、**budget が異なれば** 効果が逆転する。10k では `three-stone-subsets` で悪化、1M では改善。

### 8.3 4-stone 逆相関が成立しない例

`four-stone-subsets` では memo と final visited の相関が ρ≈0 であり、仮説 A（低 memo → 重い探索）は成立しない。LOSS はむしろ低 memo であり、探索が軽く終わる構造を持つ。

---

## 9. 成功判定

| 選択肢 | 判定 | 理由 |
|---|---|---|
| A 強く汎化 | ✗ | LOPO でランダリより悪化。 |
| B 弱く汎化 | △ | 単純固定ルールは平均 1.0 と良いが、サンプルが少なすぎて信頼できない。 |
| C 一部 stones のみ | △ | 5-stone は良好、3-stone/4-stone は不安定。 |
| D 汎化しない | ○ | **LOPO stones別最適選択は明確に汎化しない**。 |

**総合判定: D（汎化しない）に近いが、単純固定ルールの可能性を完全に否定するデータでもない**。したがって 11×11 への即座の投入は見送り、10×10 でさらに LOSS 親サンプルを増やして固定ルールの安定性を検証すべき。

---

## 10. 限界

1. **LOSS 親の数が極めて少ない**: 3/4/5-stone それぞれ 2 親しかないため、LOPO 後の学習側は 1 親のみ。これでは方向選択の統計力がない。
2. **nested CV は不可能**: inner LOPO を行うには各 stones あたり最低 3 つの LOSS 親が必要だが、現データでは満たしていない。
3. **子局面の偏り**: 一部の親（`four-stone-subsets`、`three-stone-subsets`）は多くの子を持ち、他は 1 子のみ。重み付けを考慮していない。
4. **元の solver 順位が不明**: ランダム基準のみで比較。元の探索順があればさらに実用的な比較が可能。

---

## 11. 次に最も情報価値が高い実験

1. **10×10 で LOSS 親サンプルを増やす**: 特に 3-stone と 4-stone で、同じ stones の LOSS 親を 5〜10 個集める。これがあれば LOPO の統計力が飛躍的に向上する。
2. **固定ルールの追試**: 現時点の固定ルール（3→1M memo desc、4→10k memo asc、5→10k maxdepth desc）を新たに集めた未知親で盲目的に適用し、first LOSS 位置を測る。
3. **4-stone の構造解析**: なぜ LOSS が低 memo で終わるのか、maxdepth や early cut-off の有無、探索木の形状を調べる。
4. **11×11 の最小検証（固定ルールのみ）**: もし 10×10 で固定ルールが追加サンプルでも安定するなら、11×11 の 1 親だけを使った stones別 fixed-rule 検証を行う。

---

## 12. 成果物

- `scripts/analyze_probe_lopo.py`: LOPO 評価スクリプト（再実行可能）。
- `results/10x10/probe-lopo-results.csv`: 各 fold・各親の結果。
- `results/10x10/probe-lopo-analysis.json`: 集計結果、ルール安定性、4-stone 分析、コスト分析、反例。
- `docs/10X10_PROBE_LOPO.md`: 本報告書。
