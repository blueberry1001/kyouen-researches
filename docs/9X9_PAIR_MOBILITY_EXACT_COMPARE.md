# 9×9 pair-sum vs true mobility: exact child-value comparison

最終更新: 2026-09-05

`docs/9X9_PAIR_MOBILITY_SCAN.md` で得た D4 canonical strict-disagreement parents を、ゲーム理論的な子局面値で直接比較するための次段実験。

## 実装

比較専用 solver:

```text
cpp/solvers/kyouen_solver_9_compare.cpp
```

CMake では `BUILD_RESEARCH_SOLVERS=ON` のとき

```text
kyouen-solver-9-compare
```

としてビルドされる。

入力は `scripts/analyze-9x9-pair-mobility.cpp --csv-prefix PREFIX` が生成するCSVをそのまま使う。

```text
canonical_parent,pair_top,true_unique_top
"0,1,6,50",30,57
...
```

各行について solver は

```text
parent + pair_top
parent + true_unique_top
```

の2つの5石rootだけを exact solve する。全候補を分類しないため、11,378 canonical parents なら最大22,756 root solveで endpoint 比較を行える。transposition memo は同一process内で共有する。

出力には両 child outcome、各rootで新規に訪問したstate数、solve秒数、累積memo使用量を記録する。

## arbitrary-root legality reconstruction

既存 `kyouen_solver_9.cpp` は空盤面または初手固定からの探索専用だったため、この比較solverでは arbitrary safe root から合法手maskを再構成する。

root occupied set `S` に対し、全3石部分集合 `T subset S` の completion mask をunionして

```text
danger(S) = union_{|T|=3} completion(T)
legal(S)  = board \ occupied(S) \ danger(S)
```

とする。

またroot自身が forbidden 4-setを含まないことを検査してから solve する。

## smoke exact result

最初の strict-disagreement example

```text
P = {0,1,6,50}
pair_top        = 30
true_unique_top = 57
```

を比較した。

局所scoreでは

```text
30: raw_pair=18, overlap-only union=16
57: raw_pair=17, overlap-only union=17
```

で raw pair と distinct coverage の順位が逆転する既知例。

exact child value は:

```text
P+30 : LOSS
P+57 : LOSS
```

したがってこの親では、局所評価の首位は異なるが、どちらの手も相手にLOSSを渡す winning move である。endpoint比較としては **非決着**。

machine-readable record:

```text
results/9x9/pair-vs-true-unique-smoke.csv
```

この1件は「pair ruleが勝った/true mobilityが勝った」と数えず、matched comparisonでは concordant success として除外する。

## 本実験の集計

各親について pair child と true-mobility child の outcome を比較し、LOSS child を望ましい手とする。

```text
A = #(pair child LOSS, true child WIN)
B = #(pair child WIN,  true child LOSS)
```

両方LOSSまたは両方WINは endpoint superiority の情報を持たないので、主検定ではdiscordant pair `A+B` のみ使う。

帰無仮説「両ruleの成功確率が同じ」では

```text
A | (A+B) ~ Binomial(A+B, 0.5)
```

なので exact binomial / matched sign test で比較できる。親ごとに候補数やLOSS密度が違っても、このendpoint比較自体はmatched designになっている。

## 次の実行順

1. `pair-vs-union.csv` の1,119 canonical parentsを先に流し、redundancyだけの価値を判別する。
2. 次に `pair-vs-true-unique.csv` の11,378 canonical parentsへ拡大する。
3. 各batchで `A`, `B`, both LOSS, both WIN を保存する。
4. discordant cases が得られたら、親の幾何・overcount・already-danger再加算量との関係を掘る。

特に、最初のsmoke caseが both LOSS だったことから、局所scoreの首位差がそのままgame-value差になるとは限らない。したがって全11,378件を闇雲に深掘りする前に、1,119のより純粋な実験で discordant rate を測る価値が高い。
