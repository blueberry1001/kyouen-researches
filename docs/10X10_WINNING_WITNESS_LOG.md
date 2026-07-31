# 10×10 winning-witness retention

The exact 10×10 solver can persist the move that proved each canonical WIN
position. These records are used during later `KYOENC4` extraction so the
exporter does not have to rediscover a losing child for every WIN node.

## Command line

Certificate mode accepts two additional trailing arguments:

```text
solver --certificate STATE OUTPUT.cert \
  [shrink] [load] [max_nodes] [proof_index] [proof_resume] [checkpoint_after] \
  [witness_log] [witness_resume]
```

Example:

```bash
kyouen-solver-10-kyoenc4 \
  --certificate \
  '90,61,2,73,69,66,13,91' \
  proof.cert \
  3 80 50000 proof.index 0 0 winning-witnesses.log 0
```

To reuse the same log in a later process, change the last argument to `1`.

Batch search also supports witness retention:

```text
solver STATES_FILE [shrink] [load] [witness_log] [witness_resume]
```

## Coordinate handling

The recursive solver may reach a state in any rotated or reflected orientation.
Before recording a witness it:

1. identifies the transform that produced the canonical state;
2. transforms the selected move through the same symmetry;
3. stores the canonical 128-bit state and canonical point ID.

The saved point ID is therefore directly legal on the canonical state later
reconstructed by the certificate exporter.

## File format

The log starts with a 32-byte header followed by 24-byte fixed records.

Header:

```text
magic[8] = "KYOENW1"
u32 version = 1
u32 record_size = 24
u64 record_count
u64 reserved
```

Record:

```text
u64 state_lo
u64 state_hi
u8  witness
u8  rank
u16 reserved
u32 reserved
```

Records are only appended. The count in the header is advisory metadata. On
resume, the implementation derives the usable record count from file length;
a partial final record is truncated. This permits recovery if a process stops
in the middle of the last append.

## Medium regression result

Root:

```text
90,61,2,73,69,66,13,91
```

| Metric | Without retained witnesses | With retained witnesses |
|---|---:|---:|
| Root outcome | LOSS | LOSS |
| Initial exact-search visits | 10,471 | 10,471 |
| Proof nodes | 6,524 | 3,214 |
| Proof child recomputations | 8,778 | 2,046 |
| Certificate size | 156,624 bytes | 77,184 bytes |
| Saved witnesses | 0 | 6,776 |
| Witness-log size | 0 | 162,656 bytes |
| Witness hits during export | 0 | 2,046 |
| Witness misses during export | n/a | 0 |

The proof is smaller because the search-selected witness may lead to a smaller
valid losing subproof than the exporter's previous first-legal-move scan.
The independent Rust verifier accepts the resulting 3,214-node DAG.

A second process loads all 6,776 records, appends no new records, and reproduces
the same proof node set. CI also appends five junk bytes to simulate a torn
final record; resume truncates the tail and again reproduces the same proof.

## Trust boundary

The witness log is a performance hint, not trusted proof input. The exporter
checks that the saved point is legal, and the completed `KYOENC4` DAG is then
validated independently by Rust. A wrong saved move therefore cannot make an
invalid game result pass verification.

## Current scaling boundary

The log itself is append-only and persistent, but its lookup index is currently
rebuilt into an in-process `unordered_map` on startup. This is appropriate for
thousands or millions of records, but not for the tens or hundreds of millions
that a full early-game 10×10 campaign may produce.

The next scaling step is a persistent mmap hash index paired with this log, so
lookup can remain disk-backed without loading every state into the C++ heap.
