# 10x10 three-stone holdout v2: source-label semantics audit

固定日: 2026-09-10

## 発見

holdout v2 は `three-stone-probe-holdout-v2.csv` の各 `parent` について、選抜元 `two-stone-90-*-child-proof.csv` の同じ `source_index` 行にある `loss_child` を、最終的な4-stone LOSS childラベルとして結合する前提で設計されていた。

しかし実データを照合すると、この前提は少なくとも一例で成立しない。

```text
holdout source:       two-stone-90-61-child-proof.csv
source_index:         42
holdout parent:       0,6,31
source row state:     0,6,31
source row loss_child:0,13,60,68
```

`0,13,60,68` は `0,6,31` を包含しないため、`0,6,31` に1手を加えた child ではない。

したがって、source proof の `loss_child` を holdout parent の合法4-stone child順位へ直接 join することは、現在の証拠だけでは意味的に正当化できない。

## 影響

この問題は probe の盲検性とは別で、**評価ラベルの意味そのもの**に関する。

固定済み1161-child universe、fresh-process probe、raw seal、ranking SHAは技術的には実行できる。しかし、順位固定後に `loss_child` を join して first LOSS rank を計算する予定だった最終評価は、この意味不一致を解消するまで成立しない。

特に `THREE_STONE_PROBE_HOLDOUT_V2_PRE_RUN_RECEIPT.md` と `THREE_STONE_PROBE_HOLDOUT_V2_EVAL_AUDIT.md` にある「source proof の exact LOSS child」という呼び方は、source CSV の生成意味を再確認するまで未証明として扱う。

## 安全な扱い

1. 新holdout probeは、ラベル意味を解明するまで開始しない。
2. source `loss_child` を4-stone childラベルとして読む評価器は作らない。
3. `two-stone-90-61-child-proof.csv` / `two-stone-90-66-child-proof.csv` の生成経路を追い、`state`, `source`, `loss_child` が何を表すか確認する。
4. 必要なら、holdout parentごとに本当にそのparentを包含する exact LOSS child を既存proof/witnessから再構成し、**probe結果を見ずに**新しいラベル表とそのSHAを固定する。

## pre-run status

```text
holdout selection:       FROZEN
holdout child universe:  FROZEN
holdout probe:           NOT RUN
ranking:                 NOT CREATED
label join:              BLOCKED (source loss_child semantics mismatch)
```

この監査は新holdout probe開始前に行ったため、結果を見た後の評価変更ではない。
