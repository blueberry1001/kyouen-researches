# 9×9 factorial union child solve workflow

最終更新: 2026-09-09

## 目的

`9X9_PAIR_COMPONENT_FACTORIAL_HOLDOUT_DESIGN.md` は、同一parentが複数比較に属する場合に exact child solve を共有してよいと事前固定している。

従来の `prepare-9x9-factorial-solver-inputs.py` は4比較を別CSVへ出すため、そのまま別processで実行すると同じ `(canonical_parent, move)` を複数回 exact solve し得る。

この補助workflowは統計集合・比較方向・Holm補正を変更せず、solver workだけを共有する。

## 実装

### 1. union入力

```bash
python3 scripts/prepare-9x9-factorial-union-input.py \
  /tmp/9x9-factorial-holdout.csv \
  /tmp/factorial-union.csv
```

各selected parentについて、4 score top moveのうち、そのparentが実際に属する比較で必要なmoveだけを重複排除する。

既存 `kyouen-solver-9-compare` は1行につき2 rootを解くため、必要moveを2個ずつpairにする。3個の場合だけ、最後の新規moveを既に解いた最初のmoveと組ませる。この再訪は同processのroot memo hitになることを意図する。

凍結済みworksetでは

```text
comparison memberships   3402
naive root calls         6804
unique required children 5208
union solver root calls  5232
saved root calls         1572 (23.10%)
```

である。理論上削減可能な1596 rootのうち1572 rootを削減し、残る24 rootは3 unique move parentの意図的再訪である。

### 2. primary shard

memo table飽和を避けるためparent単位でshardする。

```bash
python3 scripts/split-9x9-factorial-union-input.py \
  /tmp/factorial-union.csv \
  /tmp/factorial-union-shards \
  --parents-per-shard 64
```

同一parentの全rowは必ず同じshardへ入る。shardごとにfresh process / fresh memoで `kyouen-solver-9-compare` を実行する。

`64` は統計的な選択ではなく、memo capacityに対する保守的な運用値である。凍結worksetは2592 parents、41 primary shardsで、最大primary shardは134 root callsである。

### 3. frozen byte stream と solver入力transport

凍結SHA256は次の4ファイルに対して検査する。

```text
07e60d22eac16834726a5972967e2ae426f2a75f89401f9d4508d1ce033fc840  9x9-confirmatory-1024.csv
5e11b3bd514919c87e2702f60a8e21df026b45ea60fc9044cfa8335da62517fa  9x9-factorial-holdout.csv
9cc23b43fed601db0dae6f4e2354b2d599675a6fae97db775ae083fc29a838a7  9x9-factorial-union.csv
b55f621fed792aa9db0ab0703c1921c2d89871b1feaeadfa7b9868ca47b332b7  shards/manifest.csv
```

Python `csv.writer` が生成した凍結CSVはCRLFを含む。一方、既存C++ compare solverはheader末尾のCRを除去しない。そのためendpointでは、**上記SHAを元ファイルに対して検査した後にだけ** CRLF→LF のtransport copyを作り、そのcopyをsolverへ渡す。

この正規化はparent、move、行順、membershipを変更しない。raw receiptには元ファイル、実行copy、solver binary、solver出力のSHA256を残す。solver source自体はこのI/O問題のためには変更しない。

### 4. operational failure時の事前固定recovery規則

primary 64-parent shardが以下の**運用上の理由だけ**で完遂できない場合に限り、recovery splitを許す。

- solverが `memo table over 80%` で停止
- runnerがOOM / memory resource exhaustionとして停止

outcome、WIN/LOSS比、discordant数、実行時間の大小、観測されたmemo量を見て分割対象・分割位置・再実行範囲を選んではならない。

recoveryは次の決定的規則だけを使う。

1. 失敗したshardのparentを既存 `canonical_parent` 順のまま取る。
2. `n` parentsなら、先頭 `floor(n/2)` parentsをhalf A、残りをhalf Bとする。
3. A/Bをそれぞれ**完全なfresh process / fresh memo**で最初から解く。
4. 失敗processが途中まで出したoutcomeはendpoint結果へ混ぜない。
5. A/Bのどちらかが同じ許可済み運用理由で失敗した場合、その失敗halfだけに同じ二分規則を再帰適用する（64→32→16→8→4→2→1の方向）。
6. 1 parentでも同じ運用理由で完遂不能なら、endpointは「未完了」とし、統計解析へ進まない。memo power変更やsolver変更を結果確認後に行って同一confirmatory endpointとして扱わない。
7. recovery leaf群は元shardの `(canonical_parent, pair_top, union_top)` 行集合を重複なく完全分割していなければならない。
8. 全primary shardまたはその決定的recovery leafが完遂し、凍結holdoutの必要 `(parent, move)` 集合が完全一致するまでstatistical analysisを開始しない。

recovery input生成には次を使う。

```bash
python3 scripts/split-9x9-factorial-recovery-shard.py \
  /tmp/factorial-union-shards/union-0004.csv \
  /tmp/recovery-0004 \
  --level 1
```

scriptは前半/後半のSHA256とmanifestを出し、2 halfが元shardを正確にpartitionすることを検査する。

runnerの一時的障害、Actions service failure、network/artifact upload failureなど、solver計算そのものと無関係な障害ではshardを細分化しない。同一入力をfresh processでそのまま再実行する。

### 5. 全raw完了後の再構成

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

raw sealing段階では再構成とSHA固定だけを行い、統計解析は実行しない。41 primary shardと必要なrecovery leafの完全性が確認されてから、別段階でpreregistered解析を行う。

## 不変条件

union solve、transport正規化、operational recoveryはいずれも計算共有・実行可能性だけを扱う。以下は変更しない。

- 4つのcomparison membership
- absent / added move
- outcome definition
- discordant parentだけを使うexact binomial test
- Holm family-wise correction
- E comparisonの固定hash sample
- O comparisonのcensus
- 凍結holdoutの必要 `(parent, move)` 集合

したがってunion/sharding/recoveryは確認的推論の標本選択には影響しない。
