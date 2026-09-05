# 9×9 pair component factorial population audit

最終更新: 2026-09-05

## 結論

`S00=T`, `S10=T+E`, `S01=T+O`, `S11=T+E+O` の2×2成分実験について、当初案の

> pilot 64件と confirmatory 1024件を除いた **11,378 raw-vs-T strict-disagreement D4代表**から新holdoutを作る

という標本設計は、そのままでは不適切。

11,378集合は事前に `S00 != S11` を満たすことを条件として作られている。ここから `S00 vs S10` や `S00 vs S01` の効果を評価すると、最初から「両成分を合わせると首位が変わる」局面へ条件付けされるため、E/Oの主効果・相互作用を測る母集団として選択バイアスが入る。

この問題は outcome を見る前、局所scoreだけから判明したので、factorial experimentの標本設計を修正する。ただし、既に事前固定済みの `T vs raw` confirmatory 1024件には一切変更を加えない。

## unbiased factorial population

9×9の全 safe 4-stone parents `1,634,588` を再走査し、4 scoreすべてが unique argmax を持つ親をまず選ぶ。

```text
S00 = T
S10 = T + E
S01 = T + O
S11 = T + E + O
```

この条件を満たす raw parents は:

```text
all four scores unique argmax:
1,103,124
```

そのうち4 scoreがすべて同じmoveを選ぶ親は成分比較に情報を持たないため、少なくとも1 scoreが別moveを選ぶ親だけを残す。

```text
at least one score chooses a different move:
40,884 raw parents
5,113 D4 canonical orbits
```

したがって、2×2成分実験の自然な一次母集団は **5,113 D4 canonical orbits**。

再現コード:

```bash
g++ -O3 -std=c++20 scripts/export-9x9-factorial-population.cpp -o /tmp/export-9x9-factorial-population
/tmp/export-9x9-factorial-population --csv /tmp/9x9-factorial-population.csv
```

## 各matched comparisonの母集団サイズ

4 scoreすべて一意首位という同じ条件下で、各比較が異なるmoveを選ぶD4 orbit数は:

```text
E effect with O off:
S00 != S10
4,435 orbits

O effect with E off:
S00 != S01
801 orbits

E effect with O on:
S01 != S11
4,331 orbits

O effect with E on:
S10 != S11
702 orbits

original endpoint:
S00 != S11
5,047 orbits
```

ここで `S00 != S11` が5,047で、以前のraw-vs-T strict population 11,378より小さいのは、今回のprimary factorial analysisでは `S10` と `S01` についても unique argmax を要求しているため。

## 新しい実験設計

factorial holdoutは11,378集合から作らず、上記5,113 canonical populationから作る。

ただし既に outcome を見た局面は除外する。

- pair-vs-mobility pilot 64件
- 現在の confirmatory 1024件
- その他、factorial score outcomeを事前に見た局面があればそれも除外

除外は `canonical_parent` だけで行い、outcomeやcauseを見て選別しない。

その後、残った5,113母集団から固定seedによる deterministic hash sampling を行う。

標本サイズを決める際は、4比較で情報量が大きく違う点に注意する。E比較は4千超のorbitを持つ一方、O比較は700〜800程度しかない。単純な全体無作為標本ではO効果のdiscordant例が少なくなり得る。

したがって実装上は、各比較について十分な対象数を確保するよう **comparison membershipによる事前層化**を行うのが合理的。ただし同一parentが複数比較へ属するため、child solveは共有できる。

## 重要な解釈

この監査で変わるのは後段のfactorial experimentだけ。

現在の1024件 `T vs raw` confirmatory testは、その問い

> raw pair rule と true one-ply mobility のどちらがstrict-disagreement局面でより良いか

に対して既に固定されており、そのまま完了させる。

一方、factorial experimentの問いは

> E/Oを個別にオン・オフしたときの主効果と条件付き効果は何か

なので、`T != raw` で事前条件付けされた集合を使わない。

この分離により、confirmatory testを壊さず、後段のE/O解析だけ選択バイアスを避けられる。

## machine-readable export

`scripts/export-9x9-factorial-population.cpp` は5,113 canonical parentsを次の列で出力する。

```text
canonical_parent
top_T
top_TE
top_TO
top_raw
diff_E_at_O0
diff_O_at_E0
diff_E_at_O1
diff_O_at_E1
```

各parentは4 scoreすべてunique argmaxで、少なくとも1 comparisonが異なるmoveを選ぶ。
