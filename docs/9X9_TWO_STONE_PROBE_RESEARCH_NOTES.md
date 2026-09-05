# 9×9 two-stone probe / fixed-rule research notes

最終更新: 2026-09-05

この文書は、9×9 共円ゲームについて `probe-two-stone-subsets` の盲検追試後に行った追加解析を、**現在有効な結論 / 暫定仮説 / 棄却・訂正済み / 次の実験**に分けて残す研究メモである。

> 注意: 盲検追試を行った branch `probe-two-stone-subsets` と commit `b5172a4` は、2026-09-05 時点で接続済み GitHub から取得できなかった。そのため盲検追試の数値は完了済み実験から引き継いだ値であり、このコミットでは再実行していない。一方、幾何・組合せ構造の解析は公開されている 9×9 ルール（81点、整数行列式0で共円/共線判定）に合わせて独立に再計算した。

## 1. 盲検追試の基準点

完了済みの blind replication (`probe-two-stone-subsets`, `b5172a4`) では、新規 LOSS 親 7 件（batch0 部分探索）について:

- fixed rule first LOSS median: **3.0**
- random median: **6.0**
- solver default-order median: **3.0**
- fixed vs random: 過半数を LOSS まで到達させる探索予算が `6 -> 3`
- 成功判定: **C**
- 最大反例:
  - `4,9,33`: fixed 16 / random 6 / solver 3
  - `9,19,33`: fixed 13 / random 11 / solver 8

7件しかないので「50%改善」を一般化するより、

> fixed は budget 3 で過半数をカバーし、random は budget 5 まででは過半数をカバーできない

と表現する方が安全。

## 2. 盤面・ルールの確定事項

今回の解析対象は **9×9 / 81点**。点番号は

```text
idx -> (idx % 9, idx // 9)
```

で、4点 `p_i=(x_i,y_i)` が禁止4点組かどうかは

```text
[x^2+y^2, x, y, 1]
```

の 4×4 整数行列式が0かで判定する。これにより4点共円と4点共線を同じ条件で扱う。

9×9 の禁止4点組は **29,152個**。

また勝敗判定は石の所有者ではなく占有点集合だけに依存するため、勝敗探索の状態は本質的に occupied set だけでよい。

## 3. 重要な訂正

### 3.1 10×10 前提の反例解析は無効

途中で最大反例を10×10として解析した時期があったが、これは今回の9×9 blind replicationには適用できない。10×10前提で得た境界自己封鎖・8点円などの説明は **9×9反例の根拠として使用しない**。

### 3.2 3石親の一手評価では gain の重複は起きない

3石親 `S={a,b,c}` に合法手 `v` を置くとき、3つの親ペア由来の新規危険点集合

```text
F(a,b,v), F(a,c,v), F(b,c,v)
```

は互いに素。もし同じ完成点を共有すると、円/直線の一意性から `a,b,c,v` 自体が禁止4点組になり、`v` の合法性に反する。

全 85,320 個の3石親・全 safe 4手目（合計 6,538,352 safe moves）でも反例0。

したがって3→4石では

```text
gain(v) = g_ab(v) + g_ac(v) + g_bc(v)
```

が **実際に新しく消える安全点数と厳密一致**する。

### 3.3 4石以降では raw gain は過大計数する

4石以降は、

- 既に危険な点を再び数える
- 新規危険点集合どうしが重なる

ため raw gain と実際の unique gain がずれる。

最大反例周辺153個の4石子局面では「既存危険点を除くだけ」の補正で true unique-gain top を153/153含んだが、無作為5万4石局面では:

- raw が true unique top を外す: **7.49%**
- existing-danger 補正後: **0.774%**

まで改善するものの、完全ではない。

したがって4石以降の正しい局所量は

```text
unique_gain(action)
= popcount((union of newly created danger points) & ~existing_danger)
```

である。

## 4. 最大反例2件の共通幾何

座標は:

```text
4  = (4,0)
9  = (0,1)
19 = (1,2)
33 = (6,3)
```

両最大反例はペア `{9,33}` を共有する。

このペアは10格子点円

```text
x^2 + y^2 - 5x - 7y + 6 = 0
center = (2.5, 3.5)
r^2 = 25/2
points = {2,3,9,14,33,42,54,59,65,66}
```

上にある。

したがって `{9,33}` と同円上の残り8点へ打つと、このペア単独で **gain=7** が得られる。

さらに `{9,33}` は8点円

```text
x^2 + y^2 - 7x - y = 0
points = {0,7,9,16,28,33,39,40}
```

にも属し、残り6点は pair gain=5。

最大反例の fixed / solver-local top は:

```text
4,9,33 -> 14 : gains (7,5,2), total 14   [unique top]
9,19,33 -> 3  : gains (7,5,3), total 15   [unique top]
```

次点例:

```text
4,9,33:
  3  -> (7,5,1), total 13
  49 -> (5,5,3), total 13

9,19,33:
  59 -> (7,5,1), total 13
  49 -> (5,5,3), total 13
```

したがって、この2最大反例の最初の fixed 選択は tie-break 事故ではなく **一意首位**。

一方で `(7,5,*)` 自体は盤面全体では珍しくないため、「10点円+8点円だけ」がLOSS原因とは言えない。

## 5. 候補競合グラフとしての解釈

3石親 `S` の safe candidate を頂点とし、候補 `v,w` を続けて両方置けないとき辺を張るグラフ `G_S` を考える。

3石親では

```text
deg_G(v) = gain(v)
```

が厳密に成立する。つまり fixed rule / immediate-gain 最大化は、

> **候補競合グラフで最大次数頂点を選ぶ規則**

と解釈できる。

さらに各競合辺の原因は親の3ペア `ab/ac/bc` のうち **必ず1つだけ**。各色ごとには「同じ円/直線クラス」の候補が完全グラフを作るため、

```text
E(G_S) = E_ab disjoint-union E_ac disjoint-union E_bc
```

であり、各 `E_pair` は互いに交わらない clique の直和。

候補 `v` の3色次数を `(s1,s2,s3)` とすると:

```text
d(v) = s1+s2+s3
X(v) = s1*s2 + s1*s3 + s2*s3
P(v) = s1*s2*s3
```

`(d,X,P)` から multiset `{s1,s2,s3}` は復元できる。全85,320親では、`d -> (d,X)` は同次数 tie をかなり減らすが `P` の追加効果はほぼ無い。

- `d` で一意首位: 62,156 / 85,320 = 72.85%
- `(d,X)` で一意首位: 68,944 / 85,320 = 80.81%
- `(d,X,P)` で一意首位: 68,980 / 85,320 = 80.85%

したがって **3個の gain 数の対称式をさらに増やす方向はほぼ頭打ち**。

最大反例は:

```text
4,9,33 -> 14: (s1,s2,s3)=(7,5,2), d=14, X=59
9,19,33 -> 3 : (s1,s2,s3)=(7,5,3), d=15, X=71
```

で、`d` と `X` はどちらも各親内で単独1位。

## 6. 競合グラフの高次構造について分かったこと

### 虹三角形 / Berge cycle

3色の辺を1本ずつ使う三角形は基礎3部ハイパーグラフの length-3 Berge cycle に対応する。

最大反例では:

- `4,9,33`: `14,3,49` が主要な虹三角形
- `9,19,33`: `3,49,59` が主要な虹三角形

だが、虹三角形数や次数重み付き虹三角形は `49` など非LOSS候補を過大評価するため、主指標としては弱い。

length-4 Berge cycle もLOSS手を上位には置くが単独首位にはできず、閉路数単独説は降格。

### 2段先の単純な広がり

候補の近傍から直接非隣接な候補へ伸びる2段経路数も最大反例を上位に置くが、`d` / `X` より弱い。単純な「2段先への広がりが大きいからLOSS」説は支持が弱い。

## 7. 4石以降 / response distribution の知見

最大反例の top move 後、相手の safe response ごとの exact unique gain 分布は一般局面より不均一。

既知値:

```text
4,9,33 -> 14:
  responses 62
  mean G2 ≈ 5.806
  median 5
  max 16
  CV ≈ 0.793
  Gini ≈ 0.440
  normalized entropy ≈ 0.9199
  Neff/n ≈ 0.7186
  weak responses (G2<=3): 23/62 = 37.1%

9,19,33 -> 3:
  responses 60
  mean G2 ≈ 5.600
  median 5
  max 16
  CV ≈ 0.770
  Gini ≈ 0.434
  normalized entropy ≈ 0.9213
  Neff/n ≈ 0.7245
  weak responses (G2<=3): 26/60 = 43.3%
```

一般親では弱い応手率中央値がおよそ24%で、最大反例は「超強い応手が異常に多い」のではなく **弱い応手が大量に増えて二極化する**のが特徴。

ただしこれは最大反例を見てから得た post-hoc 指標なので、新規LOSS7件へ適用するときは定義・閾値を先に固定する必要がある。

## 8. 現時点で降格・棄却した仮説

以下は解析途中で有望に見えたが、全盤面・対照群・正規化後などで弱くなったもの。今後の主仮説としてそのまま再使用しない。

- 10×10境界自己封鎖説（盤面誤認）
- 3→4石での gain 重複説（合法手では数学的に重複しない）
- gain=9 を 8 に飽和する `S8` が最大反例を直す説（最大反例には gain=9 候補なし）
- 特定の1石が巨大ハブになる説
- 弱い応手の空間クラスタ説
- response danger set の重複が低entropyを作る説（むしろ重複は少ない側）
- 1手先最大unique-gainだけで最大反例を説明する説
- 2手先 greedy gain / 平均mobilityだけで説明する説
- raw残存辺数・LCC・clustering・橋率など単一グラフ特徴だけでLOSSを説明する説
- H3→H2 の単純な変換率 / 再結合率説
- 終局最大独立集合サイズやランダム極大完成の偶奇だけで説明する説
- 10点円 / `(7,5,*)` そのものが稀だからLOSSになる説
- channel-wise monotone score `sum f(g_i)` で最大反例を直す説。`(7,5,3)` が `(7,5,1)` と `(5,5,3)` を成分ごとに支配するため、座標単調な score では原理的に勝てない。
- 3ペアだけで二手先制約グラフを作る解析。4石局面では既存4石の **全6ペア** を使う必要がある。
- 3ペア簡略版で得た LP≈exact / partial Latin square の強い主張を、全ゲーム二手制約へそのまま拡張すること。
- `alpha`（二手先制約グラフ最大独立集合）を全合法候補上の単独LOSS predictor とする説。競合する高gain候補間では有用な場合があるが、全候補で見ると最大反例のalpha順位は平凡。

## 9. 探索高速化で確定しているもの

### D4 symmetry canonicalization

9×9正方形の回転・鏡映8対称で勝敗は保存される。

3石親:

```text
85,320 raw states -> 10,874 D4 orbits
```

約7.85倍圧縮。

深い層ほどほぼ8倍に近づくため、親だけでなく transposition table 全体のキーをD4 canonical formにする価値が高い。

### 差分 danger-mask 更新

全4点禁止パターンを3石完成表

```text
T={a,b,c} -> F(T)={q | T+q forms a forbidden 4-set}
```

へ変換すると、局面 `S` の danger mask は

```text
B(S) = union_{T subset S, |T|=3} F(T)
```

で、手 `v` の後は

```text
B(S+v)
= B(S) union union_{pair {a,b} subset S} F({a,b,v})
```

と差分更新できる。

したがって各ノードで全候補×全patternを走査する必要はなく、`C(|S|,2)` 回の table lookup + bitwise OR で合法手集合を更新できる。

この差分更新は exact unique gain 計算にも再利用できる。

## 10. 現在の研究上の見取り図

3石段階では fixed rule の immediate gain は単なる雑な近似ではなく、**相手の次のsafe candidateを何個消すかを厳密に最大化**している。それにもかかわらず最大反例でLOSSになる。

したがって不足しているのは「何個消したか」の計算精度ではなく、

> **どの候補を消し、残った候補集合が敵対的なゲーム木でどの価値を持つか**

という構造。

最大反例2件は同じ `{9,33}` 10点円モチーフを共有するので、2つを完全独立なサンプルとして扱うのは危険。

現時点では、局所特徴をさらに大量に追加するより **盲検7 LOSS親の真の solver 分岐を直接測る**方が優先度が高い。

## 11. 次の実験（定義を固定してから新規7件へ適用）

優先順:

1. **盲検7親で fixed selected move の `(degree, X)` rank を記録**
   - `degree = s1+s2+s3`
   - `X = s1*s2+s1*s3+s2*s3`
   - `X` は degree tie-breaker として評価する。

2. **true solver child value を使った killer response 診断**
   - fixed move 後に、相手のどの応手がこちらをLOSSへ送るか
   - `killer_count`, `killer_fraction`, `best_killer_rank`, `top1/top3/top5 has killer`
   - 局所特徴の追加より真の勝敗木に直接近い。

3. **fixed rule の評価失敗 vs tie-break失敗を分離**
   - maximum-score set `T(S)`
   - true winning-move set `W(S)`
   - `P_C(S)=|T cap W|/|T|`
   - `P_C=0` なら score 自体の失敗、`0<P_C<1` なら tie-break 問題。
   - 最大反例2件の最初の手は一意首位なので、少なくとも入口は tie-break ではない。

4. **strategy-width / top-k forceability**
   - 真の勝者が fixed-rule 上位k手だけ使っても強制勝ちできる最小kを測る。
   - 「fixed rule 自体はよく、浅い敵対読みだけ足せばよい」のか、「勝ち筋が score順位から深く外れる」のかを切り分ける。

5. **探索器の高速化を先に実装**
   - D4 canonical transposition key
   - incremental danger mask / 3-stone completion table
   - これにより batch0 部分探索を全batch化しやすくする。

## 12. 研究上の注意

- 新規LOSS7件は既にblind replicationに使われたデータなので、後続特徴量をそこへ当てるときは **特徴量定義を先に固定**する。
- 最大反例 `4,9,33` と `9,19,33` は同じ `{9,33}` 10点円モチーフを共有するため、2独立反例として強く数えすぎない。
- post-hoc に見つかった閾値（entropy, weak-response率, graph percentileなど）は、blind再検証なしに主結論へ昇格させない。
- 途中で訂正された数値は、この文書の現在値を優先する。

## 13. provenance

Blind replication baseline carried forward from:

```text
branch: probe-two-stone-subsets
commit: b5172a4
```

この branch / commit は 2026-09-05 時点の接続済み GitHub では解決できなかったため、この文書の追加解析と blind outcome table は分離して扱う。
