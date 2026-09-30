# 11x11 中央 v=60: baseline vs exact-hybrid の root 直下 20 返信

**11x11 の勝敗は UNKNOWN のまま。**
この測定では 20 返信のどれも WIN/LOSS に確定していない。

## 条件

- root: 中央初手 `v=60`
- budget: 300 s
- fresh process / fresh TT
- GitHub-hosted runner
- memo: `2^25 = 33,554,432`
- baseline: exact handoff 無効
- hybrid: `exact-legal=44`, `exact-budget=200000`, retries=2
- 両 arm とも `--children`

commit 系列: `f7f7498` の child diagnostic workflow。
solver は当時の publish-all exact handoff。

## root 全体

| arm | outcome | root pn | root dn | df-pn expansions | TT solved | exact nodes |
|---|---|---:|---:|---:|---:|---:|
| baseline | TIMEOUT | 91,764 | 17,148 | 7,339,905 | 8 | 0 |
| hybrid L44 | TIMEOUT | 10,527 | 5,544 | 4,864,881 | 32,913,473 | 37,300,356 |

**proof number の大小を「証明までの距離」とは解釈しない。**
この表の重要点は、hybrid が大量の exact subgame を完全解決して TT に戻している
一方で、root 自体は未解決ということ。

hybrid の TT occupancy は
`33,013,485 / 33,554,432` まで上がった。
このため main df-pn TT を exact の深い solved state で埋める設計が最適かは別途検証する。

## 20 返信の最終状態

全 20 行とも `st=1 (OPEN)`。**direct child solved = 0 / 20**。

| reply | baseline pn | baseline dn | hybrid pn | hybrid dn | hybrid work |
|---:|---:|---:|---:|---:|---:|
| 0 | 4,114 | 17,150 | 855 | 5,583 | 246 |
| 1 | 5,820 | 17,149 | 118 | 6,399 | 59 |
| 2 | 5,737 | 17,149 | 118 | 5,711 | 46 |
| 3 | 5,546 | 17,148 | 118 | 5,721 | 50 |
| 4 | 5,599 | 17,148 | 114 | 5,651 | 42 |
| 5 | 3,936 | 17,148 | 1,445 | 5,556 | 323 |
| 12 | 3,840 | 17,148 | 860 | 5,544 | 213 |
| 13 | 5,445 | 17,157 | 117 | 5,634 | 28 |
| 14 | 5,056 | 17,157 | 118 | 5,625 | 56 |
| 15 | 5,538 | 17,149 | 118 | 5,567 | 58 |
| 16 | 3,974 | 17,150 | 347 | 5,545 | 152 |
| 24 | 3,645 | 17,149 | 1,195 | 5,547 | 266 |
| 25 | 5,460 | 17,149 | 118 | 5,645 | 49 |
| 26 | 5,393 | 17,148 | 118 | 5,610 | 66 |
| 27 | 3,854 | 17,151 | 829 | 5,545 | 214 |
| 36 | 3,637 | 17,156 | 816 | 5,554 | 201 |
| 37 | 4,954 | 17,159 | 117 | 5,552 | 51 |
| 38 | 3,808 | 17,150 | 278 | 5,545 | 142 |
| 48 | 3,091 | 17,519 | 1,612 | 5,545 | 300 |
| 49 | 3,317 | 19,124 | 1,116 | 5,550 | 201 |

## 解釈

1. **大量の exact solved state は direct child の解決にはまだ到達していない。**
   3,000 万超の TT solved entry があっても、中央直下の 20 返信は全て OPEN。
   したがって global `solved` 数だけを進捗指標にしてはいけない。

2. hybrid arm では root から各 child への df-pn descent 回数 `work` が
   baseline より大幅に少ない。これは exact DFS が descent の下で大量の仕事を
   引き受けるためであり、単純に「探索が少ない」とは解釈しない。

3. 20 返信の pn/dn は大きく変わっているが、proof number は距離ではない。
   direct proof progress として確実に言えるのは、今回 **0/20 solved** だったこと。

4. publish-all hybrid は 5 分で main TT をほぼ満杯まで使った。
   そこで次の実験として、exact DFS 内部は local memo で解き、
   **handoff root だけを main df-pn TT に publish**する mode を実装している。
   目的は「deep solved state の再利用」と「df-pn open bound の保持」の
   トレードオフを測ること。

## 結論

hybrid は 11x11 frontier で確実に大量の exact work を実行しているが、
5 分では中央直下の 20 返信を 1 つも閉じなかった。

したがって現時点では

- 「hybrid で中央証明が近い」
- 「pn が小さい返信ほど残り時間が短い」

とは言わない。

**11x11 は UNKNOWN のまま。**
