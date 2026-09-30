# 11x11 中央 v=60: 20 返信を root-only hybrid で直接 sweep

**11x11 の勝敗は UNKNOWN のまま。**
中央後の D4 非同値 20 返信を、それぞれ二石 root `{60,r}` として
30 秒ずつ直接 df-pn + exact DFS で探索したが、**WIN 0 / LOSS 0 / TIMEOUT 20**。

## 条件

- 20 roots:
  `0,1,2,3,4,5,12,13,14,15,16,24,25,26,27,36,37,38,48,49`
- 1 process、20 roots 間で df-pn TT を共有
- 30 s / root、1 round、合計 600 s
- memo: `2^25`
- exact handoff: `legal <= 44`
- exact budget: 200,000 nodes / handoff
- retries: 2
- exact publish: **root-only**
- order: forward
- この実行は root-only の初期 unordered-map local cache 版。
  後続で fixed flat local memo へ高速化済み。

## 結果

| reply | outcome | pn | dn | df-pn expansions | main TT solved |
|---:|---|---:|---:|---:|---:|
| 0 | TIMEOUT | 2,440 | 7,675 | 183,004 | 992 |
| 1 | TIMEOUT | 4,830 | 13,397 | 502,165 | 1,514 |
| 2 | TIMEOUT | 4,290 | 11,518 | 346,450 | 2,223 |
| 3 | TIMEOUT | 4,321 | 12,704 | 303,019 | 3,620 |
| 4 | TIMEOUT | 3,791 | 11,767 | 216,253 | 4,678 |
| 5 | TIMEOUT | 1,461 | 5,107 | 37,710 | 5,574 |
| 12 | TIMEOUT | 1,425 | 4,801 | 34,453 | 8,159 |
| 13 | TIMEOUT | 3,704 | 11,401 | 166,973 | 9,204 |
| 14 | TIMEOUT | 3,376 | 10,739 | 123,129 | 9,936 |
| 15 | TIMEOUT | 3,320 | 11,029 | 92,045 | 11,509 |
| 16 | TIMEOUT | 1,528 | 5,331 | 21,274 | 12,307 |
| 24 | TIMEOUT | 1,382 | 4,599 | 13,051 | 13,000 |
| 25 | TIMEOUT | 3,276 | 10,670 | 63,578 | 14,109 |
| 26 | TIMEOUT | 3,020 | 9,120 | 43,909 | 14,756 |
| 27 | TIMEOUT | 1,335 | 5,159 | 11,720 | 15,346 |
| 36 | TIMEOUT | 952 | 5,162 | 5,247 | 16,043 |
| 37 | TIMEOUT | 2,954 | 8,777 | 31,703 | 16,864 |
| 38 | TIMEOUT | 1,645 | 5,752 | 12,995 | 17,685 |
| 48 | TIMEOUT | 1,447 | 4,708 | 10,710 | 18,427 |
| 49 | TIMEOUT | 1,332 | 4,769 | 9,376 | 19,683 |

**pn/dn を解決までの距離として読まない。**
小さい pn の root が「あと少し」という意味ではない。

## 共有 TT / exact work

最終 root `{60,49}` の時点:

- cumulative wall: 600 s
- main TT used: 2,228,764 / 33,554,432
- main TT solved: 19,683
- evict open / solved: **0 / 0**
- cumulative exact calls: 16,398
- cumulative exact nodes: **252,755,968**
- cumulative exact abort: **2**
- exact trigger WIN / LOSS: 9,061 / 7,316
- handoff-root stores: 16,377

つまり約 2.53 億 exact node を追加で処理し、ほぼ全 handoff が budget 内に
完全解決したが、二石 root 自体は 1 件も閉じなかった。

後半 root の df-pn expansions が大幅に小さいのは shared TT が温まった影響を
含む。これを「後半 root の方が本質的に易しい」とは解釈しない。

## 解釈

この実験は、親 `{60}` の AND-node 内で探索配分が偏っていたため direct child が
閉じなかった、という可能性をチェックしたもの。

各二石局面を**直接 root として30秒ずつ**与えても 20/20 TIMEOUT だったため、

> 「中央20返信のうち、短時間 hybrid なら簡単に証明できる返信が多数ある」

という期待には否定的な結果。

一方、L44 exact handoff 自体は abort ほぼ0で安定している。
60秒 threshold scan では L52/L56 まで上げても多くの handoff が完了しており、
より上流で exact DFS に渡す余地がある。

次の測定は同じ20返信を **L56** で 30秒ずつ。
これでも direct WIN/LOSS が出なければ、単純に handoff threshold を上げるだけで
中央証明が急に閉じる可能性は低くなる。

**11x11 は UNKNOWN のまま。**
