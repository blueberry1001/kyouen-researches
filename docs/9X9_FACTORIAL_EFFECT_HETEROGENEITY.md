# 9x9 pair-component factorial effect heterogeneity (secondary / exploratory)

最終更新: 2026-09-15
branch: `factorial-exact-pc-run`
base: `661eae2ec9ae7224963a84682ae717f89e960b34`
分析種別: **secondary / exploratory only**

## 0. スコープ

- primary factorial 結果・4本 Holm 家族・holdout・score・判定規則は **一切変更しない**
- 本文書および付随 artifact は **新しい確認的 p 値を作らない**
- 事後的な統計的有意性の主張は行わない
- 新しい heuristic の採用・最適化は行わない

参照 primary:

- `docs/9X9_FACTORIAL_EXACT_PC_RUN_RESULT.md`
- `results/9x9/factorial/primary-summary.csv`

## 1. O overall `+21 → -3` の完全分解

対象:

- `artifacts/9x9-factorial-holdout.csv`
- `artifacts/solve/merged/O_at_E0.csv` (n=715)
- `artifacts/solve/merged/O_at_E1.csv` (n=639)

事前監査どおりの strata:

| stratum | n |
|---|---:|
| O0 ∩ O1 (overlap) | 419 |
| O0-only | 296 |
| O1-only | 220 |

LOSS=1 / WIN=0 として、overlap では

```text
y00 = top_T
y01 = top_TO
y10 = top_TE
y11 = top_raw
O_effect_E0 = y01 - y00
O_effect_E1 = y11 - y10
interaction = O_effect_E1 - O_effect_E0
```

### overlap 419

| quantity | value |
|---|---:|
| O effect at E=0 net | **-6** |
| O effect at E=0 ΔLOSS | -0.014320 |
| O effect at E=0 better/same/worse | 91 / 231 / 97 |
| O effect at E=1 net | **-7** |
| O effect at E=1 ΔLOSS | -0.016706 |
| O effect at E=1 better/same/worse | 91 / 230 / 98 |
| interaction mean | **-0.002387** |
| interaction median | **0** |
| interaction positive / zero / negative | 1 / 416 / 2 |

interaction histogram (`-2,-1,0,+1,+2`):

```text
-2: 0
-1: 2
 0: 416
+1: 1
+2: 0
```

### only strata

| stratum | n | net | ΔLOSS | change rate |
|---|---:|---:|---:|---:|
| O0-only | 296 | **+27** | +0.091216 | 0.435811 |
| O1-only | 220 | **+4** | +0.018182 | 0.436364 |

### 恒等式

```text
overall_O1_net - overall_O0_net
= sum(overlap interaction) + O1_only_net - O0_only_net
= (-1) + (+4) - (+27)
= -24
```

既知 overall は `O0 = 169-148 = +21`, `O1 = 141-144 = -3`, difference `-24`。
**恒等式は一致した。**

解釈候補（確認ではない）:

- overlap 419 では O 効果は E=0 / E=1 ともにわずかに負（baseline 側がわずかに優勢）
- overall の `+21` は主に **O0-only 296 の +27** が作っている
- overall の `-3` は overlap の -7 と O1-only の +4 の相殺
- したがって `+21 → -3` の符号反転の主因は、shared-parent 上の E×O interaction ではなく **membership による母集団構成差**

出力: `results/9x9/factorial/effect-heterogeneity/o-overlap-decomposition.csv`

## 2. E overall `+43 / +26` の overlap / only 分解

対象:

- `artifacts/solve/merged/E_at_O0.csv` (n=1024)
- `artifacts/solve/merged/E_at_O1.csv` (n=1024)

事前固定交差は 254。

| stratum | n | net | ΔLOSS | change rate |
|---|---:|---:|---:|---:|
| E0 ∩ E1 overlap | 254 | E@O0 **-3** / E@O1 **-6** | -0.011811 / -0.023622 | 0.429134 / 0.425197 |
| E0-only | 770 | **+46** | +0.059740 | 0.459740 |
| E1-only | 770 | **+32** | +0.041558 | 0.446753 |

事前計算済み secondary interaction の期待値:

- overlap E0 net = -3
- overlap E1 net = -6
- E0-only net = +46
- E1-only net = +32

**4 とも一致した。**

記述:

- E の全体的な正の効果 (`+43` / `+26`) は、E0/E1 共通の 254 親ではなく、**各 sample の non-overlap 部分**から生じている
- overlap 254 では E 効果はむしろわずかに負

出力: `results/9x9/factorial/effect-heterogeneity/e-overlap-decomposition.csv`

## 3. structural feature 比較（outcome-free）

`artifacts/9x9-factorial-population.csv` と holdout の事前計算済み列、および
`artifacts/9x9-pair-gap-population.csv` の score/gap 列のみを使う。

| stratum | n | mean distinct | T=TO | TE=raw | T=TE | TO=raw | mean pair_E | mean pair_O |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| O_overlap | 419 | 2.021 | 0.000 | 0.000 | 0.983 | 0.995 | 0.535 | 2.119 |
| O0_only | 296 | 2.054 | 0.000 | **1.000** | 0.111 | 0.834 | 3.350 | 2.084 |
| O1_only | 220 | 2.050 | **1.000** | 0.000 | 0.800 | 0.150 | 3.176 | 2.096 |
| E_overlap | 254 | 2.016 | 0.996 | 0.988 | 0.000 | 0.000 | 3.740 | 0.571 |
| E0_only | 770 | 2.009 | 0.914 | 0.984 | 0.000 | 0.092 | 3.700 | 0.602 |
| E1_only | 770 | 2.008 | 0.990 | 0.936 | 0.066 | 0.000 | 3.692 | 0.607 |

主な構造差:

- **O0-only** は定義上 `top_TE == top_raw`（O が E=1 では top を動かさない）が 100%
- **O1-only** は定義上 `top_T == top_TO`（O が E=0 では top を動かさない）が 100%
- O0-only は `pair_E` が大きく（mean 3.35）、O_overlap（0.54）と明確に異なる
- これは「O 効果の符号反転」を **score 構造の membership 差**として記述する候補になる
- 本文書の段階で閾値や新ルールは最適化しない

出力: `results/9x9/factorial/effect-heterogeneity/structural-strata.csv`

## 4. full O census（事前固定有限母集団 801 / 702）

### 4.1 不足 solve

`results/9x9/factorial/o-full-census-reconstruction-audit.json` の missing states
（O_at_E0: 86 親, O_at_E1: 63 親）から `(canonical_parent, move)` を union した。

- unique child roots: **201**
- outcome を見て選択していない
- 86/63 の固定不足集合を変更していない
- solver 意味・探索順は変更していない
- 既存 pair 形式 solver ではなく、同一 `Solver9` を載せ替えた
  **single-root wrapper** `cpp/solvers/kyouen_solver_9_root.cpp` を使用
- smoke: 既知 parent `"0,1,31,41" move=13` → `LOSS`（merged と一致）
- failed shards: 0, memo-over: 0, retry: 0

入力: `artifacts/solve/o-missing-unique-children.csv`
出力: `artifacts/solve/o-missing-unique-children.out.csv`

### 4.2 full census descriptive

| comparison | n | both_loss | both_win | baseline_only | added_only | ΔLOSS | change rate | net |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| O_at_E0 full | **801** | 250 | 190 | 171 | 190 | **+0.023720** | 0.450687 | +19 |
| O_at_E0 holdout unobserved | 715 | 231 | 167 | 148 | 169 | +0.029371 | 0.443357 | +21 |
| O_at_E1 full | **702** | 218 | 170 | 154 | 160 | **+0.008547** | 0.447293 | +6 |
| O_at_E1 holdout unobserved | 639 | 204 | 150 | 144 | 141 | -0.004695 | 0.446009 | -3 |

比較:

- O_at_E0: full は holdout より **わずかに弱い正**（差 -0.005650）
- O_at_E1: holdout のわずかな負 Δ は full では **わずかな正** に符号が変わる
  （差 +0.013242）
- どちらも絶対値は小さい。除外済み親を戻しても O 効果の大きさは大きくは動かない
- O_at_E1 では「既観測親を除外した記述」と full finite population で記述の符号が
  一致しない点は、次回 independent holdout の設計時に注意する

出力:

- `results/9x9/factorial/effect-heterogeneity/o-full-census-summary.csv`
- `results/9x9/factorial/effect-heterogeneity/o-full-census-summary.json`
- `results/9x9/factorial/effect-heterogeneity/o-full-census-parents.csv`

## 5. 4-outcome 完全親の interaction

full O census 後、`T / TE / TO / raw` の 4 outcome が揃う親:

- **n = 470**

```text
I = y11 - y01 - y10 + y00
```

| quantity | value |
|---|---:|
| I=-2 | 0 |
| I=-1 | 2 |
| I=0 | 466 |
| I=+1 | 2 |
| I=+2 | 0 |
| mean I | **0** |
| median I | **0** |
| I<0 / I=0 / I>0 | 2 / 466 / 2 |
| abs(I)=2 | **0** |

出力: `results/9x9/factorial/effect-heterogeneity/o-full-4outcome.csv`

## 6. 代表反例（mechanism 探索用）

定義:

- A: O が E=0 で改善し E=1 で悪化 (`O_effect_E0 < 0` and `O_effect_E1 > 0`)
- B: O が E=0 で悪化し E=1 で改善
- C / D: E について同様の方向反転

### 強い方向反転（|I|=2）

| class | n |
|---|---:|
| A | **0** |
| B | **0** |
| C | **0** |
| D | **0** |

full 470 と E 交差 254 の双方で、符号反転に必要な |I|=2 は観測されなかった。

### 近接反転（|I|=1, O）

| canonical_parent | y00 | y01 | y10 | y11 | O@E0 | O@E1 | I | cause_class |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1,20,25,40 | 0 | 0 | 1 | 0 | 0 | -1 | -1 | O-only |
| 2,46,56,68 | 0 | 1 | 1 | 1 | +1 | 0 | -1 | O-only |
| 21,38,40,41 | 1 | 1 | 0 | 1 | 0 | +1 | +1 | both |
| 3,47,48,52 | 0 | 0 | 0 | 1 | 0 | +1 | +1 | synergy |

スコア/ gap メタデータ付き一覧:

- `results/9x9/factorial/effect-heterogeneity/examples-full-O_near_nonzero_interaction.csv`
- `results/9x9/factorial/effect-heterogeneity/examples-full-E_near_nonzero_interaction.csv`
- 全方向反転テーブル: `o-full-direction-flips.csv`

解釈候補（確認ではない）:

- shared-parent 上の O×E interaction はほぼ存在しない
- overall 符号反転は **strata membership** で説明される方が自然
- 次の independent holdout 仮説は「interaction」ではなく
  「O0-only / O1-only を分ける outcome-free 構造」を固定すべき

## 7. 次の独立検証候補（未採用）

本文書では **仮説を固定しない**。候補のみ:

1. `pair_E` の大きさ（O0-only が overlap より大きい）を freeze した上で、
   新規 independent holdout で O 効果の strata 差を再検証する
2. `top_TE == top_raw` / `top_T == top_TO` の membership を outcome 無しで固定し、
   O 効果の記述差を検証する
3. full census で O_at_E1 の Δ 符号が holdout 記述と食い違った点を、
   「除外済み親が系統的に異なる」仮説として独立確認する

いずれも **この cohort 上での閾値最適化はしない**。

## 8. artifact / SHA256

主要出力:

- `results/9x9/factorial/effect-heterogeneity/effect-heterogeneity-summary.json`
- `results/9x9/factorial/effect-heterogeneity/o-overlap-decomposition.csv`
- `results/9x9/factorial/effect-heterogeneity/e-overlap-decomposition.csv`
- `results/9x9/factorial/effect-heterogeneity/structural-strata.csv`
- `results/9x9/factorial/effect-heterogeneity/o-full-census-summary.json`
- `results/9x9/factorial/effect-heterogeneity/o-full-census-summary.csv`
- `results/9x9/factorial/effect-heterogeneity/o-full-4outcome.csv`
- `results/9x9/factorial/effect-heterogeneity/o-full-direction-flips.csv`
- `artifacts/solve/o-missing-unique-children.csv`
- `artifacts/solve/o-missing-unique-children.out.csv`
- `artifacts/solve/o-missing-join-plan.json`

スクリプト:

- `scripts/analyze-9x9-factorial-effect-heterogeneity.py`
- `scripts/prepare-9x9-factorial-o-missing-children.py`
- `scripts/analyze-9x9-factorial-o-full-census.py`
- `cpp/solvers/kyouen_solver_9_root.cpp`

SHA256 は commit 時に `results/9x9/factorial/effect-heterogeneity/SHA256SUMS.txt` へ記録する。

## 9. 変更しないもの

- primary Holm family / p 値 / reject 判定
- holdout CSV とその manifest
- 既存 merged solver outputs（`O_at_E0/O_at_E1/E_at_O0/E_at_O1` の primary 用行）
- main branch
- shared worktree registry
