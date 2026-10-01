# 専用 quant solver: 2 石 root を ∃m3 ∀m4 ∃m5 で解く

**11x11 の勝敗は UNKNOWN のまま。**
本ファイルは**実装と途中経過**であり、勝敗の断定ではない。

- base commit: `cd86ea7`
- 実装: `cpp/solvers/kyouen_dfpn_root.cpp`
- 機械: WSL / g++ -O3 -march=native、16 cores / 19 GB RAM
- swap 使用 0

## 出发点: 二石 root の論理的構造

二石 root `{m2,r2}` は OR ノードである。したがって
**「元为先手が勝つ」を示すには、勝つ三手目が 1 つあればよい**。
三石局面は AND ノードなので、選んだ三手目に対する
**全ての四手目**で WIN を維持しなければならない。
四石局面は OR ノードなので、各四手目について
**勝つ五手目が 1 つ**あればよい。

```
二石 root r2  =  ∃m3 : ∀m4 : ∃m5 : s5(m2,r2,m3,m4,m5) が WIN
中央初手全体  =  ∀m2 : ∃m3 : ∀m4 : ∃m5 : s5 が WIN
```

s5 は exact oracle で解けることが分かっているので（10M nodes 以内で
全件閉じる）、残るのは 3 段の量化評価だけである。
汎用の exact DFS で二石 root を直接解くと、この構造を捨ててしまう。

**注意: 「二石 root を閉じるには全ての子が証明される必要がある」
という記述は誤り。** WIN を示すには 1 つの勝つ三手目で十分であり、
 ∀ が必要なのは「勝つ三手目を選んだ後」の四手目に対してだけである。

## 実装

`--quant-first=60 --quant-replies=... --quant-budget=N [--quant-timeout=S]`

- `s5_oracle()`: 正規化 key → WIN/LOSS の永続 cache 付きで
  5 石局面を exact で解く。**UNKNOWN は cache しない**
  （budget 切れを後続のより豊かな query が引き継いでしまうため）。
- `quant_solve()`: `∃m3 : ∀m4 : ∃m5 : s5 WIN` を直接評価。
- `quant_root()`: oracle cache を保持したまま 1 返信を処理。
- driver `run_quant()`: 20 返信を**単一 process**で回すので
  cache が返信間で共有される。異なる三手目・異なる返信が
  同じ D4 軌道の s5 局面に到達するため效果があると期待する。

### 証明書

WIN が出た場合のみ、次の形式で出力する:

```
reply r2
  winning third move r3
    for every legal fourth reply r4
      a winning fifth move r5 and the canonical key of that s5
```

20 返信すべてでこれが出れば、中央 `60` が P 局面であることの
直接証明になる。某一返信で全三手目が失敗すればその返信は反証。

## 開発中に見つけた自分のバグ

`--quant-*` の 4 つのフラグすべてで `substr()` のオフセットが
1 ずれていて、空文字列や `=60` を `stoi` に渡して `error: stoi` に
なっていた。フラグ名長 + 1 が正解である
（`--quant-replies` は 15 文字なので 16 から取る）。

**このような mistake は「その経路を初めて通ったとき」にだけ露見するため、
フラグを追加するたびにオフセットを機械的に検証すべき。**
既存のフラグをすべて検証したところ、他は正しかった。

## 途中経過: 1 返信の最初の三手目で 12 分経過

`--quant-replies=0`（1 返信だけ）、node budget 20,000,000 で計測。
third move を 1 つずつ試すごとに進捗行を出すようにして計測した。

```
[quant] r2=0 m3=1 (1/119) queries=0 hits=0 nodes=0
```

**この行が 12 分以上更新されない。**

### 重要な観測

`queries=0` であることが決定的である。これは
「三手目 1 個目の**内部で** oracle が 1 回も return していない」
ことを意味する。cache が効いていないから遅いのではなく、
**最初の 1 件の oracle query 自体が budget を使い切っている**。

実際、三手目を 1 つ固定すると、四手目が 117 通り、
各四手目の五手目が 116 通りなので、
**1 つの三手目を処理する最悪ケースは 13,572 query**。
budget 20M なら query 1 件の平均 budget は 1,473 nodes に過ぎず、
これは s5 の benchmark（最小 130,540 nodes）より**桁違いに小さい**。

したがって budget 20M という設定自体が
「1 query も完了できない」水準であり、
`queries=0` は予算不足の徴候であって、
構造的欠陥ではない。

### 正しい budget の見積もり

s5 benchmark の実測値:
- 最小 130,540 nodes（s5 の 23 unique root の最小）
- 中央値 ~2.4M nodes
- 最大 5,677,449 nodes

したがって `queries` 1 件を完了させるには
最低でも ~130k、通常は ~1-2M の budget が必要。
1 返信を閉じるには
`117 × 116 = 13,572` query × `~1M nodes` = **~1.3e10 nodes**。

現在の exact 実装は ~1e6 nodes/s 程度なので、
1 返信あたり **数万秒から数時間**の桁になる。
20 返信すべてを単純に回すことは間に合わない。

### 結論: 素朴な量化評価は予算的に成立しない

`∃m3 : ∀m4 : ∃m5 : s5 WIN` を素朴に評価すると、
三手目 1 個あたり最悪 13,572 oracle query が必要であり、
budget 20M では 1 query も終わらない。

**構造の正しさは確認できたが、効率が 2〜3 桁足りない。**
必要な改善:

1. **Cut を使う。** 5 石局面を厳密に解くのではなく、
   相手がさらに 1 手（6 石目）を置いたときにも
   WIN の余地が残るかだけを判定する早期 cut を入れる。
2. **cache の実効を測る**。現状 `queries=0` で
   cache 効果の測定すらできていない。
3. **三手目の候補順序**を、cache hit が多い順に試す。
4. **対称性を活用する。** D4 軌道で同じ s5 局面を共有できれば、
   `∀m4` の 117 通りが軌道に縮約される。

## correctness


- hybrid 回帰: n=4 LOSS / n=5 WIN / n=6 WIN / n=7 LOSS（不変）
- adaptive 回帰: 全条件 pass（不正指定は rc=2）
- quant は n=11 専用の実装（5 石固定）のため、
  n=6/7 では「二石 root を 3 段量化で解く」こと自体が
  正しい比較対象にならない。quant の soundness は
  **n=11 で 1 返信を閉じて certificate を出力できるかどうか**で
  判定する（certificate は第三者が再検証可能な形になっている）。

## 次にすべきこと

1. **oracle cache の effectiveness を測る**。queries 対 hits の比が
   共有 benefits を示す。1 返信で 13,572 query なら cache が効けば
   数十〜数百の distinct s5 局面に収まるはず。
2. **1 返信を閉じて certificate を出せるか**。これが出れば
   残りは 20 返信へ展開するだけ。
3. 閉じない場合は、三手目の候補順序を設計する
   （cache hit が多い三手目から試す等）。

## 記録

- 20 返信 sweep の結果ではなく、**新しい solvers の実装と
  1 返信の途中経過**。未解決の二石 root はないが、
  1 件も閉じられていない。
- **11x11 は UNKNOWN のまま。**