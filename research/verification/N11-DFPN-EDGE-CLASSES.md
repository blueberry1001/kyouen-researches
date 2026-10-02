# s4 class の検証: concyclic 規則と histogram の訂正

**11×11: UNKNOWN**

- base commit: `38768a5`
- 対象: first=60, r2=0

## 訂正 1: 独立 checker が共線だけを見ていた

`dfpn_edge_classes.py` は共線（cross product == 0）だけで
禁止 4 点組を判定していた。しかしゲームの規則は**共円**である。

`build_forbidden_quadruples()` が使うのは、行

```
[ x*x + y*y,  x,  y,  1 ]
```
からなる 4x4 行列式で、これは 4 点が同一円上にあるとき 0 になる
（直線は半径無限大の円として含まれるので、共線 4 点も含む）。

したがって共線だけを見る実装は**真に弱い**であり、
`{0,5,55,60}` は共線ではないが共円なので、solvers 側は正しく拒否し
Python 側は 6985 辺と数えていた。checker を determinant 規定で
書き直したところ、**C++ と完全に一致した**:

```
vertices=119  all_pairs=7021  safe_edges=6894
unsafe pairs rejected=127  canonical s4 classes=3396
```

## 訂正 2: coverage histogram

独立 checker（concyclic 規定）で数えた結果:

```
coverage 2:  51 classes
coverage 3: 437
coverage 4: 2832
coverage 5:  33
coverage 6:  43
合計 3396、max coverage 6、ceil(119/6)=20
```

**前 commit message の「2872 of 3396 classes cover exactly 4」は
誤記で、正しくは 2832。** 指摘どおり。
`max=6` と `ceil(119/6)=20` は一致していた。

solver 側も coverage histogram を出力するようにし、
独立 checker と**完全一致**することを確認した:

```
# coverage cov2=51 cov3=437 cov4=2832 cov5=33 cov6=43 max=6 lower_bound=20
```

## 修正 3: class 内の verdict 不整合を throw

前実装は同一 class 内の各 raw edge について

```cpp
if((int)ei.verdict > v) v=(int)ei.verdict;
```

としていた。UNKNOWN=0, WIN=1, LOSS=2 なので、
同一 class に WIN と LOSS が混在すると **LOSS が黙って勝つ**。
同じ canonical s4 は真の verdict が必ず一致するので、
これは誤証明に直結する形である。

**修正**: class 内で確定 verdict が食い違えば **throw** する。
UNKNOWN は「何も言わない」ので混在チェックから除外する。

## 修正 4: 表示バグ

```
cover_class,...,covers=4,edges=4,1,2,11,22
```

`edges=4` は raw edge 数ではなく端点集めの要素数だった。
この class の raw edge は (1,2) と (11,22) の **2 本**。
字段名を `raw_edges=` にし、正しく 2 が出るようにした。

```
cover_class,1152921504606846983,0,covers=4,raw_edges=2,1,2,11,22
```

「proof class 1 個・covered 4 頂点」という本質には影響しない。

## 並列 driver の単位

今後の研究単位は **canonical s4 class** である。
既に「1 つの s4 証明が D4 経由で 4 個の m3 を同時に潰す」ことを
実証済みで、coverage 6 の class も 43 個ある。

未知 class の優先度は

```
priority = (fresh coverage DESC, unknown s5 children ASC)
```

で取ればよい。ただし「coverage が大きい class ほど LOSS になりやすい」
という根拠はまだ無いので、そこは**実測で判断すべき**である。

s4 verdict を永続化すれば、次回以降は class を構成する s5 を
再走査する必要もなくなる。

## 現状

**LOSS proof class 1 個、covered 4/119。**

reply r2=0 が LOSS とはまだ言っていない。
二石 root は 1 個も閉じていない。

## 検証

- 回帰: hybrid n=4 LOSS / n=5 WIN / n=6 WIN / n=7 LOSS、
  adaptive 全条件 pass
- cache 堅牢化 5 ケース全 pass
- checker と solver の辺数・class 数・histogram が完全一致
- **11×11: UNKNOWN**
