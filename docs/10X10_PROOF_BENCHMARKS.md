# 10×10 KYOENC4 proof-extraction benchmarks

These measurements establish deterministic regression cases for the exact
10×10 solver, the mmap proof index, and the independent Rust verifier.

## Environment used for the first measurement

- Linux x86-64
- five available CPU cores, although one solver process is single-threaded
- approximately 5.9 GiB physical RAM
- C++20, `g++ -O2`
- solver options: `shrink=3`, `load=80`

Elapsed time and RSS are environment-dependent. Outcome, search visit count,
DAG node count, recomputation count, and file sizes are deterministic for the
current implementation and move ordering.

## Two-node late-game WIN proof

Root point IDs:

```text
7,16,17,28,30,33,41,48,54,68,69,71,81,92
```

Results:

| Field | Value |
|---|---:|
| Root stones | 14 |
| Root outcome | WIN |
| Search visits | 2 |
| Proof nodes | 2 |
| Recomputed children | 1 |
| Certificate size | 96 bytes |
| mmap index limit | 1,000 nodes |
| mmap index size | 49,216 bytes |

This is the fast smoke test used to exercise the complete export pipeline.

## Medium eight-stone LOSS proof

Root point IDs:

```text
90,61,2,73,69,66,13,91
```

Results from the first local run:

| Field | Value |
|---|---:|
| Root stones | 8 |
| Root outcome | LOSS |
| Search visits | 10,471 |
| Maximum search depth | 17 |
| Search memo entries after export | 24,499 |
| Proof nodes | 6,524 |
| Recomputed child searches | 8,778 |
| Certificate size | 156,624 bytes |
| mmap index limit | 10,000 nodes |
| mmap index capacity | 16,384 slots |
| mmap index size | 393,280 bytes |
| Initial observed peak RSS | about 603 MiB |
| Initial observed wall time | about 1.6 seconds |

The proof contains a LOSS root, so the exporter must include every distinct
canonical legal child and recursively prove each one WIN. It is therefore a
substantially stronger regression test than the two-node WIN example.

CI regenerates this certificate from scratch and requires:

- exact root result `LOSS`;
- exactly 6,524 DAG nodes;
- exactly 8,778 recomputations;
- the expected certificate and index sizes;
- successful independent Rust verification of all local proof obligations.

## Checkpoint and resume of the medium proof

The same eight-stone root was intentionally stopped with
`checkpoint_after=100`.

The interruption left:

| Field | Value |
|---|---:|
| Complete reusable nodes | 102 |
| Pending call-stack nodes | 3 |
| Exit status | 4 |
| Completed certificate | not written |

The slight overshoot beyond 100 is expected: the threshold is checked when a
new node is entered, while recursive descendants may finish as the call stack
unwinds.

The second invocation reopened the same index with `resume=1`:

| Field | Value |
|---|---:|
| Reused complete nodes | 102 |
| Discarded pending nodes | 3 |
| Final proof nodes | 6,524 |
| Current-run recomputations | 8,662 |
| Final certificate size | 156,624 bytes |
| Final index size | 393,280 bytes |

The resumed proof has the same header and the same unordered set of 6,524 node
records as the clean extraction. It also passes the independent Rust verifier.

The reduction from 8,778 to 8,662 current-run recomputations shows that finished
subproofs were actually reused rather than merely rediscovered. The root game
search still runs again; only proof-DAG extraction is resumed at this stage.

## Interpretation

For this medium case, the final proof DAG is smaller than the amount of search
work used to reconstruct it: 6,524 stored nodes versus 8,778 recomputed child
searches in a clean run. This confirms that witness retention during the
original search could meaningfully reduce export work for much larger
early-game roots.

Checkpointing now protects long proof-extraction runs from losing all completed
subproofs. The next optimization should persist selected WIN witnesses during
the original exact search, reducing the recomputation still required after a
restart.

The next benchmark tier should use seven- and six-stone roots, but those should
not be promoted into mandatory CI until their runtime and memory requirements
are stable on GitHub-hosted runners.
