# 10×10 subset probes and a verified six-stone LOSS proof

This experiment continues downward from the legal eight-stone LOSS root

```text
90,61,2,73,69,66,13,91
```

that is used by the medium proof regression.

Coordinates use `id = y * 10 + x`. Outcomes are always from the player to move.
All searches used the exact C++ solver with `shrink=3`, `load=80`, retained
winning witnesses, and an mmap witness index. The final proof was checked by
the independent Rust verifier.

## Seven-stone subsets

Removing each one of the eight stones gives eight seven-stone roots. Every one
is WIN.

This also has a direct game-theoretic explanation: from each subset, restoring
the removed legal point reaches the known eight-stone LOSS root. The exact
search independently confirmed all eight results.

Measured ranges on a GitHub-hosted Ubuntu runner:

| Metric | Minimum | Maximum |
|---|---:|---:|
| Search visits | 2,360 | 24,847 |
| Search maximum depth | 15 | 17 |
| Wall time | 0.59 s | 2.21 s |
| Peak RSS | 640,368 KiB | 756,208 KiB |

The complete table is
[`results/10x10/seven-stone-subsets-of-medium-loss.csv`](../results/10x10/seven-stone-subsets-of-medium-loss.csv).

## Six-stone subsets

Removing every pair of stones gives 28 six-stone roots. A single batch search
with shared memoization completed all 28 roots.

```text
WIN  = 25
LOSS = 3
```

The three LOSS roots are:

```text
90,61,69,66,13,91
90,61,2,69,66,13
90,61,2,73,69,66
```

Batch measurements:

| Metric | Value |
|---|---:|
| Completed roots | 28 / 28 |
| Cumulative memo entries | 6,206,836 |
| Retained winning witnesses | 4,104,439 |
| Witness log size | 98,506,568 bytes |
| Wall time | 22.46 s |
| Peak RSS | 961,256 KiB |

The complete per-root table is
[`results/10x10/six-stone-subsets-of-medium-loss.csv`](../results/10x10/six-stone-subsets-of-medium-loss.csv).

The `memo` and `solver_seconds` columns in that CSV are cumulative because the
28 roots were processed by one solver instance. `visited` is the number of new
recursive visits charged to that root after reuse of the shared memo.

## Complete proof for `90,61,2,73,69,66`

The third six-stone LOSS root was solved again in a fresh process and exported
as a `KYOENC4` proof DAG.

### Exact search and proof extraction

| Metric | Value |
|---|---:|
| Root outcome | LOSS |
| Initial search visits | 432,614 |
| Search maximum depth | 18 |
| Search memo entries | 432,175 |
| Search time reported by solver | 1.81635 s |
| Proof nodes | 77,726 |
| LOSS proof nodes | 27,315 |
| WIN proof nodes | 50,411 |
| Recomputed child searches | 50,411 |
| Raw certificate size | 1,865,472 bytes |
| zstd `-19` size | 464,813 bytes |
| End-to-end wall time | 16.00 s |
| Peak RSS | 1,158,096 KiB |

### Retained witnesses

| Metric | Value |
|---|---:|
| Unique retained witnesses | 286,975 |
| Witness hits during proof extraction | 50,411 |
| Witness misses during proof extraction | 0 |
| Witness-log size | 6,887,432 bytes |

The log reported three witness conflicts. These are not contradictory outcomes:
the same canonical WIN state was encountered with different valid losing moves.
The append-only log keeps the first witness; the final proof remains subject to
full independent validation.

### Independent Rust verification

| Metric | Value |
|---|---:|
| Result | `CERTIFICATE VALID` |
| Verified nodes | 77,726 |
| Verification wall time | 0.28 s |
| Verification peak RSS | 30,172 KiB |
| Root outcome | LOSS |

The detailed machine-readable record is
[`results/10x10/six-stone-loss-proof-90-61-2-73-69-66.csv`](../results/10x10/six-stone-loss-proof-90-61-2-73-69-66.csv).

The first captured compressed certificate has SHA-256:

```text
9998d5f8a6c9d7b2ec4249edffd601af40366dc03337512273efd63e2a94e816
```

The permanent GitHub Actions regression regenerates the raw proof with tighter
index limits and requires the same outcome, search counts, proof-node counts,
certificate size, retained-witness counts, and Rust verification result.

## Implication for the full 10×10 campaign

The data show that the proof pipeline scales smoothly from the 3,214-node
eight-stone benchmark to a 77,726-node six-stone LOSS proof. Both proof-node
membership and winning-witness lookup remain disk-backed, while independent
verification is much lighter than proof generation.

The next useful depth is five stones. There are only six one-stone deletions of
the chosen six-stone LOSS root; probing those parents will show whether a
five-stone LOSS root is available for a still deeper proof benchmark or whether
all six are immediate WIN parents of this root.
