# 10×10 探索量 vs 勝敗：全確定局面検証

## 要約・結論

10×10の既存確定局面全体を使って「LOSSは探索量が大きいか」を検証した。

* **結論分類：B（弱いが実用的な相関がある）**
* 同じ深さ・同じ親の children で比較すると、LOSS の探索量は中央値で明らかに大きい。
* しかし分布の重なりは巨大で、探索量だけでは完全分離できない。
* 「重いほどLOSS」は 69,91 の特殊な状況だけではないが、全体としては弱い指標。
* 11×11では「重い候補を優先する」探索順序の参考にはなるが、単純な閾値予測は使えない。

## 使用データ

`scripts/analyze_search_cost.py` が以下を統合して `results/10x10/search-cost-outcomes.csv` を生成する。

| ファイル | 内容 |
|---|---|
| `results/10x10/two-stone-69-91-child-proof.csv` | 69,91 の 98 children（3 LOSS / 95 WIN） |
| `results/10x10/two-stone-61-66-child-proof.csv` | 61,66 の children |
| `results/10x10/two-stone-90-66-child-proof.csv` | 90,66 の children |
| `results/10x10/two-stone-90-61-child-proof.csv` | 90,61 の children |
| `results/10x10/three-stone-9-10-30-child-proof.csv` | 9,10,30 の children |
| `results/10x10/three-stone-subsets-of-medium-loss.csv` | 8-stone medium LOSS の 3-stone subsets |
| `results/10x10/four-stone-subsets-of-medium-loss.csv` | 4-stone subsets |
| `results/10x10/five-stone-subsets-of-medium-loss.csv` | 5-stone subsets |
| `results/10x10/six-stone-subsets-of-medium-loss.csv` | 6-stone subsets（shared-memo batch） |
| `results/10x10/seven-stone-subsets-of-medium-loss.csv` | 7-stone subsets |
| `results/10x10/*-loss-proof-*.csv` | 独立証明済み LOSS の再測定値 |
| `results/10x10/69-91-expanded-memo.csv` | expanded-memo による再探索 |
| `results/90-69-heavy-three-stone-results.csv` | 90-69 campaign の parents / seeds |
| `results/90-69-split-proof.csv` | split 証明 parents + children |
| `docs/10X10_PROOF_BENCHMARKS.md` | 8-stone / 14-stone benchmark |

座標は `id = y*10+x`。勝敗は手番側から見た outcome（WIN/LOSS）。

使用 solver コミット： `3ab84cee8a138102c648209b81a93e4f9a7bd301`。
expanded-memo（v3/v4）や targeted-v1/v2 はメモ容量のみ変更し、探索ロジック・手順序・対称性削減は同一。

## データ除外・フラグ

`search-cost-outcomes.csv` には以下のフラグ列を付与している。

* `has_search_cost`：`visited > 0` の行。直接勝ち（DIRECT_*）や split 親など `visited` がない局面は `False`。
* `memo_runtime_reliable`：`shared_memo=False` かつ `visited>0`。shared-memo batch では `memo` や `runtime` が累積値のため比較対象外。
* `shared_memo`：batch 共有メモリ実行。`visited` は root ごとの新規訪問数だが `memo`/`runtime` は累積。

`TABLE_FULL` や timeout で途中終了した値は、確定後の値があればそちらを採用し、未確定のままの行は含めていない。

## データセット概要

| 項目 | 値 |
|---|---|
| 全確定局面 | 988 |
| WIN | 953 |
| LOSS | 35 |
| `visited > 0` | 693（WIN 661 / LOSS 32） |
| reliable memo/runtime 行 | 655（WIN 628 / LOSS 27） |
| 直接勝ち等 `visited=0` | 295（WIN 292 / LOSS 3） |

## 基本分布

### visited

| outcome | count | min | 25% | median | mean | 75% | 90% | 95% | max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| WIN | 661 | 2 | 5.70M | 8.74M | 27.9M | 19.1M | 62.7M | 127.7M | 603.7M |
| LOSS | 32 | 10,471 | 9.56M | 12.6M | 123.5M | 19.0M | 630.6M | 822.4M | 827.8M |

### memo（reliable 行のみ）

| outcome | count | min | 25% | median | mean | 75% | 90% | 95% | max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| WIN | 628 | 1 | 6.00M | 9.19M | 29.3M | 20.1M | 66.4M | 130.0M | 602.8M |
| LOSS | 27 | 24,499 | 11.0M | 14.3M | 145.1M | 24.1M | 713.3M | 822.8M | 826.7M |

### runtime（reliable 行のみ）

| outcome | count | min | 25% | median | mean | 75% | 90% | 95% | max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| WIN | 628 | 0.0s | 14.6s | 24.7s | 90.0s | 60.0s | 236.7s | 447.9s | 1802s |
| LOSS | 27 | 1.0s | 18.8s | 23.9s | 373.9s | 41.2s | 1832s | 2447s | 2474s |

中央値では LOSS がやや重いが、分散が極めて大きい。特に LOSS の平均は中央値の約 10 倍あり、上位 3 局面（69,91 の LOSS children）が支配している。

## 分布の重なり・反例

| 指標 | 値 |
|---|---|
| 最も軽い LOSS | `90,61,2,73,69,66,13,91`、visited = 10,471（8-stone benchmark） |
| 最も重い WIN | `1,39,80`、visited = 603,662,904 |
| max(WIN) > min(LOSS) | はい |
| WIN で min(LOSS) より重い数 | 656 / 661 |
| LOSS で max(WIN) より軽い数 | 28 / 32 |

**最大の反例**：`1,39,80` は 603,662,904 訪問の WIN で、69,91 の 3 つの LOSS children（~819M–828M）に次ぐ重さ。つまり「600M 級の超重病」でも WIN は存在する。

69,91 の children だけで見ると LOSS は突出して重いが、全体では WIN の重い tail に大量の反例がある。

## 閾値による予測

`visited >= T` を LOSS 候補とした場合：

| threshold | 上位% | precision | recall | FP | FN | TP |
|---:|---:|---:|---:|---:|---:|---:|
| 8,999,426 | 50% | 7.2% | 78.1% | 322 | 7 | 25 |
| 19,094,374 | 25% | 4.6% | 25.0% | 166 | 24 | 8 |
| 27,030,124 | 20% | 5.0% | 21.9% | 132 | 25 | 7 |
| 38,634,098 | 15% | 4.8% | 15.6% | 99 | 27 | 5 |
| 65,777,799 | 10% | 7.1% | 15.6% | 65 | 27 | 5 |
| 131,916,886 | 5% | 13.9% | 15.6% | 31 | 27 | 5 |
| 505,550,558 | 1% | 57.1% | 12.5% | 3 | 28 | 4 |

上位 1% に絞れば precision は 57% になるが recall は 12.5%。
上位 5% では precision 14%、recall 16%。
単純閾値は実用に耐えない。

## 順位としての性能

visited が大きい順に並べたときの LOSS 累積回収率：

| 上位 | 件数 | LOSS 回収数 | recall | ランダム期待 | 濃縮倍率 |
|---|---:|---:|---:|---:|---:|
| 1% | 6 | 4 | 12.5% | 0.28 | 14.4× |
| 5% | 34 | 5 | 15.6% | 1.57 | 3.2× |
| 10% | 69 | 5 | 15.6% | 3.19 | 1.6× |
| 20% | 138 | 7 | 21.9% | 6.37 | 1.1× |

上位 1% で 14 倍濃縮できるが、上位を広げると急速に効果が薄れる。全体の LOSS の大半はそこそこの探索量で発生する。

## visited 以外の指標

* `memo` は `visited` とほぼ比例（`memo/visited` ≒ 0.998）。勝敗分離には役立たない。
* `visited/second` は実装・マシン・profile に強く依存する。同じ solver 内では WIN/LOSS に大差は見られなかった。
* 最大 bucket 使用率は `69-91-expanded-memo.csv` に個別に記録されている。v4 profile では d13a が 99.7% だったが、これは capacity bound の証拠であり勝敗予測には使えない。

## 深さ（石数）の影響

| stones | WIN 数 | LOSS 数 | WIN median | LOSS median | min LOSS | max WIN |
|---:|---:|---:|---:|---:|---:|---:|
| 3 | 287 | 5 | 21.2M | 819.2M | 504.6M | 603.7M |
| 4 | 311 | 12 | 7.37M | 15.1M | 9.56M | 35.4M |
| 5 | 29 | 11 | 0.33M | 11.1M | 7.40M | 5.62M |
| 6 | 25 | 3 | 0.17M | 0.47M | 0.43M | 0.45M |
| 7 | 8 | 0 | 8,937 | — | — | 24,847 |

* 3-stone：LOSS は圧倒的に重い（中央値 819M vs WIN 21M）。ただし max WIN 603M は min LOSS 504M を超える。
* 4-stone：重なりが大きい。max WIN 35.4M > min LOSS 9.6M。
* 5-stone：**重なりなし**。max WIN 5.6M < min LOSS 7.4M。同じ深さでは LOSS が必ず重い。
* 6-stone：サンプル少ないが、max WIN 451k と min LOSS 433k でわずかに重なる。

したがって「LOSS は重い」は深さによって強さが大きく変わる。全体を混ぜると相関は弱まる。

## 親ごとの比較

| parent | children | WIN | LOSS | WIN median visited | LOSS median visited | WIN max visited | LOSS max visited |
|---|---:|---:|---:|---:|---:|---:|---:|
| 69,91 | 98 | 95 | 3 | 42.5M | 826.4M | 603.7M | 827.8M |
| 3,19,90 | 97 | 97 | 0 | 8.01M | — | 29.1M | — |
| 9,10,30 | 96 | 96 | 0 | 6.25M | — | 35.4M | — |
| 9,29,30 | 97 | 97 | 0 | 7.23M | — | 20.7M | — |

69,91 では LOSS children が突出。他の LOSS parents（3,19,90 / 9,10,30 / 9,29,30）の children はみな WIN で、親が LOSS でも子はそこまで重くない。同じ親内での比較は強い相関を示すが、それは 69,91 という特定の親に強く依存している。

## 統計検定

visited 分布の WIN/LOSS 差について Mann-Whitney U 検定（ノンパラメトリック、両側）：

* U = 13150
* p = 0.020
* 効果量（rank-biserial r）= -0.24

p は 0.05 未満だが、効果量は小さい。LOSS は平均的にやや重いが、分布の重なりが支配的。

## 可視化

`results/10x10/analysis/` に以下を出力した。

| ファイル | 内容 |
|---|---|
| `visited_distribution.png` | WIN/LOSS の visited 分布（log10 ヒストグラム） |
| `visited_sorted_scatter.png` | visited 小さい順の散布図 |
| `visited_boxplot.png` | outcome 別 log10(visited) 箱ひげ図 |
| `memo_vs_visited.png` | memo vs visited 散布図 |
| `loss_recall_by_rank.png` | 探索量順位に対する LOSS 累積回収率 |

## 11×11への応用可能性

結論 B なので、以下のように使うのが現実的：

1. **初期短時間プローブ**：各候補を数秒〜数分だけ走らせ、visited や memo の増加速度を測る。
2. **成長速度指標**：最終 visited は探索後にしか分からない。最初の数秒間の `visited/sec` や `memo/sec` の伸びを特徴量にする。
3. **重い候補優先**：同じ深さの候補群で上位 1〜5% を先に探索すれば、LOSS を数倍濃縮できる可能性がある。
4. **計算資源配分**：明らかに軽い候補は後回しにし、重そうな候補にコアを割く。

次段階の研究案：

* 探索開始後の最初の数秒〜数分で測れる特徴（visited/sec、memo/sec、depth 別 bucket 使用率の上昇、ノードあたりの分岐数）から、最終探索量と LOSSLikelihood を回帰・分類する。
* これができれば、11×11 で「完全探索後の visited」を未来予測に置き換えられる。

## 未確定事項・限界

* LOSS 件数が 35 と少なく、統計的検定の一般化は限られる。
* 5-stone / 6-stone で「LOSS は必ず重い」傾向が見られたが、サンプル数は少ない。
* runtime は環境依存が大きい。ここでは同じ solver 内の相対比較に留めた。
* いくつかの LOSS parents（9,10,30 など）は split 証明により確定しており、単一の `visited` がない。これらを含めると「LOSS は軽い」反例がさらに増える。

## 最終報告

1. **LOSSは本当に重いのか？** → 平均・中央値ではやや重いが、完全分離はできない。
2. **差はどの程度か？** → 中央値で 1〜2 桁、分布の重なりは巨大。効果量 r ≈ -0.24（小さい）。
3. **探索量だけで予測できるか？** → いいえ。単純閾値は precision が低い。
4. **最大の反例？** → `1,39,80`（WIN、603.7M visited）は LOSS children に匹敵する重さ。
5. **11×11で使えるか？** → 探索優先順位の参考にはなる（上位 1% で 14 倍濃縮）。ただし最終 visited は使えず、初期成長速度に置き換える必要がある。
6. **次にやるべき最も情報価値の高い実験？** → 各候補を短時間プローブし、最初の数秒〜数分の特徴から最終探索量と LOSSLikelihood を予測するモデルを作る。
