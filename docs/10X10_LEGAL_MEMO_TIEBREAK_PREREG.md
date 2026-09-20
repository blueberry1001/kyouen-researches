# 10×10 legal-move-count + independent memo tie-break 事前登録

最終更新: 2026-09-07

## 背景

旧3石盲検追試では、共有memoを含むprobe値に入力順汚染があり、fresh Solverで各候補を独立にprobeし直すと `memo` 単独昇順は既存solver順より悪化した。したがって、`memo` を探索順全体の第一キーにする仮説は支持されない。

一方、solver既定順の主要成分は「子局面からの合法手数が少ない順」である。既観測7親を用いた探索的解析では、合法手数を第一キーとして固定し、同じ合法手数の候補同士だけを independent `memo_used` 昇順で並べると、一部親で first LOSS 順位が改善する兆候があった。ただしこれは既観測outcomeを用いた post-hoc 仮説生成であり、証拠には数えない。

本書は、その残余仮説を新規・未観測の10×10 holdoutへ適用する前に固定する。

## 仮説

子局面 `s` の順位キーを

```text
K_memo(s) = (legal_move_count(s), independent_memo_used(s), canonical_state_key(s))
```

とする。

対照は

```text
K_base(s) = (legal_move_count(s), canonical_state_key(s))
```

とする。

ここで

- `legal_move_count(s)`: その局面から打てる合法手数。共線または共円を作る手を違法とする現行10×10ルールで決定的に再計算する。
- `independent_memo_used(s)`: 各候補ごとに fresh Solver を生成し、固定budgetでprobeした終了時memo使用量。
- `canonical_state_key(s)`: outcomeに依存しない決定的tie-break。局面を昇順整数列として辞書順比較する。

`memo` は合法手数が異なる候補間の順位を絶対に逆転させない。

## probe条件

既存のcorrected independent probeと同じ条件を使う。

```text
board = 10x10
budget = 1,000,000
shrink = 3
load = 80
fresh Solver per candidate = required
```

solver binary・source・task集合・budgetをmanifestで固定する。

候補を順にprobeして同じmemoを共有してはならない。

## 対象holdout

この検定に使えるのは、以下をすべて満たす親だけとする。

1. 親集合がprobeおよびexact child outcomeを見る前に固定されている。
2. 子候補集合もoutcomeを見る前に固定されている。
3. 各候補の `legal_move_count` と independent probe値がexact outcomeを参照せず計算されている。
4. 既存7親 `2,9,33`, `4,9,33`, `9,12,33`, `9,19,33`, `9,23,33`, `0,31,36`, `0,36,44` はconfirmatory集計から除外する。

現在別実験として進行中の新規10×10 `memo昇順` holdoutを流用する場合は、exact outcomeを開く前に本書のcommitが存在し、かつ上記1--3を満たすことを必須とする。条件を満たさない場合は次の新規holdoutに適用する。

## 主評価量

各LOSS親 `i` について

```text
R_base(i) = K_base順で最初のLOSS childが現れる1-indexed順位
R_memo(i) = K_memo順で最初のLOSS childが現れる1-indexed順位
D(i) = R_memo(i) - R_base(i)
```

とする。

`D < 0` はmemo tie-break改善、`D > 0` は悪化、`D = 0` は同順位。

第一の要約値は

```text
sum_i D(i)
```

および

```text
median_i D(i)
```

とする。

ただし、合法手数tieがfirst LOSS到達前に一度も発生しない親は規則上 `D=0` になり、情報を持たない。そのため「memoが実際に順位を変え得る親」だけを対象とした符号比較も事前に併記する。

## confirmatory判定

非tie親について

```text
memo-win  = count(D < 0)
memo-loss = count(D > 0)
```

を数え、帰無仮説

```text
P(D < 0 | D != 0) = 1/2
```

に対する exact two-sided sign test を主p値とする。

方向仮説は `memo-win > memo-loss` だが、既観測7親から仮説生成したため、保守的に両側p値を主報告とする。

有意水準は `alpha = 0.05`。

効果量として

- `memo-win / (memo-win + memo-loss)`
- `sum D`
- `median D`
- 全LOSS親での `R_base` と `R_memo` の中央値

を報告する。

## 成功条件

次をすべて満たした場合のみ、「memoは合法手数tie-breakとして再検証に値する」と判定する。

1. non-tie親で `memo-win > memo-loss`
2. `sum D < 0`
3. exact two-sided sign test `p < 0.05`

標本不足でp値条件へ到達できない場合は「未確定」とし、勝ち越しだけで成功扱いにしない。

## 副解析

以下は探索的とする。

- `memo_used` 差の大きさと `D` の関係
- `legal_move_count` tie群サイズ別の効果
- LOSS child数別の効果
- probeがbudget内でexactに終了した候補と未解決候補の分離
- `visited`, `maxdepth` など他probe特徴量によるtie-break

これらを見て主ルールや主p値を変更しない。

## 禁止事項

- exact outcomeを見た後で `memo` 昇順/降順を選ぶ
- legal_move_countとmemoの重み付き和をholdout上でfitする
- 合法手数が異なる候補間でmemoにより順位を逆転させる
- 不都合な親を事後除外する
- 既観測7親をconfirmatory標本へ戻す
- shared memo probeをindependent probeとして扱う
- solver入力順を無指定tie-breakとして利用する

## 研究上の位置づけ

この実験は `memo昇順` を主順位とする仮説の救済ではない。問いはより限定的である。

> 既存の強い `legal_move_count` ヒューリスティックが同点まで絞った後にも、fresh independent probeの `memo_used` は追加情報を持つか。

ここで負ければ、少なくとも現行budget=1,000,000の `memo_used` は探索順特徴量として優先度を大きく下げる。勝てば、全面的な並べ替えではなく限定的tie-breakとしてのみ次段の実測探索コスト比較へ進める。
