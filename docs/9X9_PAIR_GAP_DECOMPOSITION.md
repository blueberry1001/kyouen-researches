# 9×9 pair score gap decomposition

最終更新: 2026-09-05

`raw pair-sum` と「相手の safe response を実際に何個減らすか」の差には、性質の違う2種類の過大評価が混ざっている。

4石親 `P`、safe candidate `v` について、親の各2石ペアが作る response 集合を `W_ab(v)`、親局面ですでに danger な点集合を `B(P)` とする。次を定義する。

```text
U(v) = union_{ab subset P} W_ab(v)
T(v) = |U(v) \ B(P)|
E(v) = |U(v) cap B(P)|
O(v) = sum_ab |W_ab(v)| - |U(v)|
```

ここで

- `T`: candidate によって新たに失われる safe responses。真の one-ply mobility reduction。
- `E`: すでに danger だった response をもう一度評価している分。
- `O`: 同じ response を複数の親ペアで重複評価している分。

したがって fixed rule の raw score は厳密に

```text
raw_pair = T + E + O
```

と分解できる。

再現コード:

```bash
g++ -O3 -std=c++20 scripts/analyze-9x9-pair-gap-decomposition.cpp -o /tmp/pair-gap
/tmp/pair-gap
```

## 全数結果

9×9 の safe 4-stone parents 全1,634,588件、safe parent-candidate pairs 全117,253,740件を走査した。

```text
O > 0                         8,595,588 =  7.33076%
E > 0                        23,589,996 = 20.1188%
E > 0 and O > 0              5,107,224 =  4.3557%

max O = 3
max E = 9
max(E+O) = 9
```

候補単位では、重複 `O` よりも「すでに危険な点を再評価する」`E` の方が約2.74倍頻繁に発生する。

`raw_pair` と `T` がともに一意首位で、しかも別の手を選ぶ親は90,988件。この90,988件で pair winner `p` と true winner `t` を比較した。

```text
pair winner が E advantage を持つ     87,332 / 90,988 = 95.9819%
pair winner が O advantage を持つ     61,364 / 90,988 = 67.4419%

T+E だけで pair winner が逆転できる   53,476 / 90,988 = 58.7726%
T+O だけで pair winner が逆転できる    8,344 / 90,988 =  9.17044%
両方がそれぞれ単独で十分               2,696 / 90,988 =  2.96303%
E と O の両方が必要                    31,864 / 90,988 = 35.0200%
```

最後の4分類は、`E-only`, `O-only`, `both`, `synergy` とすると raw 90,988件では

```text
E-only   = 50,780
O-only   =  5,648
both     =  2,696
synergy  = 31,864
```

D4 canonicalization 後の11,378 orbitsでは:

```text
E-only   = 6,350
O-only   =   706
both     =   337
synergy  = 3,985
```

したがって `pair-sum -> true mobility` の差を「重複 witness の問題」だけで説明するのは不十分。主成分は既存 danger の再評価 `E` であり、さらに約35%は `E` と `O` が組み合わさって初めて首位を逆転する。

## 4石では O <= 3 は経験則ではなく上限

4石親を `{a,b,c,d}` とする。同じ response `w` が2つの `W` 集合に入るには、その2つの親ペアは disjoint でなければならない。親点を共有する2ペア、例えば `{a,b}` と `{a,c}` が同じ `w` を持つと、`a,v,w` を通る円または直線の一意性から `b,c` も同じ円/直線上に乗り、`P+v` がすでに forbidden になってしまう。

したがって重複し得る組は

```text
ab | cd
ac | bd
ad | bc
```

の3つの perfect matching だけ。

さらに固定した1つの matching、例えば `ab | cd` を考える。`W_ab(v)` は `a,b,v` を通る円または直線上の候補点、`W_cd(v)` も同様である。2つの幾何学的軌跡はともに `v` を通る。もし同一なら親 `{a,b,c,d}` 自体が forbidden なので、safe parent では必ず異なる。異なる2円、円と直線、または2直線は、既知の共通点 `v` 以外には高々1点しか共有できない。

よって各 matching が生む追加重複は高々1。

```text
O <= 1 + 1 + 1 = 3
```

全数走査で `max O = 3` が実現しているので、この上限は9×9上で sharp。

## redundancy 補間の候補は連続無限個ではない

`union = T+E` とし、重複 `O` の価値だけを補間する

```text
F_alpha = union + alpha O,  0 <= alpha <= 1
```

を考える。4石では `O in {0,1,2,3}`、`union` は整数なので、2候補の順位が区間内部で入れ替わる点は

```text
alpha = 1/3, 1/2, 2/3
```

しか存在しない。

したがって redundancy の価値を探索する際、任意の細かい alpha grid は不要。順位は、tie を除けば

```text
(0,1/3), (1/3,1/2), (1/2,2/3), (2/3,1)
```

の4区間で不変である。

ただしこれは `O` 軸だけの性質で、`raw_pair` と真の `T` の補間全体にはそのまま使えない。`E` は最大9まで取り得るため、完全な分解は

```text
F(alpha,beta) = T + beta E + alpha O
```

と考える方が自然。

```text
T             = F(0,0)
union=T+E     = F(0,1)
raw_pair      = F(1,1)
```

となる。

## exact game-value pilot

11,378 D4 orbitsを `E-only / O-only / both / synergy` に分け、各型について canonical key の小さい順から16件、計64件を選ぶ deterministic pilot を行った。各親について `pair_top` と `true T top` を置いた5石子局面を exact solve した。

LOSS child は親側から見て desirable move である。

```text
class       pair-only LOSS   true-only LOSS   both LOSS   both WIN
E-only            2               3              7          4
O-only            4               2              6          4
both              1               9              3          3
synergy           3               5              2          6
---------------------------------------------------------------
total            10              19             18         17
```

勝敗が異なる29件だけを見ると `true T top` が有利なケース19、`pair top` が有利なケース10。等確率を帰無仮説とした片側 exact binomial は約 `p=0.0680`。

これは**予備結果**であり、canonical key の小さい順という非無作為標本、かつ各型を16件ずつ等重みで取っているため、全11,378 orbitsへの推定値としては使わない。方向としては true mobility 優勢を示すが、まだ確定的ではない。

次の本試験では、11,378 orbitsから原因型ごとに無作為抽出または全件solveし、親ごとの matched comparison と exact binomial/McNemar 型集計を使う。まず discordant child outcomes だけで `pair` と `T` のどちらが実際に LOSS child を多く拾うかを比較する。
