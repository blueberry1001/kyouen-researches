# 9×9 pair-sum / mobility exhaustive scan

最終更新: 2026-09-05

この文書は、4石親における two-stone-subset additive score と one-ply mobility の差を、再現可能な全数走査で整理したもの。

再現コード:

```bash
g++ -O3 -std=c++20 scripts/analyze-9x9-pair-mobility.cpp -o /tmp/analyze-9x9-pair-mobility
/tmp/analyze-9x9-pair-mobility --csv-prefix /tmp/9x9
```

## 1. 重要な用語分離

4石親 `P` と safe candidate `v` に対して、親の各2石ペア `{a,b}` から生じる response set を `W_ab(v)` とする。

このとき3つの量を区別する必要がある。

```text
raw_pair(v) = sum_{pairs ab subset P} |W_ab(v)|
union(v)    = | union_{ab} W_ab(v) |
true_unique(v)
            = | (union_{ab} W_ab(v)) \ existing_danger(P) |
```

- `raw_pair`: two-stone subset の単純加算。重複を複数回数える。
- `union`: 同じ response の重複だけ除く。
- `true_unique`: さらに、その親局面ですでに danger だった response を除く。これは candidate `v` によって**新たに失われる safe responses の実数**。

以前の follow-up note で `S_mob` と呼んでいた 14.7528% の全数値は、厳密には `union` との比較であり、`true_unique` との比較ではなかった。以後この2つを混同しない。

## 2. 全数走査の基本検算

走査は 9×9 / 81点、4点共円または4点共線を整数行列式0で forbidden とする。

```text
forbidden 4-sets                 29,152
safe 4-stone parents          1,634,588
safe parent -> candidate     117,253,740
```

`C(81,4) - 29,152 = 1,634,588` なので親数も整合する。

## 3. raw pair vs overlap-only union

既報値を再現した。

```text
candidate raw > union                 8,595,588 / 117,253,740
                                      = 7.330758064%
maximum raw-union overcount           3

argmax set differs                  241,148 / 1,634,588
                                      = 14.752830683%
top sets completely disjoint         10,824 / 1,634,588
                                      = 0.662185211%
both unique max, different moves       8,952 / 1,634,588
                                      = 0.547660940%
D4 canonical strict-disagreement       1,119 orbits
```

したがって、以前の `1,119 canonical representatives` は正しく再現した。ただしこれは

> raw pair-sum vs **overlap-only union**

を識別する集合である。

## 4. raw pair vs true one-ply safe-response reduction

既存 danger も除いた `true_unique` と比較すると差はかなり大きくなる。

```text
candidate raw > true_unique          27,078,360 / 117,253,740
                                      = 23.093813468%
maximum raw-true_unique gap            9

argmax set differs                  453,802 / 1,634,588
                                      = 27.762469809%
top sets completely disjoint        122,224 / 1,634,588
                                      = 7.477358209%
both unique max, different moves      90,988 / 1,634,588
                                      = 5.566417960%
D4 canonical strict-disagreement      11,378 orbits
```

これは重要な修正。

4石以降で fixed rule が one-ply mobility の近似としてずれる原因は、

1. 同じ新規danger responseを複数pairが重複して数えること
2. すでにdangerだったresponseをもう一度scoreに加えること

の両方である。

しかも全数では2番目の影響が大きく、`raw pair` と真の one-ply safe-response reduction の首位集合は **27.76%** の4石親で異なる。

## 5. 実験優先順位の修正

ゲーム理論的に

- two-stone additive score が効くのか
- 本当に相手のsafe responsesを減らすことが効くのか

を比較したいなら、優先すべき対象は `1,119` ではなく、原則として

```text
11,378 D4 canonical parents
```

の `raw pair vs true_unique` strict-disagreement 集合。

ただし計算コストを抑える初段として、以下の二段階に分ける価値がある。

1. 1,119件: **redundancyだけ**の価値を判別する。
2. 11,378件: redundancy + already-danger overcount を含む、raw fixed rule と真の one-ply mobility の総合差を判別する。

前者は「同じresponseへの複数witnessに深い価値があるか」というきれいな構造実験、後者は「実際のfixed ruleを改善するならどちらが良いか」という実用実験になる。

## 6. CSV出力

再現コードに `--csv-prefix PREFIX` を渡すと、D4正準化した strict-disagreement parents を出力する。

```text
PREFIX-pair-vs-union.csv
PREFIX-pair-vs-true-unique.csv
```

列は

```text
canonical_parent,pair_top,union_top
canonical_parent,pair_top,true_unique_top
```

で、任意初期局面を直接 solve する次段実験へそのまま投入できる。

## 7. 研究上の解釈

3石親では既存dangerへの再加算もpair間重複も起きないため、fixed pair-sum は真の one-ply mobility と一致する。

4石で初めてこの同値性が壊れる。

したがって現在の最も明確な境界は、

```text
3 stones:
  pair-sum == true one-ply safe-response reduction

4+ stones:
  pair-sum != true one-ply safe-response reduction in general
```

である。

10×10既存分類で4石WINから5石LOSSへ進む証人手がmobility順位から大きく外れる例もあるため、`true_unique` に直せばゲーム理論的評価まで解決するとは限らない。今回の結果はまず、**局所評価として何を実際に測っているかを正確に分離した**ものとして扱う。
