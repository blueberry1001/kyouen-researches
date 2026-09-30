# 朝の報告（2026-09-30 夜勤）

## 11×11: **UNKNOWN**

**Main HEAD**: `e8781ca`（`Add replay determinism check: node counts are reproducible`）
すべて main へ push 済み。他のエージェントの成果は上書きしていない。

**完全証明は 1 件も無い。** 以下の全ての測定は途中経過であり、
未完探索・TIMEOUT・proof number・ヒューリスティックから勝敗を
断定していない。

---

## 1. 変更したコード

すべて `cpp/solvers/kyouen_dfpn_root.cpp`（単一ファイル実装）。

| 追加 | 目的 |
|---|---|
| `--exact-record` | exact-handoff 1 試行ごとに 1 行を CSV 出力 |
| `--exact-record-limit=N` | 記録数の上限 |
| `--exact-replay=P` | 記録した局面を exact 単体で単独 replay |
| `--exact-replay-budget=N` | replay の node budget |
| `--exact-budget-by-stones=5:N,6:N` | stone count 別 exact budget |

`exact_record_add()` は呼び出し前後で `exact_nodes_` を差分して
per-attempt の node 消費を得る（以前は不可能だった）。

---

## 2. correctness regression

**全 arm 通過。変化なし。**

- hybrid 回帰: n=4 LOSS / n=5 WIN / n=6 WIN / n=7 LOSS
  - exact-legal ∈ {0,4,6,8}、publish ∈ {all,root,separate}
  - forced-abort arm（`--exact-budget=1 --exact-retries=2`）で
    **801,180 abort** があっても最終勝敗一致
- adaptive 回帰（新規 `dfpn_regress_adaptive.sh`）:
  baseline / s5:5M+s6:200k / 全 stone count budget=1 の 3 条件
  すべて LOSS/WIN/WIN/LOSS、publish=root でも同一、
  不正な指定は rc=2 で拒否
- replay 交差検証: n=6 で **6,942 / 6,942 一致**（`REPLAY_AGREE`）
- replay 決定性: 2 回実行で result と node count が一致、
  **行を逆にしても 23 keys すべて同一**（`ORDER_INDEPENDENT`）

---

## 3. s5/s6 handoff の unique / repeat 統計

`--exact-record`、v=60 / L72 / exact-budget=200k / publish=root / 60 s:

| stones | calls | **unique** | **repeats** | aborts | win/loss/unk |
|---|---:|---:|---:|---:|---|
| s5 | 23 | **23** | **0** | 22 | 0/1/22 |
| s6 | 45 | **45** | **0** | 11 | 34/0/11 |

abort 合計 33 試行 = **33 個の異なる canonical root**。

### 結論（Phase 5 の判断材料）

**s5 の abort は少数の同一局面の繰り返しではない。**
したがって **persistent exact cache も exact resume も優先度が低い**。
Phase 2 の想定（「同じ数個の s5 root が何度も abort するなら
resume する価値が高い」）に対する明確な否定的答えである。

---

## 4. s5 exact 単独 benchmark

`N11-DFPN-S5-BENCH.md`。23 unique s5 root、各局面 cold、memo 2^22。

| budget | WIN | LOSS | UNKNOWN |
|---:|---:|---:|---:|
| 200,000 | 0 | 2 | 21 |
| 500,000 | 0 | 2 | 21 |
| 1,000,000 | 1 | 3 | 19 |
| 2,000,000 | 2 | 7 | 14 |
| 5,000,000 | 11 | 10 | 2 |
| 10,000,000 | **12** | **11** | **0** |

**10M なら s5 全 23 件が閉じる。** node 数は最小 130,540、
最大 5,677,449。WIN と LOSS はほぼ半々。

s6 も同じ方法で測定（`N11-DFPN-CENTER20-ADAPTIVE.md` 参照）:
200k で 36/45、1M で 43/45 が WIN、**LOSS は 0**。
s6 は s5 より桁違いに安い（最小 2,143 nodes）。

### 測定方法上のバグを 1 件発見・修正

初回の replay は全 row で solver を 1 つ再利用していた。
`exact_prop` は main PnTT を先に参照し publish=ALL はそこに
solved を書き込むため、**前の row と重なる局面が僅かな node で
解かれてしまう**。実例: ある root が budget 200k で 8,588 nodes
だったのに、budget 500k では **1 node** で LOSS と報告された。

修正: row ごとに solver を新規生成（memo は 2^22 に縮小。
2^26 の alloc 自体が benchmark を乱すため）。
修正後 node 数が予算に対して単調かつ安定になったことが、
修正が成功したことの証拠になっている。

---

## 5. adaptive budget の有無と効果

`N11-DFPN-L72-ADAPTIVE.md`。v=60、60 s、memo 2^24、逐次実行。

| arm | root_pn | root_dn | dfpn exp | exact calls | exact nodes | s5 (c/w/l/a) |
|---|---:|---:|---:|---:|---:|---|
| global 200k | 361 | 116 | 1,301 | 114 | 16.0M | 24 / 0 / 1 / **23** |
| adaptive s5:5M s6:200k | 309 | 112 | 856 | 5 | 14.6M | **5 / 1 / 1 / 2** |
| global 5M（対照） | 309 | 112 | 856 | 5 | 14.1M | 5 / 1 / 1 / 2 |

**s5 abort 率が 23/24 → 2/5 に低下。** Phase 7 の主要指標が動いた。

予算が効いたことは推論ではなく `--exact-record` で確認した
（3 試行すべて 200k 超消費、うち 2 件が解けた、1 件は 5,000,000 で abort）。

**正直な解釈**: adaptive と global 5M はほぼ同一。
**利得は「s5 に十分な予算を渡すこと」由来**であり、
per-stone 分割そのものが global 上昇に勝ったわけではない。
分割は構造を明文化して将来の調整を容易にするものとして残す。

---

## 6. cache policy 比較

**今回は実施していない。** Phase 2 の結果（s5 abort は 23 unique /
0 repeat）により、**persistent cache に効く余地がない**ことが
分かったため。repeat が無ければ同じ局面は再入せず、
キャッシュが効く場面が存在しない。

L44 での「差がない」という過去の観測は、今回の s5 固有の構造
（重複ゼロ）の方が強い理由になっている。

---

## 7. L72 再測定（確認 run）

`dfpn_l72_confirm.sh`、5 分、memo 2^26、`--children`、swap 使用 0。

- root: **TIMEOUT**、root_pn=1133、root_dn=269
- exact: calls=94、nodes=69,341,184、abort=22、WIN=57、LOSS=14
- histogram: `s5=21/4/14/2 s6=73/53/0/20`
- **root 直下 20 子はすべて `st=1`（OPEN）、solved 0/20**
- main TT eviction 0 / 0

5 分回しても二石 child は 1 つも閉じない。

---

## 8. central 20 replies の変化

`N11-DFPN-CENTER20-ADAPTIVE.md`。60 s/root、memo 2^26 shared TT、L72、
s5:5M + s6:200k、20 分。

- **WIN 0 / LOSS 0 / TIMEOUT 20、MISSING 0**
- 二石 root の `root_pn` が **30〜161**（r=36 が 30）。
  前回（L44/L56）は数百〜数千程度。
- exact nodes 合計 **35.9 億**
- histogram: `s5=49/5/19/15 s6=1409/854/0/545`

**s5 で 5 WIN / 19 LOSS が出てきたが**、これらは二石 root
**の下位層**の結果であって二石 root 自身ではない。

**20 返信のどれ一つ閉じていない。** 中央勝ちには 20 全部 WIN が
必要、1 つでも LOSS があれば反証。現状はどちらでもない。

---

## 9. solved / unsolved

- 中央 1 石局面 `{60}`: **未解決**
- 中央後の二石 root 20 個: **0 / 20 が solved**
- 完全証明: **0 件**

---

## 10. 現在の bottleneck

**「証明上に現れる s5 局面はすべて 10M nodes 以内で解けるのに、
二石 root が解けない」という構造が現在の bottleneck。**

つまり:

- s6: 200k でほぼ閉じる（LOSS 0）
- s5: 10M で全件閉じる（WIN/LOSS 半々）
- s7 以上: 未測定

exact が個々を解けるのに root が閉じないのは、
**子和がまだ両方とも解けていない**ためであり、
個別の証明可能性がそのまま上位の証明に伝播していない。

s5 で LOSS が出ている（19 件）ので、次は **s5 より上の層
（s6 の sibling、s7 以降）の difficulty** を測る段階に入る。

---

## 11. 次にやるべき 1〜3 項目

1. **s7 / s8 の replay benchmark**（200k → 10M）。
   s5 が 10M で閉じるなら s7 はどれくらいの budget で閉じるか。
   ここで「 Budget 10M でも解けない層」が出るか否かで
   以後の戦略（threshold 拡大か、証明分解か）が決まる。

2. **root 直下 20 子の個別 replay**。
   `--exact-record` で二石 root を 60 s ずつ走らせ、
   その直下 s3/s4 局面を記録し、それぞれを exact 単体で
   能不能閉じて 1M/10M で測る。s5 より浅ければ
   budget が桁違いに小さくて済む可能性がある。

3. **exact DFS の move ordering A/B**（Phase 6）。
   23 s5 root という**固定 benchmark 集合**が s5 bench で用意できた。
   `total nodes to solve` を評価指標にして、A/B が明確にできる。
   1 度に 1 つの ordering だけ変更する。

---

## 補足: Phase 12 の優先順位変更

以下が実測で判明したため、当初の「L76,L80,... と threshold を
上げる」を**最後**に回した。

- s5 が 10M で全部解けることが分かったので、
  L72 で s5 budget を上げただけで s5 abort が 23/24 → 2/5 に低下した。
  **threshold を上げる前に budget を上げたほうが効く**。
- s5 の abort は全部 unique で repeat ゼロなので、
  **persistent cache / resume は低優先**。
- s6 に LOSS が 1 件もない点は注目に値する。
  s6 が「片側に偏った層」である可能性があり、
  これを補うために二石 root が解けない構造があるのかもしれない。