# Two-stone probe follow-up notes — 2026-09-05

この文書は [`9X9_TWO_STONE_PROBE_RESEARCH_NOTES.md`](./9X9_TWO_STONE_PROBE_RESEARCH_NOTES.md) の追補である。既存メモに入っていなかった、その後の解析・訂正・10×10既存分類から得た補助知見を記録する。

## 1. 3石で fixed rule と solver primary key は独立ではない

3石親 `P={a,b,c}` で safe candidate `v` を考える。親3ペア由来の新規 danger-response 集合は互いに素なので、

```text
S_pair(v) = s_ab(v) + s_ac(v) + s_bc(v)
```

は、相手の次の safe response を何個消すかに厳密一致する。

既存 exact solver の候補順序も、候補 `v` 後に残る safe-response set の大きさを昇順に並べるのが primary key である。したがって3石では、

```text
maximize S_pair(v)
<=> minimize opponent safe responses after v
```

であり、fixed rule と solver default ordering は primary key が数学的に同じである。

よって blind replication の

```text
fixed median = 3
solver median = 3
```

を「独立な2手法が一致した証拠」とは扱わない。random に対する改善は依然意味があるが、fixed と solver の一致自体は独立検証ではない。

## 2. random first-LOSS rank は LOSS 密度で補正する

親に候補が `m` 個、そのうち LOSS 子が `l` 個あるとき、random ordering で最初の LOSS が rank `R` に現れる分布は

```text
P(R > r) = C(m-r, l) / C(m, l)
E[R] = (m+1)/(l+1)
P(R <= r) = 1 - C(m-r, l)/C(m, l)
```

である。

今後は単純な random median だけでなく、親ごとに

- `m`: candidate count
- `l`: LOSS-child count
- fixed rank
- solver rank
- `E[R]`
- `q = P(R <= fixed_rank)`

を記録する。これにより親ごとの LOSS 密度の差を補正できる。

## 3. 4石以降: pair-sum と exact mobility の差の一般式

親 `P`、candidate `v` に対し、各親ペア `{a,b}` が新たに danger にする response 集合を `W_ab(v)` とする。

3石ではこれらは互いに素だが、4石以上では disjoint parent pairs に由来する集合が重なり得る。

各 response `w` の multiplicity を

```text
m_w = #{ parent pair {a,b} | w in W_ab(v) }
```

と置くと、

```text
S_pair = sum_w m_w
S_mob  = sum_w [m_w > 0]
O      = sum_w max(0, m_w - 1)
S_pair = S_mob + O
```

となる。

- `S_pair`: raw two-stone-subset additive score
- `S_mob`: 実際に新しく消す distinct safe responses の数
- `O`: redundancy / overcount

同じ `w` に寄与する親ペアは互いに disjoint でなければならないため、

```text
m_w <= floor(|P|/2)
```

である。4〜5石では `m_w<=2`、6石で初めて triple overlap が可能。

実現例として、6石親

```text
P = {2,3,9,10,21,45}, v=0, w=1
```

では `(2,3)`, `(9,10)`, `(21,45)` の3つの disjoint pairs が同じ response `w=1` を danger にし、`m_w=3` を達成する。

## 4. 9×9・全4石親の exhaustive disagreement scan

9×9 の safe 4-stone parents 全体を走査した結果:

```text
safe 4-stone parents                         1,634,588
safe parent -> candidate pairs             117,253,740
parent has >=1 overlap                      81.7782%
candidate-level S_pair > S_mob               7.33076%
argmax(S_pair) set != argmax(S_mob) set      14.7528%
top sets completely disjoint                 0.662185%
both unique max and choose different move    8,952 = 0.547661%
maximum observed overcount O                  3
```

厳密な reversal 例:

```text
P = {0,1,6,50}

candidate 30:
  S_pair = 18
  S_mob  = 16
  O      = 2

candidate 57:
  S_pair = 17
  S_mob  = 17
  O      = 0
```

したがって raw pair rule は `30` を選び、exact mobility は `57` を選ぶ。tie-break の差ではない。

これは4石が、

1. 「distinct response coverage が重要」
2. 「同じ response を複数の forbidden witness で支える redundancy にも価値がある」

という2仮説を初めて分離できる深さであることを示す。

### D4 reduction

`argmax` sets が完全 disjoint な 10,824 parents は、D4 canonicalization で **1,362 orbits**。

さらに「pair / exact とも unique max だが別の手を選ぶ」8,952 parents は **1,119 D4 canonical orbits**。

したがって exact game-value 実験は raw 8,952 件ではなく、まず1,119代表に絞れる。

## 5. redundancy を連続パラメータとして扱う仮説

`S_pair = S_mob + O` なので、両端を補間する

```text
F_alpha(v) = S_mob(v) + alpha * O(v),  0 <= alpha <= 1
```

を定義できる。

- `alpha=0`: exact one-ply mobility
- `alpha=1`: raw pair-sum

strict disagreement で pair winner `p` と mobility winner `e` が

```text
S_pair(p) > S_pair(e)
S_mob(p)  < S_mob(e)
```

を満たすなら、

```text
d = S_mob(e) - S_mob(p) >= 1
r = O(p) - O(e)
```

に対して整数性から必ず

```text
r >= d + 1
```

となる。つまり raw pair rule が exact coverage を逆転するには、その deficit より少なくとも1大きい redundancy advantage が必要。

上の `{0,1,6,50}` 例は `d=1, r=2` で、最小の strict reversal になっている。candidate 30 と57だけを比較すれば切替点は `alpha=1/2`。

一般には全候補の `F_alpha` は直線群なので、各親で upper envelope と rational breakpoints を厳密計算できる。将来の blind game-value data に対して「共通 alpha が存在するか」を検定できる。

重要なのは、`O` は one-ply の distinct safe-response 数には何も寄与しないことである。したがって `alpha>0` が有効なら、redundancy は deeper structure の proxy と解釈すべきであり、即時 mobility の改善ではない。

## 6. 10×10既存完全分類: 局所 mobility の強い反例

10×10 の既存 exact classification / verified proof data は、9×9 blind replication とは別実験だが、仮説の外部対照として使える。

既知の5石 LOSS

```text
F = {2,13,61,73,91}
```

の各4石部分集合は、欠けた1石を置くことで LOSS に遷移できるため WIN である。

チャット側の局所 score 再評価では、その既知 LOSS witness move より高い pair/exact-mobility score を持つ候補が多数存在した:

```text
parent              LOSS witness   # higher pair   # higher exact
13,61,73,91              2               66             66
2,61,73,91              13               58             56
2,13,73,91              61               41             41
2,13,61,91              73               11             11
2,13,61,73              91               52             52
```

この表は現在、checked-in 再計算スクリプトを伴わない session-derived result なので、再利用前に機械可読 artifact として再現すること。

それでも示唆は明確で、3石で有効だった immediate mobility rule は4石以降のゲーム理論的な決定手を一様には説明しない。pair overcount を exact union に直すだけでも救えない反例がある。

## 7. 10×10 medium LOSS root の深さ別「LOSS核」

既存の legal eight-stone LOSS root

```text
R = {90,61,2,73,69,66,13,91}
```

の subset classifications を横断すると、LOSS subsets に強く偏る pair が深さごとに変化する。

### 3石

56 subsets 中 LOSS は2件:

```text
{90,2,91}
{90,73,91}
```

両方が `{90,91}` を含む。

```text
P(LOSS | contains {90,91}) = 2/6 = 33.3%
overall LOSS rate          = 2/56 = 3.57%
enrichment                 = 9.33x
```

### 4石

70 subsets 中 LOSS は12件で、**12/12 が `{61,66}` を含む**。

`{61,66}` を含む4石 subsets は15件なので:

```text
P(LOSS | contains {61,66}) = 12/15 = 80%
overall LOSS rate          = 12/70 = 17.14%
enrichment                 = 4.67x
```

逆に `{61,66}` を含まない55件は 55/55 WIN。

`{61,66}` を含みながら WIN になる例外3件は、追加2石が

```text
{2,13}
{2,73}
{90,13}
```

の場合。

4石LOSSへの点出現回数は:

```text
61: 12
66: 12
69: 5
91: 5
90: 4
73: 4
2 : 3
13: 3
```

### 5石

56 subsets 中 LOSS は11件。全件共通pairはなく、最頻 pair は `{13,91}` で9/11件。

```text
P(LOSS | contains {13,91}) = 9/20 = 45%
overall LOSS rate          = 11/56 = 19.64%
enrichment                 = 2.29x
```

### 6石

28 subsets 中 LOSS は3件で、3/3 が再び `{61,66}` を含む。

```text
P(LOSS | contains {61,66}) = 3/15 = 20%
overall LOSS rate          = 3/28 = 10.71%
enrichment                 = 1.87x
```

### 解釈

「強い2石部分集合」という発想は支持されるが、静的 pair weight

```text
score(P) = sum_{pair subset P} w(pair)
```

だけでは不十分。強いpairが

```text
3 stones: {90,91}
4 stones: {61,66}
5 stones: {13,91}
6 stones: {61,66}
```

と入れ替わるため、pair価値は少なくとも depth / surrounding stones に依存する。

候補仮説は

```text
w(a,b | |P|, P\{a,b})
```

のような context-dependent pair strength。

10×10座標 `id=y*10+x` では

```text
90=(0,9), 91=(1,9)  # horizontal adjacent
61=(1,6), 66=(6,6)  # horizontal, distance 5
```

なので「水平pair」だけでも「pair distance」だけでも核交代は説明できない。

## 8. 9×9完全証明書を4石LOSS探索に使えない理由

9×9の完全証明書は、中央初手後の1石 LOSS root からの AND/OR proof DAG である。

LOSS node は全 safe children を持ち、それらは WIN。WIN node は少なくとも1つの LOSS witness child を持つ。このため証明DAG上の outcome は depth とともに

```text
1 stone: LOSS
2 stone: WIN
3 stone: LOSS
4 stone: WIN
5 stone: LOSS
...
```

と交互になる。

したがって、この proof DAG の内部から **4石LOSS sample を抽出することはできない**。

また certificate は unbiased labeled dataset でもない。WIN node は通常1つの LOSS witness だけ保持すれば証明可能なので、証明書に現れる LOSS children を「全LOSS子の無作為標本」として扱わない。

4石で `S_pair` vs `S_mob` を game-value で判別するには、任意4石状態を root として direct solve する必要がある。

## 9. 次の実験優先順位の更新

### Priority A: 1,119 canonical strict-disagreement parents

9×9の「pair / exact がともに unique max だが別手」を選ぶ1,119 D4代表は、二仮説を最も効率よく分離する集合。

各親について最初から全候補を完全順位付けして探索する必要はなく、まず

```text
child_pair = P union {argmax S_pair}
child_mob  = P union {argmax S_mob}
```

の2 child positions の exact game value だけを問い合わせる。

- game values が異なる: その親は即座に識別力を持つ
- 同じ: その親だけ必要に応じて2位以下へ展開

D4 canonicalizationを使い、同一orbitを重複solveしない。

### Priority B: checked-in score reproduction

10×10の5石LOSS witnessに対する `# higher pair / # higher exact` 表を、既存 solver geometry と同じ定義で再生成する小さなツールを追加する。

出力候補:

```text
results/10x10/five-stone-loss-witness-local-scores.csv
```

少なくとも列:

```text
parent,witness,pair_score,mob_score,pair_rank,mob_rank,higher_pair,higher_mob
```

### Priority C: context-dependent pair test

10×10 medium root の subset classification は既に exact label があるため、新規solveなしで特徴量研究ができる。

各 depth `k`、各pairについて

```text
support(pair,k)
loss_count(pair,k)
P(LOSS | pair,k)
enrichment(pair,k)
```

を全pairで出し、`{90,91}`, `{61,66}`, `{13,91}` だけが post-hoc に目立ったのか、それとも pair-enrichment distribution の極端値なのかを評価する。

多重比較を考慮し、最大 enrichment の raw 値だけで結論しない。

## 10. 現時点の結論

1. 3石 fixed rule は exact immediate mobility そのもので、solver primary key とも本質的に同じ。randomより良かったことは意味があるが、solverとの一致は独立証拠ではない。
2. 4石以降では raw pair sum は distinct response coverage と redundancy に分解される。
3. 9×9全4石で pair と exact が実際に異なる選択をするため、4石はこの仮説を判別する最初の自然な深さ。
4. 10×10 exact classifications は、深い局面で immediate mobility が決定手を大きく外す例と、depth依存の強い pair core を示している。
5. したがって研究軸は「two-stone subsets を捨てる」ではなく、**単純加算から、distinct coverage / redundancy / context-dependent pair strength を分離して検証する**方向へ進める。

## Provenance / caution

9×9 blind replication baseline:

```text
branch: probe-two-stone-subsets
commit: b5172a4
```

その branch / commit の blind outcome table はこの追補では再実行していない。

10×10 subset labels は repository の既存 exact classifications / verified proof data に基づく。一方、10×10 witness local-score rank 表と、9×9 exhaustive pair-vs-mobility scan の数値は今回までの research-session derived results であり、今後再現用スクリプト・CSVを checked in して provenance を強化すること。