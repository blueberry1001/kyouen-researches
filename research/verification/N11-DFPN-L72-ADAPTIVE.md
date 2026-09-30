# L72 adaptive budget の再測定

**11x11 の勝敗は UNKNOWN のまま。**
v=60 中央 1 石局面は **TIMEOUT（未証明）**。20 返信のどれも閉じない。
本ファイルは**途中経過**であり、勝敗の断定ではない。

- 機械: WSL / g++ -O3 -march=native、16 cores / 19 GB RAM
- memo: 2^24（各 run 同一）
- budget: 60 s / run、v=60、exact-legal=72、exact-retries=1、publish=root
- 3 本は**逐次**実行（並列化せず。各 run が 2^24 の memo を確保し、
  19 GB 環境では無闇な並列を避ける）
- script: `research/verification/scripts/dfpn_l72_adaptive_probe.sh`

## 結果

| arm | root_pn | root_dn | dfpn exp | exact calls | exact nodes | exact abort | exact WIN | exact LOSS | s5 (call/win/loss/abort) | s6 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| base: global 200k | 361 | 116 | 1,301 | 114 | 16,003,072 | 53 | 59 | 1 | 24 / 0 / 1 / **23** | 90 / 59 / 0 / 30 |
| **adaptive** s5:5M, s6:200k | 309 | 112 | 856 | 5 | 14,610,432 | 2 | 1 | 1 | **5 / 1 / 1 / 2** | （出現せず） |
| global 5M（対照） | 309 | 112 | 856 | 5 | 14,106,624 | 2 | 1 | 1 | 5 / 1 / 1 / 2 | （出現せず） |

main TT eviction は 3 本すべて 0。root-only publish の性質が保たれている。

## 観察

1. **s5 abort 率が 23/24 から 2/5 へ大幅に低下した。**
   これが Phase 7 の主要指標であり、明確に改善している。
2. **adaptive と global 5M がほぼ同一**（root も dfpn exp も同じ、
   s5 histogram も同じ）。これは **adaptive 分割そのものが効くのではなく、
   s5 に十分な予算を渡すことが本質**であることを意味する。
   s5 に 5M を渡してやれば Adversary Frontier が 24 → 5 に縮小し、
   そこに s6 の handoff も抓到らなくなるため、s6 の予算切割は
   観測Effect がほとんど出ない。
3. **dfpn expansions が 1,301 → 856 に減った**。s5 が解けるように
   なると df-pn 自身がuhiThose 分emateelesnatる fewer nodes を使う。
4. **exact nodes も 16.0M → 14.6M に減った**。予算を増やしたのに
   総消費が減んでいる = abort になる s5 を捨てるより
   s6 を回したほうが安いという構造。
5. **`root_pn` 361 → 309**。ただしこれは「証明が近い」という意味では
   ない。pn は精密化で増減する値であり、root は依然未解決。

## s5 予算が実際に効いたことの確認

`--exact-record` を使い、per-attempt の node 消費を確認した:

```
s5 calls=3  nodes_total=9,002,595  nodes>200k=3  win=1 loss=1 unknown=1
個別: 1,858,933 / 2,143,662 / 5,000,000(abort)
```

3 試行すべて 200k を超えて消費しており（うち 1 件は予算上限の
5,000,000 で abort）、2 件が実際に解けている。**予算指定は
確実に反映されている。**

## 解釈の注意

**adaptive の利点は「分割設計の正当性の確認」であり、
「s5 budget を 5M に上げた効果」と分けて評価すべき。**
observed  では global 5M と同等であり、adaptive による
「s6 に無駄な予算を与えない」効果は这次の測定では観測されない。

このため、実用上は **「s5 に十分大きな予算を渡す」ことが
本質的な変更**であり、per-stone 分割はその構造を
明文化して将来の調整を容易にするもの、的位置づけ。

## 次の手への示唆

1. **s5 予算をさらに大きく**（10M）しての s5 abort 率がどれだけ
   下がるか測る。bench（N11-DFPN-S5-BENCH.md）で 10M なら
   全 23 件が閉じたので、10M なら s5 abort はほぼ消えるはず。
2. **root-only publish を維持的前提下**で、この設定の状態で
   central 20 replies の再sweep（Phase 8）へ進む。
3. global 5M と adaptive が同等である以上、実装を簡素化して
   「global budget を上げる」だけでも同じ効果が得られる。

## 記録

- 3 本すべて **TIMEOUT（未証明）**。WIN 0 / LOSS 0。
- root 未解決。11x11 は UNKNOWN のまま。