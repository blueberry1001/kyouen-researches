# 11x11 df-pn + exact endgame DFS handoff

**11x11 の勝敗は UNKNOWN のまま。**
この文書はアルゴリズム改善の検証記録であり、勝敗証明ではない。

## 実装

基準実装: `cpp/solvers/kyouen_dfpn_root.cpp`
初期 hybrid commit: `472d538`

df-pn を外側の探索として維持し、合法手数が小さい frontier node に到達したときだけ
exact DFS を試す。

オプション:

- `--exact-legal=N`: 合法手数 `<= N` で handoff。0 は無効
- `--exact-budget=N`: handoff 1 回あたりの exact DFS node budget
- `--exact-retries=N`: 同一 TT residency 中に再試行できる回数

exact DFS は fixed proposition「元の先手が最終的に勝つ」を直接評価する。
OR/AND は df-pn と同じ parity で、

- even stones: OR
- odd stones: AND

を使う。

**soundness の要点**:

- exact DFS が完全に解いた局面だけ `pn=0/dn=INF` または
  `pn=INF/dn=0` として TT に書く
- node budget を使い切った場合は `UNKNOWN` を返し、未解決 parent を
  solved として書かない
- exact DFS は同じ TT の既存 solved entry を再利用する
- open df-pn bound は exact DFS の真偽判定には使用しない
- TT slot が別 key に置換されたときは pn/dn/aux counter もリセットし、
  stale exact-attempt bit を引き継がない

heartbeat / timeout / done には以下を追加:

`exact_calls exact_nodes exact_abort exact_win exact_loss exact_stores`

## 正当性回帰

GitHub Actions:
`.github/workflows/n11-dfpn-hybrid-regression.yml`

既知空盤勝敗:

| n | expected |
|---:|---|
| 4 | LOSS |
| 5 | WIN |
| 6 | WIN |
| 7 | LOSS |

`exact-legal = 0,4,6,8` の全設定で上記と一致。

小盤では handoff が実際に動き、同じ結果のまま df-pn expansions が減った。
例として n=7:

| exact-legal | df-pn expansions | exact nodes | outcome |
|---:|---:|---:|---|
| 0 | 2,123,417 | 0 | LOSS |
| 4 | 1,080,990 | 327,138 | LOSS |
| 6 | 978,068 | 557,998 | LOSS |
| 8 | 661,662 | 556,438 | LOSS |

これは小盤上では hybrid が単なる dead code ではなく、正しい結果を保ったまま
endgame を exact DFS に移せていることを示す。ただしこの速度差をそのまま
11x11 に外挿しない。

### 強制 abort 試験

`exact-legal=8, exact-budget=1, exact-retries=2` として、
ほぼすべての handoff を意図的に `UNKNOWN` にした。

n=7 では:

- exact calls: 847,893
- exact abort: 801,180
- final outcome: **LOSS**（baseline と一致）
- df-pn expansions: 2,123,417（baseline と一致）

n=4..7 全てで最終勝敗は baseline と一致した。
したがって budget exhaustion が unsound な solved mark を注入していないことを
回帰で確認した。

## 11x11 60 秒 smoke test

GitHub-hosted runner 上の短時間診断。ユーザーの WSL 計測とはマシンが異なるため、
絶対速度の比較には使わない。同一 run 内の arm 比較と handoff の発火状況を見る。

条件:

- root: `v=60`
- budget: 60 s
- memo: `2^24`
- exact budget: 200,000 nodes / call
- retries: 2
- 各 arm fresh process

最終 baseline-vs-hybrid 同時比較:

| exact-legal | outcome | root pn | root dn | df-pn expansions | exact calls | exact nodes | exact solved stores |
|---:|---|---:|---:|---:|---:|---:|---:|
| 0 | TIMEOUT | 18,496 | 6,105 | 921,593 | 0 | 0 | 0 |
| 20 | TIMEOUT | 18,456 | 6,110 | 915,761 | 19 | 2,963 | 2,963 |
| 32 | TIMEOUT | 17,200 | 5,974 | 849,725 | 829 | 1,114,569 | 1,114,569 |
| 44 | TIMEOUT | 8,521 | 5,428 | 444,936 | 493 | 8,122,368 | 8,122,363 |

`exact-legal <= 12` は 60 秒では handoff が一度も発火せず、
16 で初めて少数発火した。現在の df-pn frontier に endgame DFS を
実際に当てるには 20 以上が必要。

`exact-legal=44` では約 812 万 exact state を完全に解き、
df-pn が選んだ frontier node の exact WIN/LOSS が大量に TT へ戻った。
ただし **root pn が baseline より小さいことを「証明に近い」とは読まない**。
proof number は残り作業量ではなく、精密化で増減するためである。

今回の意味のある観察は、

1. hybrid handoff が 11x11 の実探索 frontier で大量に発火する
2. handoff は 200k node cap 内でほぼ完了しており、短時間 smoke では
   `exact_abort=0`
3. exact による solved state が df-pn の選択中 frontier へ実際に注入される
4. それでも 60 秒では root 自体は未解決

という点。

## 現時点の判断

hybrid は **正しさ回帰を通過し、11x11 でも実際に仕事をしている**。
一方、まだ「11x11 証明時間を短縮した」とは言えない。
その判定には同じマシン・同じ wall time で baseline と hybrid を比較し、
最終 WIN/LOSS、critical frontier の solved 化、handoff の abort 率などを
見る必要がある。

次の本命は WSL 上で `exact-legal=0` と 32〜44 の 5 分 A/B。
特に `exact-legal=44` は短時間 run で exact work が大きいため、
memo=26 の容量で eviction / solved eviction を確認しながら測る。

**11x11 は UNKNOWN のまま。**
