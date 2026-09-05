# 9×9 pair component factorial holdout design

最終更新: 2026-09-05

## 背景

4石親に対する局所scoreを

```text
S00 = T
S10 = T + E
S01 = T + O
S11 = T + E + O = raw pair
```

と分解する。

ここで

- `T`: candidateによって本当に新しく失われる safe response 数
- `E`: すでにdangerなresponseの再加算
- `O`: 同じ新規danger responseの重複加算

である。

全safe 4-stone parentsを走査し、4 scoreすべてがunique argmaxを持ち、少なくとも1 scoreが別moveを選ぶD4 canonical populationは5,113 orbits。

各matched comparisonの母集団は outcomeを見る前に次のように確定している。

```text
E effect with O off:  S00 != S10   4,435 orbits
O effect with E off:  S00 != S01     801 orbits
E effect with O on:   S01 != S11   4,331 orbits
O effect with E on:   S10 != S11     702 orbits
```

既存のpair-vs-mobility pilot 64件、confirmatory 1,024件など、すでにexact outcomeを観測したcanonical parentはこの後段実験から除外する。

## 標本配分

単純に5,113代表から同じ割合で抽出すると、O比較の対象が少なすぎて情報を捨てる。一方、O比較だけを過剰抽出したunionをE比較にもそのまま使うと、E比較の標本がcomparison membershipに条件付けされる。

この2問題を分離するため、各matched comparisonの解析集合を事前に別々に固定する。

```text
E at O=0 (S00 vs S10): eligibleから固定hashで最大1,024件
E at O=1 (S01 vs S11): eligibleから固定hashで最大1,024件
O at E=0 (S00 vs S01): eligible全件のcensus
O at E=1 (S10 vs S11): eligible全件のcensus
```

同一parentが複数集合に入る場合、exact child solve自体は共有してよい。ただし各比較の集計には、その比較用に事前指定された集合だけを使う。

これにより

- O効果では、利用可能な未観測情報を全て使う
- E効果では、O membershipによる過剰抽出を解析集合へ混ぜない
- solver workはunionで共有して削減する

を同時に満たす。

E比較の1,024という件数は、現confirmatory testと同程度の規模に固定し、後からoutcomeを見て変更しない。除外後にeligibleが1,024未満なら全件を用いる。

## deterministic selection

実装:

```text
scripts/select-9x9-factorial-holdout.py
```

固定seed:

```text
kyouen-9x9-pair-components-factorial-v1-2026-09-05
```

E比較では

```text
SHA256(seed || NUL || comparison_label || NUL || canonical_parent)
```

の昇順で選ぶ。`E0` と `E1` はlabelを分けるので、それぞれ独立した決定的抽出になる。

O比較はhashによる削減を行わず、除外後のeligible parentを全件採用する。

## 使用例

まず母集団を再生成する。

```bash
g++ -O3 -std=c++20 scripts/export-9x9-factorial-population.cpp \
  -o /tmp/export-9x9-factorial-population
/tmp/export-9x9-factorial-population \
  --csv /tmp/9x9-factorial-population.csv
```

その後、すでにoutcomeを観測したCSVをすべて `--exclude` で与える。

```bash
python3 scripts/select-9x9-factorial-holdout.py \
  /tmp/9x9-factorial-population.csv \
  /tmp/9x9-factorial-holdout.csv \
  --exclude results/9x9/pair-vs-true-unique-pilot-64-input.csv \
  --exclude /tmp/9x9-confirmatory-1024.csv
```

confirmatory 1,024件は、事前固定済みの既存selectorから同じものを再生成して除外してよい。保存済みCSVがある場合は、再生成物と一致を確認する。

出力CSVには元の4 top moveとcomparison membershipに加えて

```text
sample_E_at_O0
census_O_at_E0
sample_E_at_O1
census_O_at_E1
```

を保存する。

`.manifest.csv` には各比較のeligible/selected件数を保存する。

## 主な解析単位

各比較で2つのtop moveが異なることは母集団定義から保証される。exact solve後、子局面のoutcomeが異なるparentのみをdiscordantとする。

各比較について

```text
left-only LOSS
right-only LOSS
both LOSS
both WIN
```

を数える。

primary quantityはdiscordant parent中で成分を追加した側がLOSS childを選ぶ割合。ただし、このfactorial experimentは現在固定済みの`T vs raw` confirmatory testとは別実験であり、その主判定を変更しない。

4比較を同時に推論する場合の多重性処理は、exact outcomeを見る前に別途固定する。少なくとも、生の4つのp値から都合のよいものだけを主結果として選ばない。

## 禁止事項

- outcomeを見てE標本1,024件を選び直さない
- O censusから不都合なparentだけ除外しない
- 既観測parentをholdoutへ戻さない
- union solveに含まれたという理由だけで、そのparentを全4比較の解析に使わない
- 現在の1,024件 `T vs raw` confirmatory testの設計をこの後段計画に合わせて変更しない

この設計は、5,113母集団に修正したpopulation auditの次段として固定する。
