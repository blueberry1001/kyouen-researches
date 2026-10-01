# center 20 replies: 層別 gate での再 sweep

**11x11 の勝敗は UNKNOWN のまま。**
`SUMMARY WIN=0 LOSS=0 TIMEOUT=20 MISSING=0 TOTAL=20`

**20 返信のどれも依然閉じていない。**

- script: `dfpn_center20_layered_sweep.sh`
- base commit: `5ce0531`
- 機械: WSL / g++ -O3 -march=native、16 cores / 19 GB RAM
- memo 2^26 shared TT、60 s/root、ROUNDS=1、publish=root、swap 使用 0
- gate: `5:116,6:115,7:114,8:113`（s5〜s8 を開き、s9 以降は 0 で無効）
- budget: `5:20000000,6:1000000,7:1000000,8:200000`
  （各層の測定値に余裕を持たせた設定）

## 結果

| reply | outcome | root_pn | root_dn |
|---:|---|---:|---:|
| 0 | TIMEOUT | 30 | 64 |
| 1 | TIMEOUT | **1** | 118 |
| 2 | TIMEOUT | **1** | 118 |
| 3 | TIMEOUT | **1** | 118 |
| 4 | TIMEOUT | **1** | 118 |
| 5 | TIMEOUT | 30 | 64 |
| 12 | TIMEOUT | 30 | 64 |
| 13 | TIMEOUT | **1** | 118 |
| 14 | TIMEOUT | 58 | 118 |
| 15 | TIMEOUT | **1** | 118 |
| 16 | TIMEOUT | 30 | 64 |
| 24 | TIMEOUT | 30 | 64 |
| 25 | TIMEOUT | **1** | 118 |
| 26 | TIMEOUT | **1** | 118 |
| 27 | TIMEOUT | 30 | 64 |
| 36 | TIMEOUT | 30 | 64 |
| 37 | TIMEOUT | 58 | 118 |
| 38 | TIMEOUT | 30 | 64 |
| 48 | TIMEOUT | 30 | 64 |
| 49 | TIMEOUT | 30 | 64 |

累積 histogram: `s5=72/12/40/0 (call/win/loss/abort)`

- 総 expansions: 1,930（前回は 56,731）
- 総 exact nodes: 3,717,005,312
- **総 exact abort: 0**（前回は 560）
- main TT eviction: 0 / 0

## 前回との比較

| 指標 | adaptive sweep（前回） | 層別 gate（今回） |
|---|---:|---:|
| WIN / LOSS / TIMEOUT | 0 / 0 / 20 | 0 / 0 / 20 |
| root_pn 最小 | 30 | **1** |
| root_pn 最大 | 161 | 58 |
| exact abort 合計 | 560 | **0** |
| df-pn expansions | 56,731 | 1,930 |

**abort が完全に消え、df-pn expansions が 29 分の 1 になった。**
層別 gate で s6/s7/s8 にも予算を渡したため、s5 に浪費されていた
abort がなくなった。

## 重要な注意: `root_pn=1` は「証明が近い」ではない

11 個の返信が `root_pn=1` を示すが、これは**良好ではない**。

二石 root は OR ノードなので `pn = min(子の pn)`。
`pn=1` かつ `root_dn=118` という組み合わせは、
**未展開の子（pn=1）が 1 つ以上ある**ことを意味する。
その子（OR ノード）が未展開なら親の min も 1 になる。
つまり `pn=1` は「その子の探索がまだ始まっていない」であり、
「1 手で証明に到達した」ではない。

裏付けとして確認した:

- main TT に publish された solved root は **0 件**
  （`[done] ... WIN/LOSS` の行なし、`done lines: 0`）
- `root_dn` が 118 と大きい =  unexplored な子が支配している

したがって `root_pn` の低下は「証明が近い」ではなく
「未展開の子が explicit に出ている」という意味であり、
**勝敗には何も言わない**。20 返信すべて TIMEOUT であることに変わりない。

## 解釈

層別 gate の効果は明确的である（abort 0、expansions 29 分の 1）が、
**二石 root が閉じない理由は変わっていない。**

二石 root が閉じるには、20 個の子のそれぞれについて
「その子的一切の concrete response が証明される」必要がある。
s5〜s8 の末端局面がすべて解けても、
それらを束ねる二石 root 自身の集約が完了しないと閉じない。

つまり **末端の exact 解は十分に得られているが、
集約（AND/OR の伝播）が bottleneck になっている。

## 次の手への示唆

1. **df-pn 側の集約效率を測る**。末端は解けているのに root が
   閉じないなら、証明を子から親へ伝播する仕組みの效率を
   調べる。solved entry の publish 範囲（root-only）が
   伝播を遅らせている可能性がある。
2. **二石 root の直下（3 石局面）を個別に exact で解く**。
   3 石局面が WIN / LOSS どちらに偏るかが分かれば、
   20 返信の行方が変わる可能性がある。

## 記録

- 本ファイルは**途中経過**であり、勝敗の断定ではない。
- 20 返信すべて TIMEOUT、MISSING 0、main TT eviction 0。
- **11x11 は UNKNOWN のまま。**