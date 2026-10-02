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

## 最小 set cover: **OPT = 31**（ILP で確定）

**`OPT = 31` が ILP で確定した。**

```
min sum_C x_C   s.t.  sum_{C contains v} x_C >= 1   x_C in {0,1}

3396 変数・119 制約を scipy.optimize.milp（HiGHS）で解いた:

```
status=0   wall=0.10s   objective=31.0   mip_gap=0.0
selected classes = 31   union covers 119/119
coverage sizes: 3x8  4x21  5x1  6x1
OPTIMUM CERTIFIED = 31
```

`mip_gap = 0.0` かつ `status = 0` なので**最適性が証明済み**で、
単なる witness ではなく真の最適値である。

独立検証（`dfpn_cover_verify.py`、`cert_cover_ilp_forced.json`）:

```
  OK  (a) class count = 31
  OK  (b) all keys are legal canonical s4 classes
  OK  (d) all coverage sets match the recomputation
  OK  (c) union covers all 119 vertices (missing 0, spurious 0)
  OK  (e) known-proved LOSS class present
VERIFIED
```

### 既知 LOSS class を強制した版

素の ILP の 31 解は**既知の proved class を含んでいなかった**
（別の 31 解である）。.refutation certificate としては
既に支出した証明を再利用したいので、`x_known = 1` を強制して
解き直した:

```
status=0  wall=0.11s  objective=31.0  gap=0.0
selected=31  union=119/119  known present=True
coverage sizes: 3x8  4x21  5x1  6x1
OPTIMUM_WITH_KNOWN = 31
```

**既知 class を強制しても最適値は 31 のまま**であり、
その certificate も独立検証済み（(e) を含む 5 項目すべて OK）。

### 内訳の一致

報告された 31 解の内訳 `21×4 + 8×3 + 1×5 + 1×6` は
ILP が返した `4x21 3x8 5x1 6x1` と**完全に一致**する。
両者は互いに素な 119 頂点の partition である。

したがって当方の 35 class witness（`3x8 4x6 5x1 6x20`）は
最適ではなく、local improvement が大きな class を偏って
使っていたためである。

**撤回: 「limit 20..30 を除外したので OPT >= 31」**

この排除は `dfpn_cover_optimum.py` の `lower_bound()` に依存していたが、
その関数は fractional charge と disjointness charge を**加算していた**。
これは一般には正しくない。2 つの charge がそれぞれ有効な下界でも、
**同じ選択 class を二重に課金しうる**ので和は下界にならない。

最小反例は「頂点 1 個・それを覆う class 1 個」の set cover:

```
OPT = 1
fractional charge = 1
disjoint charge   = 1
sum               = 2   <- 下界になっていない
```

したがって `limit=20..30` を 1 node で除外していた部分は
**証明として使えない**。修正は `max(A, B)` であり、和ではない。
両者がそれぞれの下界ならその max も下界だが、加算的な結合は一般に不可。

**確定: `OPT = 31`。**

## 観測値（証明ではない）

```
vertices          : 119
classes           : 3396
distinct covers   : 2002   （coverage 集合が同一の class を統合）
max coverage      : 6
counting bound    : 20
greedy upper bound: 35
```

coverage 6 の class が 43 個、coverage 4 が 2832 個であり、
重なり制約が強いため単純 count は確かに弱い。

## 最適値を確定するには

set cover を 0-1 ILP として解く:

```
min  sum_C x_C
s.t. for all v:  sum_{C contains v} x_C >= 1
     x_C in {0,1}
```

3396 変数・119 制約。scipy.optimize.milp の HiGHS が使えれば
最適 witness を機械可読に出せる。optimal を返せばその選択 class を
既存の `dfpn_cover_verify.py` で独立検証する。時間切れなら
best bound と 35-class witness から区間だけを報告する。

**adaptive coordinator は OPT の確定を待たずに作れる。**
coordinator の正しさは最適値が 31 でも 35 でも変わらず、
変わるのは進捗指標の数字だけである。

## 報告された 31 class 解（未検証）

```
21 x coverage4  +  8 x coverage3  +  1 x coverage5  +  1 x coverage6  =  119
```

coverage 集合が互いに素で 119 頂点をちょうど partition する、という
主張であるが、**witness として検証されていない**。
上に記したとおり 31 class の具体解をまだ出力できていない。

## orbit による観測

## orbit による検証

固定 root `{60,0}` の stabilizer は恒等変換と主対角線反射の 2 元。
119 個の m3 はこの作用で:

- 55 個の 2 点 orbit
- 対角線上の 9 個の 1 点 orbit

= 計 64 orbit に落ちる。

現在の LOSS class `{1,2,11,22}` は raw では 4/119 だが、
orbit 単位では `{1,11}` と `{2,22}` の **2/64** を覆う。

1 class が覆える m3-orbit は最大 3 なので、この見方の単純下界は 22、
そこから実際の incidence をすべて考慮すると 31 になる（未検証）。

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
- 31-class optimum は ILP で確定、witness も独立検証済み

**11×11: UNKNOWN**

## 確認された witness（`dfpn_cover_witness.py` + `dfpn_cover_verify.py`）

machine-readable な witness を生成し、**別スクリプトで独立検証**した。

```
n_classes      : 35
coverage sizes : 3x8  4x6  5x1  6x20
union size     : 119 / 119
counting bound : 20
```

`dfpn_cover_verify.py` の検証結果（すべて OK）:

```
recomputed : 119 vertices, 3396 classes
witness    : 35 classes (claim 35)
  OK   (a) class count = 35
  OK   (b) all keys are legal canonical s4 classes
  OK   (d) all coverage sets match the recomputation
  OK   (c) union covers all 119 vertices (missing 0, spurious 0)
  OK   (e) known-proved LOSS class present
certified bounds (greedy witness) : 20 <= OPT <= 35
VERIFIED
```

**witness が 35 なので `OPT <= 35` は実証された。**

## 確定していること・していないこと

**確定**:

- `OPT >= 20`（単純 count）
- `OPT <= 35`（35 class の witness を生成し独立検証）
- 既知 LOSS class `{1,2,11,22}` は witness に含まれる

**未確定**:

- 最適値は 20 と 35 の間のどこか。
- この witness は local improvement による heuristic であり、
  最適値に到達する保証はない。

**最適値を確定するには 0-1 ILP として解く必要がある:**

```
min  sum_C x_C
s.t. for all v:  sum_{C contains v} x_C >= 1
     x_C in {0,1}
```

3396 変数・119 制約であり、scipy.optimize.milp の HiGHS が
使えるなら最適 witness を機械可読に出せる。
31 の witness が機械可読に 31 class を出力し、
ILP で 31 が確定した（上記）。

## 生成した witness の構造

35 class の内訳:

| coverage | class 数 |
|---:|---:|
| 3 | 8 |
| 4 | 6 |
| 5 | 1 |
| 6 | 20 |

coverage 6 の class を 20 個使っており、報告された 31 解の
「21×4 + 8×3 + 1×5 + 1×6」という分布とは大きく異なる。
local improvement が大きい class を優先して貪欲に固めているためで、
これは 31 解が存在するならその分布に近づいていないことを
示唆する。**31 witness を得るには別の探索が必要**（simulated annealing
や exact 探索の残りなど）。
