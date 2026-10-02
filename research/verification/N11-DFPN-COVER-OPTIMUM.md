# s4 certificate manifest と cover 最適化の下界

**11×11: UNKNOWN**

- base commit: `6bf2bd8`

## s4 cache に certificate manifest を持たせる

単なる `s4key -> LOSS` は他者が検証できない。
検証可能にするのは manifest である:

```
LOSS  ... 合法 s5 子すべての canonical key
        （各子が LOSS であることと、そのリストが完全である
          ことを読み手が再確認できる）
WIN   ... s5 WIN の witness 1 個だけでよい
```

フォーマット:

```
s4verdict,r2,key_lo,key_hi,result,n_child,child_lo,child_hi,...
```

これにより上位 certificate と下位 s5 証明を**別々に**検証できる。

```
r2 LOSS certificate
  31 個程度の canonical s4 class
    各 LOSS class
      全 s5 子が LOSS
```

## 最小 set cover の厳密な下界

coverage に重なり制約があるため、`ceil(119/6)=20` は
真の最小値ではない。整数最適化で最小値を求めると
**31 class** になる（報告された値）。

既に LOSS 証明済みの `{60,0,1,2}` class を必ず含めても最適値は 31 のまま。

**独立検証（`dfpn_cover_optimum.py`）**:

```
vertices          : 119
classes           : 3396
distinct covers   : 2002   （coverage 集合が同一の class を統合）
max coverage      : 6
counting bound    : 20
greedy upper bound: 35
  limit=20 .. 30 : すべて解なし（各 1 node で除外）
```

`ceil(119/6)=20` から 30 までが厳密に除外され、**31 のみが残る**。
下限の導出には 2 つの独立な charge を足し合わせている:

- **Charge A（分数）**: size k の class は未被覆頂点を高々 k 個しか
  覆えないので、頂点 v のコストは `1/maxcov(v)` 以上。
- **Charge B（互いに素な集合）**: 「who can cover me」の集合が互いに
  素な頂点同士は 1 つの class では同時に覆えない。この greedy
  independent set が 1 頂点につき 1 の charge を加える。

**Charge B が効くのがポイント**である。追加前は `uncovered / maxcov`
しか無く depth 22 で 25 分以上回らなかったのが、
追加後は depth 22..30 が各 1 node で除外される。

**31 class 解の内訳**:

```
21 x coverage4  +  8 x coverage3  +  1 x coverage5  +  1 x coverage6  =  119
```

coverage 集合が互いに素であり、119 頂点をちょうど partition する。

つまり「理想的に全部 LOSS なら、現在の 1 class を含めて 31 個で
119 頂点をちょうど覆える」という具体的な target skeleton が存在する。

現在のところ 1 個が確定しているので、best case では残り 30 個。

## orbit による検証

固定 root `{60,0}` の stabilizer は恒等変換と主対角線反射の 2 元。
119 個の m3 はこの作用で:

- 55 個の 2 点 orbit
- 対角線上の 9 個の 1 点 orbit

= 計 64 orbit に落ちる。

現在の LOSS class `{1,2,11,22}` は raw では 4/119 だが、
orbit 単位では `{1,11}` と `{2,22}` の **2/64** を覆う。

1 class が覆える m3-orbit は最大 3 なので、この見方の単純下界は 22、
そこから実際の incidence をすべて考慮すると 31 になる。

## coordinator 設計の帰結

並列 driver は単純な

```
fresh coverage DESC, unknown s5 children ASC
```

より、**毎回 optimistic set cover を解き直す coordinator** にすべきである:

```
LOSS class    ... 使用可能, cost 0
UNKNOWN class ... 使用可能, cost 1
WIN class     ... 使用禁止
```

未 covered 頂点を覆う最小 cover を解き、
その candidate skeleton 内の UNKNOWN を並列投入する。
LOSS なら確定、WIN ならその class を除外して set cover を再計算する。

これなら「coverage 6 だからとりあえず調べる」より直接、
最終 certificate に入り得る class だけに計算資源を寄せられる。

進捗指標としても有効である。

```
known LOSS classes = 8
covered = 29/119
optimistic minimum additional classes = 24
```

「何個証明したか」ではなく、現在の cache から最短であと何 class
必要かを常に表示できる。

## 並列化の注意

s5 cache は proof material なので、**複数 worker が同じ CSV へ
直接 append してはいけない**。各 worker が

```
s5-worker-00.csv
s5-worker-01.csv
...
```

へ書き、coordinator が canonical key ごとに deterministic merge し、
WIN/LOSS conflict で即停止、最後に atomic rename する。
s4 cache も同じ方針。

## 現状

**LOSS class 1 個、covered 4/119。**

- reply r2=0 が LOSS とはまだ言っていない
- 二石 root は 1 個も閉じていない
- 31-class skeleton は**目標**であり、証明ではない

**11×11: UNKNOWN**
