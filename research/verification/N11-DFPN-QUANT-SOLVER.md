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

## 途中経過: 1 返信を閉じるのに 10 分超

`--quant-replies=0`（1 返信だけ）を 20M budget で走らせたところ、
**10 分を超えても終わらなかった**。

想定と違っていたのは、量化構造の `∃m3` ループが
三手目候補を順に試すだけで、**1 つの三手目が ∀m4 を満たすとは
限らない**ためである。ある三手目が失敗するたびに
117 個の四手目 × 各々 116 個の五手目 = 13,572 回の s5 query を
要しうる。実際には cache が効くはずだが、それでも
「1 返信で 1 万回以上 oracle を叩く」可能性がある。

**したがって 1 返信を閉じるコストは、当初の想定より
1 桁以上大きい可能性がある。** 20 返信すべてを単純に
回すことは现实には来不及ない。共有 oracle cache の効果を
測定してから規模を決めるべき。

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