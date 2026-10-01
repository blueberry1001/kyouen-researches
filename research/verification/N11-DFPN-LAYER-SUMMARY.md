# 11x11 df-pn + exact hybrid: 層の全体像と現在の bottleneck

**11x11 の勝敗は UNKNOWN のまま。**

- base commit: `6e16edd`
- 機械: WSL / g++ -march=native、16 cores / 19 GB RAM、swap 使用 0
- 完全証明: **0 件**。中央 1 石局面も、二石 root 20 個も未解決。

このファイルは既存の個別報告を 1 枚にまとめた現況であり、
新しい測定ではない。

## 層の全体像

`--exact-legal-by-stones` で 1 層ずつ gate して測った結果:

| 層 | root 数 | 全部閉じる budget | 最悪 nodes | WIN / LOSS | 偏り |
|---|---:|---:|---:|---|---|
| s5 | 23 | 10,000,000 | 5,677,449 | 12 / 11 | 均衡 |
| s6 | 45 | 1,000,000 | 665,057 | 43 / 0 | WIN のみ |
| s7 | 301 | 1,000,000 | 222,479 | 47 / 254 | LOSS 84% |
| s8 | 2,003 | 200,000 | 67,804 | 1,924 / 79 | WIN 96% |
| s9 以上 | 0 | — | — | — | 到達せず |

**difficulty は s5 を境に単調に下がり、s8 が最も軽い。**
s5 の最悪値は s8 の 83 倍である。

偏りは parity と整合して層ごとに反転する
（s6 OR = WIN 側、s7 AND = LOSS 側、s8 OR = WIN 側）。
これは層固有の性質であって、全体の勝敗を示していない。

## 層の分離が成立する条件

合法手数の上限が `121 - k` なので、単一の `--exact-legal` では層を
選別できない（s7 に必要な 114 以上では s5/s6 も同時に条件を満たす）。
`--exact-legal-by-stones` で初めて分離できる。
実測: control (`--exact-legal=80`) は s5 61 + s6 17 で s7 は 0、
gated は s7 301 のみ。

## budget 配分の効果

| 設定 | root_pn 最小 | exact abort | df-pn expansions |
|---|---:|---:|---:|
| global 200k / L72 | 361 | 53 | 1,301 |
| adaptive s5:5M | 30 | 2 | 856 |
| 層別 gate（s5〜s8） | 1 | **0** | **1,930** |

層別 gate で **abort が完全に消えた**。

## 現在の bottleneck: 集約（末端ではない）

層別 sweep で 20 返信すべて TIMEOUT のまま。
末端の exact 解は十分に得られている（s5〜s8 が budget 内で閉じる）が、
二石 root が閉じない。

二石 root が閉じるには、その子 1 つについて
「その子のすべての concrete response が証明される」必要がある。
末端が解けても、それを束ねる root の集約が完了しないと閉じない。

**したがって次の測定対象は末端ではなく伝播である。**
solved entry の publish 範囲（root-only）が伝播を遅らせている
可能性がある。

## `root_pn=1` を読むときの注意

層別 sweep で 11 個の返信が `root_pn=1` を示した。
これは**最良ではなく cautionary な値**である。

二石 root は OR ノードで `pn = min(子の pn)`。
`pn=1` かつ `root_dn=118` は「未展開の子が 1 つ以上ある」ことであり、
未展開の子は pn=1 を持ち親の min を 1 に引き下げる。
つまり「その子の探索がまだ始まっていない」であり、
「1 手で証明に到達した」ではない。

確認した事実: publish された solved root は 0 件、
log に `[done] ... WIN/LOSS` の行は 0 件。

## 次にやるべきこと（優先順）

1. **集約の効率を測る**。leaf は解けているのに root が閉じない。
   root-only publish が伝播を遅らせているかを確認する。
2. **二石 root 直下の 3 石局面を個別に exact で解く**。
   3 石がどちらに偏るかが分かれば 20 返信の行方が変わる。
3. **s5 専用予算を 20M まで上げる**。s5 だけが重いので、
   他の層_gate が解決したうえで s5 に集中する。

## 参照

- `N11-DFPN-EXACT-FRONTIER.md` — Phase 1〜2（s5 unique/repeat）
- `N11-DFPN-S5-BENCH.md` — s5 の budget 別 benchmark
- `N11-DFPN-L72-ADAPTIVE.md` — L72 adaptive の効果
- `N11-DFPN-EXACT-ORDER-AB.md` — ordering A/B（baseline 勝ち）
- `N11-DFPN-FRONTIER-LAYERS.md` — 合法手数上限による構造的限界
- `N11-DFPN-S7-LAYER.md`、`N11-DFPN-S8-LAYER.md` — 上層
- `N11-DFPN-CENTER20-LAYERED.md` — 層別 sweep