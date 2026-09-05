# 9×9 pair-sum vs true mobility: first 12 exact comparisons

最終更新: 2026-09-05

`pair-vs-true-unique` strict-disagreement parents の列挙順先頭12件を exact solve した初期結果。

全12件はD4 canonical orientationのままで、相互に同一orbitへ潰れないことを確認した。

## 結果

子局面 outcome は「その手を打った後、次の手番側から見た値」。したがって **LOSS child を作る手が望ましい**。

集計:

```text
pair LOSS, true LOSS : 7
pair WIN,  true WIN  : 3
pair LOSS, true WIN  : 1   # pair-only success
pair WIN,  true LOSS : 1   # true-only success
```

つまり:

```text
decisive / discordant parents = 2 / 12
pair-only wins                 = 1
true-mobility-only wins        = 1
```

最初のdiscordant例:

```text
P={0,1,2,16}
pair_top=9       -> child WIN
true_unique=64   -> child LOSS
```

ここでは真の one-ply safe-response reduction 側だけが winning move。

逆向きの反例も直後に存在する:

```text
P={0,1,2,18}
pair_top=27      -> child LOSS
true_unique=58   -> child WIN
```

ここでは raw pair-sum 側だけが winning move。

## 解釈

この小標本だけで優劣は決めない。ただし重要な否定結果が得られた。

> raw pair-sum を true one-ply mobility に置き換えれば単調に改善する、という仮説は成立しない。

すでに両方向のdiscordant caseがあるため、pair側が数えている redundancy / already-danger 再加算の一部は、少なくとも一部局面では deeper game-tree structure の有用なproxyになっている可能性がある。

一方、true mobilityだけが正しい局面も存在するので、raw pair ruleも支配的ではない。

したがって次段では単純な endpoint replacement より、

```text
raw pair = true_unique
         + already-danger re-count
         + duplicate-new-response overcount
```

の2種類の余剰成分を分け、どちらがdiscordant方向と相関するかを調べる価値が高い。

## machine-readable result

```text
results/9x9/pair-vs-true-unique-first12.csv
```

この12件は探索的pilotとして扱い、本比較の統計検定には事前に固定した全canonical setまたは独立batchを使う。
