# LOSS-edge cover: safe edge + canonical s4 class への修正

**11×11: UNKNOWN**

- base commit: `2f564f0`
- 対象: first=60, r2=0

## 修正 1: 不正な s4 辺の除去

前の実装は 119 頂点の**全ペア**（7021 通り）を辺として扱っていた。
しかし 4 手目として安全でないペアも含まれる。
例えば `{0,60,12,24}` は、0=(0,0), 12=(1,1), 24=(2,2), 60=(5,5) で
4 点共線なので、m3=12 のあとに m4=24 を置くことはできない。

`classify_edge()` は「石の重複」しか検査しておらず、
4 石局面が既に禁止 4 点組を含むかを確認していなかった。
`legal_for()` は「次の手の危険性」を計算する関数なので、
「現在の 4 石が既に unsafe」という状態を検出できない。

**修正**: `legal_moves_from()` を追加し、m3=a ごとに
**実際の合法 4 手目**を生成し、その中の b だけを
unordered pair `{min(a,b), max(a,b)}` として登録する。
ゲーム本体の合法手生成を使うので、判定が二重化しない。

**実測（修正後）**:

```
all_pairs=7021  safe_edges=6894  classes=3396
```

7021 - 6894 = **127 unsafe pair** で、これは指摘どおり。

## 修正 2: terminal s4 の verdict

前の判定は

```cpp
else if(e.unknown_children==0 && e.loss_children>0) LOSS;
```

だったが、**合法な m5 が 0 個の s4 は OR terminal なので LOSS** である。
`loss_children>0` は不要で、正しくは:

```cpp
if(win_children>0)        -> WIN
else if(unknown_children>0) -> UNKNOWN
else                      -> LOSS     // 空の子集合も LOSS に入る
```

## 修正 3: canonical s4 class への縮約

同じ canonical s4 を持つ辺は**同じ局面**なので、
証明材料としては 1 個の proof object である。

```
proof object 1 個
  canonical key: 1152921504606846983,0
  representative edges: 4 本
  covers: {1, 2, 11, 22}
```

**実測（修正後、r2=0）**:

```
vertices=119  safe_edges=6894  classes=3396
classes_loss=1  classes_win=0  classes_unknown=3395
cover_class,1152921504606846983,0,covers=4,edges=4,1,2,11,22
# COVER covered=4/119 classes_used=1
```

**1 本の証明で 4 頂点**カバー。前の実装が「2 本の辺」と数えていた
のは同じ証明を重複計上していたため。

## 二石 root 判定の統一的な表現

```
m3=a が LOSS  <=>  a に incident な safe s4 class に LOSS が 1 つ
m3=a が WIN   <=>  a に incident な safe s4 class がすべて WIN
r2 が LOSS     <=>  全 119 頂点が LOSS class で covered
r2 が WIN      <=>  どれか 1 頂点で incident class がすべて WIN
```

証明側と反証側が同じデータ構造で扱える。

## 現在の正確な状態

**LOSS proof class 1 個、covered 4/119。**

{60,0,1,2} の LOSS 証明は有効であり、
class 1152921504606846983,0 として 1 個の証明になる。
残る 115 頂点には s4 class の証明が必要。

- reply r2=0 が LOSS とは**まだ言っていない**
- 二石 root は 1 個も閉じていない

## 検証

- 回帰: hybrid n=4 LOSS / n=5 WIN / n=6 WIN / n=7 LOSS、
  adaptive 全条件 pass
- cache 堅牢化 5 ケース全 pass（矛盾 verdict 拒否、
  外部ヘッダ拒否、UNKNOWN 無視、再保存で行数不変）
- **11×11: UNKNOWN**
