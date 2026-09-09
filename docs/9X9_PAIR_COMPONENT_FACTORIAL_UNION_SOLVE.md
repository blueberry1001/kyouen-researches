# 9×9 factorial union child solve workflow

最終更新: 2026-09-09

## 目的

`9X9_PAIR_COMPONENT_FACTORIAL_HOLDOUT_DESIGN.md` は、同一parentが複数比較に属する場合に exact child solve を共有してよいと事前固定している。

従来の `prepare-9x9-factorial-solver-inputs.py` は4比較を別CSVへ出すため、そのまま別processで実行すると同じ `(canonical_parent, move)` を複数回 exact solve し得る。

この補助workflowは統計集合・比較方向・Holm補正を変更せず、solver workだけを共有する。

## 実装

1. union入力を作る。

```bash
python3 scripts/prepare-9x9-factorial-union-input.py \
  /tmp/9x9-factorial-holdout.csv \
  /tmp/factorial-union.csv
```

各selected parentについて、4 score top moveのうち、そのparentが実際に属する比較で必要なmoveだけを重複排除する。

既存 `kyouen-solver-9-compare` は1行につき2 rootを解くため、必要moveを2個ずつpairにする。3個の場合だけ、最後の新規moveを既に解いた最初のmoveと組ませる。この再訪は同processのroot memo hitになることを意図する。

2. memo table飽和を避けるためparent単位でshardする。

```bash
python3 scripts/split-9x9-factorial-union-input.py \
  /tmp/factorial-union.csv \
  /tmp/factorial-union-shards \
  --parents-per-shard 64
```

同一parentの全rowは必ず同じshardへ入る。shardごとにfresh process / fresh memoで `kyouen-solver-9-compare` を実行する。

`64` は統計的な選択ではなく、memo capacityに対する保守的な運用値である。既存 `results/9x9/pair-vs-true-unique-first12.csv` では12 parents / 24 roots後に `memo_used=4,198,534` まで増えており、数千rootを単一processへ入れる設計は28-bit tableの80% guardに接近し得る。

shardが `memo table over 80%` で失敗した場合は、outcomeを選別せず、そのshard全体をより小さい固定parent数へ再分割してfresh rerunする。

3. 全shard出力から4比較のsolver結果を再構成する。

```bash
python3 scripts/reconstruct-9x9-factorial-results-from-union.py \
  /tmp/9x9-factorial-holdout.csv \
  /tmp/factorial-union-results/union-*.csv \
  /tmp/factorial-comparison-results
```

再構成scriptは以下を拒否する。

- holdoutにないparent
- 事前指定比較で不要な `(parent, move)`
- 必要childの欠落
- repeated `(parent, move)` のoutcome不一致
- WIN/LOSS以外のoutcome

出力は既存 `analyze-9x9-factorial-outcomes.py` が読む

```text
canonical_parent,pair_top,added_top,pair_child_outcome,added_child_outcome
```

形式へ戻す。

## 不変条件

union solveは計算共有だけを行う。以下は変更しない。

- 4つのcomparison membership
- absent / added move
- outcome definition
- discordant parentだけを使うexact binomial test
- Holm family-wise correction
- E comparisonの固定hash sample
- O comparisonのcensus

したがってunion/shardingは確認的推論の標本選択には影響しない。
