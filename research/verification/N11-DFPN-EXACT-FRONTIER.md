# 11x11 df-pn + exact hybrid: exact frontier の現状

**11x11 の勝敗は UNKNOWN のまま。**
本ファイルは **途中経過**であり、いかなる勝敗の主張も行っていない。

- solver: `cpp/solvers/kyouen_dfpn_root.cpp`
- base commit: `0813ac3`（"Scan handoff thresholds into the s5 frontier"）
- 機械: WSL / g++ -O3 -march=native、16 cores / 19 GB RAM

## 重要な読み方の注意（再掲）

- `pn` は「残り作業量」「あと何ノード」「証明までの距離」**ではない**。
  未展開の葉は最初 `(1,1)` で、探索が精密化する過程で**普通に大きくなる**。
  証明線が閉じた瞬間に初めて 0 になる。
  **小さい pn から時間を外挿してはならない。**
- `pn/dn` 比を勝率と呼んでいない。
- solved entry 総数だけを root の進捗とは見なさない。

## Phase 1: threshold scan（既存结果的再録）

root-only、v=60、60 s、memo=2^24、exact-budget=200k:

| level | root (pn,dn) | dfpn exp | exact calls | exact nodes | abort | exact WIN | exact LOSS |
|---|---|---:|---:|---:|---:|---:|---:|
| L60 | (1313,438) | 12,024 | 162 | 19,972,096 | 55 | 106 | 0 |
| L64 | (1140,423) | 10,609 | 142 | 20,197,376 | 67 | 74 | 0 |
| L68 | (1140,423) | 10,390 | 148 | 20,271,104 | 62 | 85 | 0 |
| L72 | (386,117) | 1,541 | 145 | 20,566,016 | 69 | 74 | 1 |

depth histogram（call/win/loss/abort）:

| level | s5 | s6 |
|---|---|---|
| L60 | 1 / 0 / 0 / 1 | 161 / 106 / 0 / 54 |
| L64 | 6 / 0 / 0 / 6 | 136 / 74 / 0 / 61 |
| L68 | 12 / 0 / 0 / 12 | 136 / 85 / 0 / 50 |
| L72 | 29 / 0 / 1 / 28 | 116 / 74 / 0 / 41 |

**確実な新観察**: threshold を上げるにつれ exact DFS が **5 石局面 (s5)**
へ到達し始めた。ただし s5 は 200k budget ではほぼ全件 abort。

**注意**: L72 が「解に近い」ことを意味しない。root 自体が未解決であり、
`pn` は距離ではない。

## Phase 2: aborted handoff root の記録と dedup

`--exact-record` を追加。exact-handoff の 1 試行ごとに 1 行を CSV に出す:

```
tag,seq,stones,key_lo,key_hi,legal,depth_from_root,is_or,retries,nodes,result
result: 0=UNKNOWN(abort) 1=WIN 2=LOSS
```

per-attempt の nodes は呼び出し前後で `exact_nodes_` を差分して得る
（以前は不可能だった）。

### 実測（v=60, L72, exact-budget=200000, publish=root, 60 s, memo=2^24）

| stones | calls | unique | repeats | maxrep | aborts | win/loss/unk |
|---|---:|---:|---:|---:|---:|---|
| s5 | 23 | **23** | **0** | 1 | 22 | 0/1/22 |
| s6 | 45 | **45** | **0** | 1 | 11 | 34/0/11 |

abort 合計 33 試行 = **33 個の異なる canonical root**。

### 結論（Phase 5 の判断材料）

**s5 の abort は少数の同一局面の繰り返しではない。** 23 calls は
23 unique、repeat 0。したがって:

- **separate persistent exact cache の優先度は低い。** 同じ局面が
  何度も再入しないので、キャッシュが効く余地がない。
- **incomplete exact search の resume の優先度も低い。** 同様に
  再入がない。

これは Phase 2 の想定（「同じ数個の s5 root が何度も abortするなら
resume 可能にする価値が高い」）に対する**明確な否定的答え**である。

## Phase 3: s5 root の exact 単独 benchmark

`--exact-replay=P` を追加。記録した各局面を df-pn から切り離して
exact solver だけで解く。時間制限は node budget のみ。

**局面の再構築について**: TState は canonical orientation で occupied
点を `add()` に通して再構築し、legal mask は同じ occupancy から
`legal_for()` で**再計算**する。親 frame から継承した legal を使わず、
canonical key を「実際に着手して到達した向き」として扱わない。
（これは本コードベースの以前のバグであり、コメントに明記した。）

### 測定方法上の重要な修正

初回の実装では 1 つの solver を全 row で再利用していた。しかし
`exact_prop` は main PnTT を先に参照し、publish=ALL では solved entry を
PnTT に書き込むため、**前の row と重なる局面が僅かな node 数で解かれて
しまう**。実例: ある root が budget 200k で 8,588 nodes だったのに、
budget 500k では 1 node で LOSS と報告された。

**対策**: row ごとに solver を新規生成する（memo は 2^22 に縮小。
2^26 の alloc 自体が benchmark を乱すため）。この修正により
n=6 で 6,942 row 全てが in-search の結果と一致（`REPLAY_AGREE`、
不一致 0）。

**この交差検証は n=6（全て既知）で行っている。11x11 の replay 数値を
信用する前に必ず通過させる。**

### 結果

別ファイル `N11-DFPN-S5-BENCH.md` に記録。

## 正しいかどうかの回帰

hybrid 回帰を再実行し不変:

- n=4 LOSS / n=5 WIN / n=6 WIN / n=7 LOSS
- exact-legal ∈ {0,4,6,8}、publish ∈ {all,root,separate} の全 arm
- forced-abort arm（`--exact-budget=1 --exact-retries=2`）で
  801,180 abort があっても最終勝敗は一致
- replay の結果交差検証: n=6 で 6,942/6,942 一致