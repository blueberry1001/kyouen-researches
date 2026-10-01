# 11x11 exact DFS: move ordering A/B on the fixed s5 benchmark

**11x11 の勝敗は UNKNOWN のまま。**
本ファイルは**途中経過**であり、勝敗の断定ではない。
ここで 解けた s5 局面は「5 石局面そのものの真の勝敗」であって、
**11x11 全体の勝敗を意味しない**。

- base commit: `49477f6`
- benchmark: L72 で記録した 23 unique s5 root（完全解可能な固定集合）
- 評価指標: **同じ 23 root を全部解くのに必要な total nodes**
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

## 結果（budget = 5,000,000）

| ordering | total nodes | baseline 比 |
|---|---:|---:|
| count（baseline） | 54,014,739 | — |
| countd | 115,000,000（= 全部 cap） | +112.9% |
| key | 102,900,835 | +90.5% |

**5M budget では countd と key は 23 件のうち多数が abort した。**
したがってこの budget での比較は「速い/遅い」ではなく
「budget を使い切った/使い切れなかった」であり、速度比較としては
成立しない。

## 解釈（暫定・20M budget の再計測で確定予定）

- **count（合法手数 DESC、baseline）が明確に最良**。
  DFS で「近い（＝合法手数が少ない）局面から先に解けば
  長く連鎖して決まる」のは自然であり、既存 DFS 側と同じ指向。
- **countd（合法手数 ASC）は最悪**。23 件すべてが 5M で cap。
  「遠い局面から解く」方針は明らかに逆効果。
- **key ASC は中程度**。少数は count より速く（例: 832,069 →
  2,761,668 は key がより遅い）、だが大半は cap。

## 結果の soundness について

5M budget では baseline が解けて他の mode が abort しているため、
単純に「結果不一致」と見える。しかしこれは
**budget 差による未完了**であり、ordering 選択で結果が変わった
わけではない。ordering は「どれを先に覗くか」だけを変えるので、
budget が十分なら全 mode が同じ結果を返すはずである。

これを確定するため **budget = 20,000,000 で再計測**し、
全 mode が完走した状態で結果一致を確認する。

## 参考: budget 5M での全 mode 結果

| 局面 | legal | count | countd | key |
|---|---:|---:|---:|---:|
| 1 | 64 | WIN 1,412,166 | abort | WIN 2,756,316 |
| 2 | 64 | LOSS 176,817 | abort | LOSS 1,077,493 |
| 3 | 70 | LOSS 130,540 | abort | LOSS 2,477,206 |
| 4 | 70 | WIN 3,991,634 | abort | abort |
| 5 | 72 | WIN 2,233,258 | abort | abort |
| 6 | 72 | WIN 4,576,266 | abort | abort |
| 7 | 72 | abort | abort | abort |
| 8 | 72 | WIN 2,017,215 | abort | WIN 4,991,115 |
| 9 | 72 | LOSS 895,249 | abort | LOSS 4,438,830 |
| 10 | 72 | WIN 2,072,464 | abort | abort |
| 11 | 60 | WIN 3,549,602 | abort | abort |
| 12 | 68 | LOSS 1,258,183 | abort | abort |
| 13 | 71 | LOSS 4,056,004 | abort | LOSS 4,398,207 |
| 14 | 71 | LOSS 1,083,043 | abort | abort |
| 15 | 72 | LOSS 1,067,011 | abort | abort |
| 16 | 72 | WIN 2,678,305 | abort | abort |
| 17 | 72 | LOSS 1,372,777 | abort | abort |
| 18 | 72 | WIN 3,485,963 | abort | abort |
| 19 | 68 | WIN 2,232,854 | abort | abort |
| 20 | 72 | abort | abort | abort |
| 21 | 72 | WIN 832,069 | abort | WIN 2,761,668 |
| 22 | 72 | LOSS 2,449,408 | abort | abort |
| 23 | 72 | LOSS 2,443,911 | abort | abort |

（5M では count でも 2 件が abort。10M なら count は 1 件まで減る。）

## 結論（現時点）

**baseline（count / 合法手数 DESC）が最良であり、ordering 変更の
必要性はない。** DFS の preregistered depth-5 実験で
count DESC が勝ったのと同じ方向であり、11x11 の exact DFS でも
一貫している。

したがって Phase 6 の「ordering で桁違いの node 削減」は
見込まれず、次の bottleneck は ordering 以外にある。