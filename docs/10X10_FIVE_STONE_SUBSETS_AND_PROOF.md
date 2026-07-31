# 10×10 five-stone subsets and a verified LOSS proof

This experiment continues from the legal eight-stone LOSS root

```text
90,61,2,73,69,66,13,91
```

and the three six-stone LOSS subsets recorded in the preceding benchmark.
Coordinates use `id = y * 10 + x`; outcomes are from the player to move.

## Classification of all 56 five-stone subsets

There are `C(8,5) = 56` five-stone subsets of the eight-stone root.

```text
WIN  = 45
LOSS = 11
```

Sixteen WIN roots need no new recursive search: each has a legal move to one
of the independently verified six-stone LOSS roots. The remaining forty roots
were solved by the exact C++ searcher.

- Eleven were first completed in one shared-memo batch. That batch later
  stopped because its retained-witness log reached the configured 20-million
  record limit; every result printed before the stop had already completed its
  exact recursive solve.
- The remaining twenty-nine roots were then solved in fresh independent
  processes with witness retention disabled, avoiding that unrelated log-size
  limit.
- All independent jobs completed within 26 seconds each using `shrink=3` and
  `load=80`.
- Peak RSS of the independent jobs was approximately 568 MiB.

The complete table is
[`results/10x10/five-stone-subsets-of-medium-loss.csv`](../results/10x10/five-stone-subsets-of-medium-loss.csv).
For shared-memo rows, `visited` is new recursive work charged to that root while
`memo` and `solver_seconds` are cumulative. For independent rows all metrics are
per root.

### The eleven LOSS roots

```text
90,61,2,73,91
90,61,2,13,91
90,61,73,13,91
90,2,73,66,91
90,2,73,13,91
90,2,69,13,91
90,2,66,13,91
90,73,69,13,91
61,2,73,13,91
2,73,66,13,91
73,69,66,13,91
```

## Complete proof for `61,2,73,13,91`

The lightest independently measured five-stone LOSS root was selected for full
proof export.

### Exact search and proof extraction

| Metric | Value |
|---|---:|
| Root outcome | LOSS |
| Initial search visits | 7,404,873 |
| Search maximum depth | 19 |
| Search memo entries | 7,396,568 |
| Solver-reported search time with witness logging | 30.3503 s |
| Proof nodes | 1,533,310 |
| LOSS proof nodes | 526,809 |
| WIN proof nodes | 1,006,501 |
| Recomputed child searches | 1,006,501 |
| Raw certificate size | 36,799,488 bytes |
| zstd `-19` size | 10,287,255 bytes |
| Search plus extraction wall time | 36.55 s |
| Peak RSS | 1,551,112 KiB |

### Retained winning witnesses

| Metric | Value |
|---|---:|
| Unique retained witnesses | 4,970,738 |
| Witness conflicts | 252 |
| Witness hits during proof extraction | 1,006,501 |
| Witness misses during proof extraction | 0 |
| Append-only witness log | 119,297,744 bytes |

A conflict means that the same canonical WIN state was encountered with two
different valid moves to LOSS children. The first move remains in the log. The
log and its mmap index are performance hints only; they are not trusted proof
input.

### Independent Rust verification

| Metric | Value |
|---|---:|
| Result | `CERTIFICATE VALID` |
| Verified nodes | 1,533,310 |
| LOSS nodes | 526,809 |
| WIN nodes | 1,006,501 |
| Verification wall time | 6.32 s |
| Verification peak RSS | 218,084 KiB |
| Root outcome | LOSS |

The compressed certificate captured in the first run has SHA-256:

```text
2c5801211f57f9be3c4d1399cea2e52fdb00dcb61f1b0ed718359aa487aff1a1
```

The machine-readable benchmark record is
[`results/10x10/five-stone-loss-proof-61-2-73-13-91.csv`](../results/10x10/five-stone-loss-proof-61-2-73-13-91.csv).

## Scaling trend

| Root stones | Proof nodes | Raw certificate | Generation wall time | Verification wall time |
|---:|---:|---:|---:|---:|
| 8 | 3,214 | 77,184 bytes | about 1.6 s | small |
| 6 | 77,726 | 1,865,472 bytes | 16.00 s | 0.28 s |
| 5 | 1,533,310 | 36,799,488 bytes | 36.55 s | 6.32 s |

The five-stone proof is roughly twenty times larger than the six-stone proof,
but still comfortably generated and independently verified on a GitHub-hosted
runner. Verification remains substantially lighter than proof generation.

## Next depth

The next local family contains `C(8,4) = 70` four-stone subsets. Any four-stone
state with a legal move to one of the eleven LOSS roots above is immediately
WIN; only the remaining states require new search. The five-stone measurements
show that those searches may begin to approach the compact memo-table capacity,
so the next probe should preserve completed roots independently rather than
placing every state behind one shared witness-log limit.
