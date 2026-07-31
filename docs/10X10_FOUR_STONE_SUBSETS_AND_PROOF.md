# 10×10 four-stone subsets and a verified LOSS proof

This experiment continues from the legal eight-stone LOSS root

```text
90,61,2,73,69,66,13,91
```

and the eleven verified five-stone LOSS subsets. Coordinates use
`id = y * 10 + x`; outcomes are from the player to move.

## Classification of all 70 four-stone subsets

There are `C(8,4) = 70` four-stone subsets.

```text
WIN  = 58
LOSS = 12
```

Thirty-four WIN roots have an explicit legal move to one of the verified
five-stone LOSS roots. The remaining thirty-six roots were solved independently
with the exact C++ searcher using `shrink=3` and `load=80`.

Every independent run completed. There were no table-full or timeout results.

| Metric over the 36 searched roots | Minimum | Maximum |
|---|---:|---:|
| Search visits | 4,973,501 | 36,337,892 |
| Wall time | 8.02 s | 58.30 s |
| Peak RSS | 567,948 KiB | 568,236 KiB |

The complete table is
[`results/10x10/four-stone-subsets-of-medium-loss.csv`](../results/10x10/four-stone-subsets-of-medium-loss.csv).

### The twelve LOSS roots

```text
90,61,2,66
90,61,73,66
90,61,69,66
90,61,66,91
61,2,69,66
61,2,66,91
61,73,69,66
61,73,66,13
61,73,66,91
61,69,66,13
61,69,66,91
61,66,13,91
```

## Complete proof for `61,73,66,13`

The lightest independently measured four-stone LOSS root was selected for full
proof export.

### Exact search and proof extraction

| Metric | Value |
|---|---:|
| Root outcome | LOSS |
| Initial search visits | 9,559,583 |
| Search maximum depth | 19 |
| Search memo entries | 9,517,270 |
| Solver-reported time with witness logging | 37.5238 s |
| Proof nodes | 1,784,457 |
| LOSS proof nodes | 604,383 |
| WIN proof nodes | 1,180,074 |
| Recomputed child searches | 1,180,074 |
| Raw certificate size | 42,827,016 bytes |
| zstd `-10` size | 14,355,441 bytes |
| Search plus extraction wall time | 47.67 s |
| Peak RSS | 2,141,008 KiB |

### Retained winning witnesses

| Metric | Value |
|---|---:|
| Unique retained witnesses | 6,490,893 |
| Witness conflicts | 1,933 |
| Witness hits during proof extraction | 1,180,074 |
| Witness misses during proof extraction | 0 |
| Append-only witness log | 155,781,464 bytes |

A conflict means that the same canonical WIN position was encountered with
more than one valid move to a LOSS child. The first saved move is retained. The
log remains an untrusted performance hint; the completed proof is checked from
scratch by the independent verifier.

### Independent Rust verification

| Metric | Value |
|---|---:|
| Result | `CERTIFICATE VALID` |
| Verified nodes | 1,784,457 |
| LOSS nodes | 604,383 |
| WIN nodes | 1,180,074 |
| Verification wall time | 6.51 s |
| Verification peak RSS | 217,944 KiB |
| Root outcome | LOSS |

The compressed certificate captured in the first run has SHA-256:

```text
8f85f34a1ff895cd394c7ab6bbcc4ee995a9398717254b2bc048edb3ef5cfc31
```

The machine-readable benchmark record is
[`results/10x10/four-stone-loss-proof-61-73-66-13.csv`](../results/10x10/four-stone-loss-proof-61-73-66-13.csv).

## Scaling trend

| Root stones | Proof nodes | Raw certificate | Generation wall time | Verification wall time |
|---:|---:|---:|---:|---:|
| 8 | 3,214 | 77,184 bytes | about 1.6 s | small |
| 6 | 77,726 | 1,865,472 bytes | 16.00 s | 0.28 s |
| 5 | 1,533,310 | 36,799,488 bytes | 36.55 s | 6.32 s |
| 4 | 1,784,457 | 42,827,016 bytes | 47.67 s | 6.51 s |

The proof did not grow monotonically by a fixed factor: the selected four-stone
LOSS root has only about 16% more proof nodes than the selected five-stone root.
Proof size depends strongly on which losing subtrees the retained witnesses
select, not only on the root depth.

## Next depth

There are `C(8,3) = 56` three-stone subsets. Any subset that can move directly
to one of the twelve LOSS roots above is already WIN. The remaining roots are
close to the previously solved early-game branches and are the next meaningful
classification frontier.
