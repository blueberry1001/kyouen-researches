# 10×10 blind probe: batch0 selection-bias audit

最終更新: 2026-09-07

## 結論

既存の blind probe 追試で用いられた `solver既定順` との比較には、batch0 の作り方に由来する選択バイアスがある。

`docs/10X10_PROBE_BLIND_VALIDATION.md` では、各3-stone parentについて children を入力順に分割し、まず **先頭20 children (= batch0)** だけを exact solve している。一方、同報告書の `solver既定順` は **children入力ファイル順** と定義されている。

したがって主評価7親は、実質的に

1. solver既定順の先頭20だけを観測し、
2. その先頭20に少なくとも1つLOSSが存在したparentだけを残し、
3. その条件付き集合でsolver既定順の first LOSS rankを評価する

という手続きになっている。

このため、`solver既定順中央値=3.0` を fixed rule / random と同列の公平な baseline と解釈してはいけない。

## 何が問題か

parent全体の child 列を

```text
c1, c2, ..., cN
```

とし、この順序そのものをsolver既定順とする。

今回 exact outcome を観測したのは

```text
c1, ..., c20
```

のみである。

さらに主集計には

```text
{ parent : c1..c20 のどこかに LOSS がある }
```

という条件を満たすparentだけが入る。

この条件はsolver既定順の first LOSS rankが20以下であることを直接要求している。したがって、solver既定順が悪いparent、特に最初のLOSSが21番目以降にあるparentは主集計から構造的に落ちる。

実際 `0,36,43` はbatch0にLOSSがなく主集計から除外されている。これは単なる欠測ではなく、solver順に依存した選別である。

## 何がまだ使えるか

### fixed vs random

fixedとrandomは、観測済みの同じ20 childrenを並べ替えて比較している。そのため

> 「solver既定順の先頭20にLOSSがあるparentに条件付けたとき、その20件内でfixedがrandomより早く既知LOSSを拾うか」

という限定された問いには使える。

ただしこれは

> 「parentの全childrenを対象にfixedがrandomより良い」

とは同じではない。

また、batch0入力順自体がfixed featureと相関していないことは保証されていないため、完全な独立holdoutとは言い切れない。

### solver defaultとの比較

主張を最も弱める必要がある。

現在の

```text
fixed median = 3
solver median = 3
```

は、solverが自身の先頭20にLOSSを持つparentだけを選んだ後の比較なので、solver側へ有利な条件付けを含む。

したがって

- `fixedはsolver既定順と同等だった`
- `fixedはsolver既定順に勝てなかった`

という結論は、全childrenを観測するまで confirmatory evidence として扱わない。

## C判定への影響

旧C判定のうち、次はそのまま残る。

- batch0条件付きで fixed median 3
- batch0条件付きで random median 6
- batch0条件付きで fixedはrandomより3勝2敗2分
- 大きな反例 `4,9,33`, `9,19,33` が存在

一方、次は保留へ下げる。

- solver既定順中央値3との同等比較
- solver既定順に対する個別勝敗
- solver既定順比の総コスト改善

よってC判定を完全に無効とする必要はないが、内容は

> `batch0条件付きでrandomより有望な兆候はあるが、solver defaultに対する優位・同等性は未検証`

と読むべきである。

## 最優先の修正実験

既観測7親について、新しいfeature tuningを行う前に **全childrenをexact分類**する。

各parentで:

1. batch1以降を含む全childrenをexact solve
2. 全child outcomeが揃ったことをmanifestで検証
3. その後にのみ
   - fixed rule
   - random
   - solver default
   - legal-count baseline
   - legal-count + independent memo tiebreak
   のfirst LOSS rankを再計算
4. 旧batch0条件付き結果と全children結果の差を記録

この再評価は既にoutcomeを見たparent上のpost-hoc監査であり、新規confirmatory evidenceとはしない。ただし、旧C判定がtruncationにどれだけ依存していたかを定量化できる。

## 今後の新規holdout設計

計算量上、全childrenを最初から解けない場合でも、batchをsolver入力順の先頭から取ってはいけない。

outcomeを見る前に、各childを例えば

```text
SHA256(seed || NUL || canonical_parent || NUL || canonical_child)
```

で順位付けし、最初のK件をpartial-exact subsetとして固定する。

このsubset選択は

- solver default順
- fixed probe score
- legal_move_count
- memo_used

のいずれからも独立でなければならない。

ただし、partial subsetだけを使う限り評価対象はあくまでそのsubset内順位であり、全children順位の代用にはしない。

本命confirmatoryでは、可能ならparent単位で全childrenを分類する。

## 実験優先順位

1. 既存7親の全children exact completion
2. full-childで旧fixed/random/solver評価を再計算
3. batch0結果との差分監査
4. その後に legal-count + memo tiebreak の新規holdout
5. 旧batch0結果を新ルール選択へ追加学習データとして混ぜない

この順序なら、現在見えている最大の方法論的不確実性を、追加の仮説自由度を増やさず潰せる。
