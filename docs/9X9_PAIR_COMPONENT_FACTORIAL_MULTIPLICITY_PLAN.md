# 9×9 pair component factorial experiment: multiplicity plan

最終更新: 2026-09-05

## 目的

後段の2×2成分実験では、局所score

```text
S00 = T
S10 = T + E
S01 = T + O
S11 = T + E + O
```

について、次の4比較を同時に評価する。

```text
E at O=0: S00 vs S10
O at E=0: S00 vs S01
E at O=1: S01 vs S11
O at E=1: S10 vs S11
```

標本集合は `9X9_PAIR_COMPONENT_FACTORIAL_HOLDOUT_DESIGN.md` で outcome 観測前に固定済み。

4比較から都合のよいものだけを主結果として選ぶことを避けるため、exact outcomeを見る前にfamily-wise inferenceを以下で固定する。

## 各比較の統計量

各parentについて、component absent側とcomponent added側のtop moveをexact solveする。

子局面outcomeが異なるparentだけをdiscordantとし、

```text
A = component added側だけがLOSS child
B = component absent側だけがLOSS child
n = A + B
```

とする。

LOSS childを作る手が現在手番側にとってwinning moveなので、`A/(A+B)` が0.5より大きければ追加成分側が有利、小さければ追加しない側が有利という向きになる。

ただし、このfactorial実験ではE/Oの効果方向を結果観測後に選ばないため、各比較の確認的p値は

```text
H0: P(component-added-only | discordant) = 0.5
H1: != 0.5
```

の**両側 exact binomial test**とする。

方向は `A` と `B` の大小、および `A/(A+B)` で報告する。

## 多重性

4つの両側exact p値を1つのfamilyとして扱い、

```text
Holm step-down procedure
family-wise alpha = 0.05
```

で補正する。

Holm法を選ぶ理由は、4つの解析集合がparentの重複を許し、検定統計量が独立とは限らないためである。Holm法はこの依存を仮定せずFWERを制御できる。

判定はHolm-adjusted p-valueが0.05未満かどうかで行う。

生p値も併記するが、生p値だけを使って「有意」と判定しない。

## E/Oの主張単位

4比較はそれぞれ独立した条件付き効果として報告する。

```text
E | O=0
E | O=1
O | E=0
O | E=1
```

例えば `E | O=0` だけが有意でも、「Eは一般に有効」とは直ちにまとめない。逆条件で同方向かどうかを併記する。

この段階では、

```text
(E | O=1) - (E | O=0)
(O | E=1) - (O | E=0)
```

の相互作用に対する追加の確認的p値は定義しない。解析集合が同一parentの完全なpaired 2×2ではないため、単純な差の差を確認的検定として後付けしないためである。

相互作用は記述的な差として観察できるが、新しい検定を行う場合は別holdoutで事前固定する。

## 実装

solver入力作成:

```text
scripts/prepare-9x9-factorial-solver-inputs.py
```

holdout CSVから4つの解析集合だけを取り出し、既存 `kyouen_solver_9_compare` が読める

```text
canonical_parent,pair_top,added_top
```

形式を生成する。

ここで `pair_top` はsolver互換の列名であり、factorial解析では「component absent側のtop move」を意味する。

集計・検定:

```text
scripts/analyze-9x9-factorial-outcomes.py
```

このscriptは、

- solver結果のparent集合が事前指定集合と完全一致するか
- absent/addedのmoveがholdout CSVと一致するか
- outcomeがWIN/LOSSのどちらかか

を検証してから、4比較のdiscordant counts、両側exact binomial p値、Holm-adjusted p値を出力する。

## 固定事項

outcome観測後に以下を変更しない。

- 4比較のfamily定義
- 両側検定
- family-wise alpha=0.05
- Holm補正
- discordant parentだけをexact binomial testの分母にすること
- component-added側をAとして記録する符号規約

また、現在進行中の `T vs raw` 1,024件confirmatory testは別の事前固定実験であり、このfactorial計画によって判定規則を変更しない。
