# 9×9 pair score component factorial experiment

最終更新: 2026-09-05

## 動機

4石局面の fixed two-stone score は

```text
raw = T + E + O
```

と分解できる。

- `T`: candidate によって本当に新しく失われる safe response 数
- `E`: 親局面ですでに danger だった response の再加算
- `O`: 同じ新規 danger response の重複加算

現在の confirmatory test は `T` と `raw` の比較として正しく固定されている。しかし、この比較だけで raw 側が勝った／負けたとしても、その原因が `E` なのか `O` なのかは識別できない。

連続重み

```text
F(alpha,beta) = T + beta E + alpha O
```

を pilot 結果に合わせて最適化すると、自由度が増えて post-hoc fitting になる。したがって confirmatory test の後段では、まず重み最適化をせず、成分の有無だけを切り替える 2×2 実験を行う。

## 4つの事前定義 score

```text
S00 = T
S10 = T + E
S01 = T + O
S11 = T + E + O = raw
```

ここでは第1添字を `E` の有無、第2添字を `O` の有無とする。

意味はそれぞれ:

```text
S00: 真の one-ply mobility のみ
S10: 既存 danger の再加算だけ許す
S01: duplicate witness の価値だけ許す
S11: 現在の raw pair rule
```

この4点は `F(alpha,beta)` の単なる便利な格子ではなく、`E` と `O` の寄与を混同せず比較できる最小の解釈可能な factorial design である。

## なぜ4点必要か

`S00` と `S11` だけでは、両者の差

```text
E + O
```

しか観測できない。

`S10` を加えると `E` を単独でオンにした効果、`S01` を加えると `O` を単独でオンにした効果を観測できる。さらに `S11` と比較することで、`E` と `O` の組合せが単独効果から外れるかを調べられる。

したがって、少なくとも

```text
T,
T+E,
T+O,
T+E+O
```

の4評価が必要。

## 実験単位

親4石局面 `P` ごとに、各 score の argmax move を求める。

```text
m00 = argmax S00
m10 = argmax S10
m01 = argmax S01
m11 = argmax S11
```

同じ move が複数 score で首位になる場合は同じ5石 childを一度だけ exact solveすればよい。

したがって1親あたり必要な独立 child solve 数は最大4であり、通常はそれより少ない。

### tie の扱い

最初の成分識別実験では、各 score が unique argmax を持つ親のみを primary analysis に使う。

理由は、tie-break rule の良し悪しと score 自体の良し悪しを混同しないため。

secondary analysis として tie を含める場合は、score の top-set 内に LOSS child が1つでも存在するか等の set-valued 指標を別に定義する。primary と混ぜない。

## 推奨する標本

現在進行中の `T` vs `raw` confirmatory holdout 1024件は、その主検定を変更せず完了させる。

この factorial experiment は、その1024件の結果を使って重みを選んだ後に同じ1024件へ当て直してはならない。

推奨順:

1. 現 confirmatory test を完了。
2. `S00/S10/S01/S11` の4 score 定義を変更しない。
3. pilot 64件と confirmatory 1024件を除外した残り D4 canonical population から、新しい holdout を deterministic hash sampling で作る。
4. 各親について4 score の unique top move の child outcome を exact solve。
5. 4 score を matched comparison する。

## primary questions

連続重みの最適値を聞く前に、以下を答える。

### Q1: E は役に立つか

`S00=T` と `S10=T+E` が異なる child を選ぶ親だけで比較し、どちらが LOSS child を多く選ぶかを matched exact test で評価する。

```text
E effect: S10 vs S00
```

### Q2: O は役に立つか

同様に

```text
O effect: S01 vs S00
```

を比較する。

### Q3: E の効果は O があると変わるか

```text
S11 vs S01
```

は `O` をオンにした条件で `E` を追加する比較。

### Q4: O の効果は E があると変わるか

```text
S11 vs S10
```

は `E` をオンにした条件で `O` を追加する比較。

これにより、`E` または `O` の単独効果と interaction を区別できる。

## 集計

各 pairwise comparison `(A,B)` について、score A と score B が別childを選んだ親で

```text
A-only LOSS
B-only LOSS
both LOSS
both WIN
```

を数える。

主に informative なのは discordant outcome:

```text
A-only LOSS vs B-only LOSS
```

で、exact binomial / McNemar 型の matched test を使う。

4比較を同時に正式検定する場合は多重性を事前に処理する。最も単純なのは Holm correction。

ただし現 confirmatory test の主仮説・有意水準・標本にはこの新計画を遡及適用しない。

## 実装仕様

既存の

```text
scripts/analyze-9x9-pair-gap-decomposition.cpp
```

を拡張し、各 safe candidate の `(T,E,O)` から

```text
score_T       = T
score_TE      = T + E
score_TO      = T + O
score_raw     = T + E + O
```

の4首位を同時に追跡する。

D4 canonical CSVには最低限

```text
canonical_parent,
top_T,
top_TE,
top_TO,
top_raw,
unique_T,
unique_TE,
unique_TO,
unique_raw
```

を保存する。

必要なら各top moveの `(T,E,O)` も付ける。

比較solver側は parentごとの unique move集合を作り、最大4 childを exact solveする。memo共有時の `visited/seconds` は outcome比較には使わない。

## ここから得られる判断

結果は少なくとも次のように解釈できる。

- `S10 > S00`, `S01 ~= S00`: raw rule の有用部分は主に `E`。
- `S01 > S00`, `S10 ~= S00`: duplicate witness `O` に深い価値がある。
- `S10,S01` は弱いが `S11` が強い: E/O interaction が重要。
- `S00` が全般に強い: pair rule の余剰成分は主にノイズ。
- scoreごとに勝敗が交錯する: 固定線形 score の限界が強く、局面依存または浅い敵対読みへ進むべき。

この結果を得るまでは、`alpha,beta` の細かい連続最適化を優先しない。4つの意味の明確な端点で成分の方向を確定してから、必要なら独立データで中間重みを調べる。
