# 9×9 factorial exact endpoint: pre-run receipt

固定日: 2026-09-09

このreceiptはfactorial confirmatory holdoutのexact endpointを開始する**前**に固定する。ここに記載した検査ではfactorial holdoutのchild outcomeを計算・解析していない。

## Frozen workset

```text
parents                     2592
comparison memberships      3402
naive root calls            6804
unique required children    5208
union solver root calls     5232
saved root calls            1572 (23.10%)
primary shards              41
primary parents per shard   64 (last shard 32)
max primary root calls      134
memo power                  28
```

SHA256:

```text
07e60d22eac16834726a5972967e2ae426f2a75f89401f9d4508d1ce033fc840  9x9-confirmatory-1024.csv
5e11b3bd514919c87e2702f60a8e21df026b45ea60fc9044cfa8335da62517fa  9x9-factorial-holdout.csv
9cc23b43fed601db0dae6f4e2354b2d599675a6fae97db775ae083fc29a838a7  9x9-factorial-union.csv
b55f621fed792aa9db0ab0703c1921c2d89871b1feaeadfa7b9868ca47b332b7  shards/manifest.csv
```

## Frozen execution policy

Endpoint workflow:

```text
.github/workflows/factorial-union-exact-frozen.yml
```

functional endpoint integration commit:

```text
9e9913b7a8d264ca3cac975a1d9ff65566aa3d60
```

実行条件:

- `workflow_dispatch` only
- confirmation value `RUN_FROZEN_41_SHARDS`
- 41 primary shardsをcomplete endpointとして扱い、partial subsetをconfirmatory resultとして扱わない
- 1 primary shard = 1 fresh processから開始
- frozen CRLF bytesのSHAを先に検査し、その後だけLF execution copyへ正規化
- solverがexact marker `memo table over 80%` で停止した場合だけrunnerが自動でcanonical-parent順の連続二分を行う
- 自動二分は64→32→16→8→4→2→1まで（max recovery level 6）
- 失敗processの途中outcomeはdiagnosticsとして隔離し、consolidated endpoint resultへ一切使用しない
- exact memo marker以外のfailureは自動二分しない
- OOM等のrunner外resource failureをrecoveryする場合も、`9X9_PAIR_COMPONENT_FACTORIAL_UNION_SOLVE.md` の同じ決定的二分規則だけを使う
- 全必要 `(parent, move)` が揃うまでseal/statistical analysisへ進まない
- raw seal段階はreconstructionとhash固定だけを行い、統計解析を実行しない

## Outcome-free verification receipts

### Workset / source / known-smoke preflight

GitHub Actions run:

```text
34356205087  SUCCESS
```

確認内容:

- frozen 4 SHA256: PASS
- deterministic recovery split 64→32+32: PASS
- recursive recovery split 32→16+16: PASS
- compare solver build: PASS
- committed non-holdout smoke semantic match: PASS

### Synthetic recovery-runner test

GitHub Actions run:

```text
34356005193  SUCCESS
```

確認内容:

- exact memo-limit markerによるrecursive split: PASS
- failed partial output exclusion: PASS
- non-preregistered failureでsplitしない: PASS
- CRLF→LF transport: PASS
- fresh leaf process間で`memo_used`がresetし得るため、memo単調性は各process内だけで検査することを確認

### Real C++ solver through recovery runner

GitHub Actions run:

```text
34356274180  SUCCESS
```

既知の非holdout局面を使い、直接 `kyouen-solver-9-compare` を実行した場合とrecovery runner経由を比較した。

確認内容:

- parent/move identity: PASS
- WIN/LOSS outcomes: PASS
- visited counts: PASS
- memo_used: PASS
- recoveryなしsingle-process path: PASS
- partial failed output used = 0

## Endpoint state at receipt creation

```text
factorial holdout exact endpoint: NOT STARTED
sealed raw endpoint:             NOT CREATED
factorial statistical analysis:  NOT RUN
```

このreceipt以後、confirmatory endpointの結果を見る前に標本、比較方向、Holm family、凍結workset SHA、memo power、recovery split位置を変更しない。
