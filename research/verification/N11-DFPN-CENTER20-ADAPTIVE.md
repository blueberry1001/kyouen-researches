# central 20 replies: adaptive s5 budget での再 sweep

**11x11 の勝敗は UNKNOWN のまま。**
`SUMMARY WIN=0 LOSS=0 TIMEOUT=20 MISSING=0 TOTAL=20`

**20 返信のどれも依然として閉じていない。** ただし前回
（L44/L56, exact-budget=200k, WIN 0 / LOSS 0 / TIMEOUT 20）と
比べ、**探索の到達点が若干ORDER 改善している**。

- script: `research/verification/scripts/dfpn_center20_adaptive_sweep.sh`
- 機械: WSL / g++ -O3 -march=native、16 cores / 19 GB RAM
- memo: 2^26 = 67,108,864（shared TT、20 root 連続）
- budget: 60 s / root、ROUNDS=1、L72、exact-retries=1、publish=root
- exact budget: global 200k + **per-stone s5:5,000,000, s6:200,000**
- 実測 wall: 約 20 分

## 結果（root ごとの最終値）

| reply | outcome | root_pn | root_dn | exact_win(累積) | exact_abort(累積) |
|---:|---|---:|---:|---:|---:|
| 0 | TIMEOUT | 95 | 888 | 73 | 30 |
| 1 | TIMEOUT | 161 | 10,333 | 114 | 90 |
| 2 | TIMEOUT | 102 | 1,293 | 162 | 131 |
| 3 | TIMEOUT | 160 | 9,905 | 250 | 185 |
| 4 | TIMEOUT | 108 | 2,115 | 344 | 235 |
| 5 | TIMEOUT | 55 | 979 | 347 | 236 |
| 12 | TIMEOUT | 55 | 692 | 353 | 249 |
| 13 | TIMEOUT | 117 | 2,830 | 418 | 305 |
| 14 | TIMEOUT | 118 | 4,759 | 461 | 342 |
| 15 | TIMEOUT | 112 | 2,490 | 580 | 375 |
| 16 | TIMEOUT | 55 | 1,334 | 580 | 376 |
| 24 | TIMEOUT | 55 | 1,030 | 611 | 381 |
| 25 | TIMEOUT | 117 | 4,016 | 706 | 419 |
| 26 | TIMEOUT | 97 | 2,774 | 714 | 425 |
| 27 | TIMEOUT | 95 | 1,274 | 735 | 447 |
| 36 | TIMEOUT | **30** | 848 | 735 | 449 |
| 37 | TIMEOUT | 103 | 3,039 | 801 | 500 |
| 38 | TIMEOUT | 93 | 1,699 | 832 | 547 |
| 48 | TIMEOUT | 55 | 1,487 | 833 | 548 |
| 49 | TIMEOUT | 92 | 1,461 | 859 | 560 |

累積 exact-depth histogram（sweep 全体）:
`[exact-depth] s5=49/5/19/15 s6=1409/854/0/545 (call/win/loss/abort)`

exact nodes 合計: **3,589,844,992**（約 35.9 億）
df-pn expansions 合計: 56,731
main TT eviction: **0 / 0**（root-only publish を維持）

## 前回との比較

| | L44/L56（前回） | adaptive L72（今回） |
|---|---:|---:|
| WIN / LOSS / TIMEOUT | 0 / 0 / 20 | 0 / 0 / 20 |
| 二石 root の root_pn | 未記録（数百〜数千程度） | **30 〜 161** |

`root_pn` が 2 桁下がっている点が今回の主な変化。ただし
**pn は距離ではない**ため、これは「解に近い」的意味ではない。
exact が 2 石局面の下位層をかなり削っていることの反映と解釈すべき。

## s5 予算が効いたことの確認

**s5 で 5 WIN / 19 LOSS が出ている**。前回は s5 は 0 WIN だった。
ただしこれらは二石 root そのものの結果ではなく、
二石 root の**下位層にある s5 局面**の結果である。
二石 root が 20 個とも TIMEOUT であることを変えるものではない。

## 解釈の注意

- **20 返信のどれもまだ閉じていない**。中央勝ちには 20 全部の
  WIN が必要であり、少なくとも 1 つでも LOSS があれば中央は反証される。
  現状はどちらでもない = UNKNOWN のまま。
- `root_pn=30`（r=36）でも **TIMEOUT** である。pn が小さいことは
  証明済みであることを意味しない。
- shared TT による cross-root 効果は前回測定済みだが、
  今回の主因は adaptive s5 予算の導入である
  （最初の root r=0 単独でも root_pn=95 に達している）。

## 記録

- 本ファイルは**途中経過**であり、勝敗の断定ではない。
- 20 返信すべて TIMEOUT、`MISSING=0`（記録漏れなし）。
- raw log: `/mnt/d/ghq/build11/logs/c20_adaptive/c20.log` と `c20.csv`