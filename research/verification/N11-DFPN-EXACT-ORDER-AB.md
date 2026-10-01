# 11x11 exact DFS: move ordering A/B on the fixed s5 benchmark

**11x11 の勝敗は UNKNOWN のまま。**
本ファイルは**途中経過**であり、勝敗の断定ではない。
ここで解けた s5 局面は「5 石局面そのものの真の勝敗」であって、
**11x11 全体の勝敗を意味しない**。

- base commit: `49477f6`
- benchmark: L72 で記録した 23 unique s5 root（完全解可能な固定集合）
- 評価指標: **同じ 23 root を全部解くのに必要な node 数**
  （proof number ではなく、具体的な node 数で比較する）
- 機械: WSL / g++ -O3 -march=native、16 cores / 19 GB RAM
- memo: 2^22（row ごと）、swap 使用 0

## 実装した ordering

`--exact-order=count|countd|key`

- **count**（baseline）: 決定的子優先、その次は **合法手数 DESC**
- **countd**: 決定的子優先、その次は **合法手数 ASC**
- **key**: 決定的子優先、その次は **canonical key ASC**（count を見ない）

「決定的子優先」（OR なら既に解けた WIN 子、AND なら LOSS 子を先頭へ）
は全 mode で共通であり、探索を早期打ち切りできる唯一の部分。
そのため各 mode を**一度に一つだけ**変えられるようにしてある。

選択した ordering は run ヘッダと replay CSV の先頭コメント行に
記録しているので、benchmark を誤った rule に帰属させることはない。

## 結果（budget = 5,000,000）

| ordering | 解けた局面 | 解けた分だけ total nodes | 平均 nodes |
|---|---:|---:|---:|
| count（baseline） | **21 / 23** | 44,014,739 | 2,095,939 |
| countd | **0 / 23** | 0 | — |
| key | **7 / 23** | 22,900,835 | 3,271,547 |

5M では countd と key の大半が budget を使い切った。
この budget での比較は「速い / 遅い」ではなく
「budget を使い切った / 使い切れなかった」であり、
速度比較としては成立しない。

## 結果（budget = 20,000,000）

| ordering | 解けた局面 | 解けた分だけ total nodes | 平均 nodes |
|---|---:|---:|---:|
| count（baseline） | **23 / 23** | 55,010,745 | 2,391,771 |
| countd | 3 / 23 | 28,782,914 | 9,594,304 |
| key | 13 / 23 | 108,301,404 | 8,330,877 |

**3 mode すべてが解けた 3 局面に絞った同条件比較**
（budget をあきらめずに純粋な速度差だけを見る）:

| ordering | total nodes | count 比 |
|---|---:|---:|
| count（baseline） | 2,484,232 | — |
| key | 8,272,639 | **+233.0%**（約 3.3 倍） |
| countd | 28,782,914 | **+1058.6%**（約 11.6 倍） |

## 判定

**baseline（count / 合法手数 DESC）が明確に最良。**
他の 2 mode は「窮屈な budget なら解ける」程度であり、
同じ条件では 3.3 倍〜11.6 倍の node を無駄にする。

DFS で「近い（合法手数が少ない）局面から先に解けば
長く連鎖して決まる」のは自然であり、既存 DFS 側の
事前登録済み depth-5 実験（count DESC 勝ち）と同じ指向で、
11x11 exact frontier でも一貫している。

**したがって Phase 6 の「ordering で桁違いの node 削減」は見込まれない。
次の bottleneck は ordering 以外にある。**

## 測定方法上の注意

「解けた局面の総 nodes」を比較すると、budget で先に諦めた mode の
ほうが有利に誤って見える。本比較では

1. **解けた局面数**（coverage）を主指標とし、
2. 全 mode が解けた局面に絞った node 数（純粋な速度差）を副指標とした。

両者が一致しない場合、nodes 指標だけでは誤解を招く。

## 結果の soundness について

5M/20M では baseline が解けて他の mode が abort しているため、
単純に「結果不一致」と見える。これは **budget 差による未完了**であり、
ordering 選択で結果が変わったわけではない。ordering は
「どれを先に覗くか」だけを変えるので、budget が十分なら
全 mode が同じ結果を返すはずである。

20M かつ全 mode が解けた 3 局面について、結果は
3 mode すべて一致している（mismatch 0）。

## correctness regression

ordering フラグ追加後も、hybrid 回帰は前回と完全に一致
（n=4 LOSS / n=5 WIN / n=6 WIN / n=7 LOSS、exact-legal 0/4/6/8、
publish all/root/separate、forced-abort arm 801,180 abort）。
default が count-desc のままであるため、当然同じ結果になる。

## 結論

**ordering 変更は不要。** baseline を維持する。
残る bottleneck は「s5 より上の層（s6 の sibling、s7 以降）」の
difficulty にある。