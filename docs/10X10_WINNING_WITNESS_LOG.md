# 10×10 winning-witness retention

The exact 10×10 solver can persist the move that proved each canonical WIN
position. These records are used during later `KYOENC4` extraction so the
exporter does not have to rediscover a losing child for every WIN node.

## Command line

Certificate mode accepts witness-log and optional mmap-index arguments:

```text
solver --certificate STATE OUTPUT.cert \
  [shrink] [load] [max_nodes] [proof_index] [proof_resume] [checkpoint_after] \
  [witness_log] [witness_resume] [witness_index] [witness_max_records]
```

In-memory lookup example:

```bash
kyouen-solver-10-kyoenc4 \
  --certificate \
  '90,61,2,73,69,66,13,91' \
  proof.cert \
  3 80 50000 proof.index 0 0 winning-witnesses.log 0
```

Disk-backed lookup example:

```bash
kyouen-solver-10-kyoenc4 \
  --certificate \
  '90,61,2,73,69,66,13,91' \
  proof.cert \
  3 80 50000 proof.index 0 0 \
  winning-witnesses.log 0 winning-witnesses.index 10000
```

To reuse the files in a later process, set `witness_resume` to `1`.

Batch search supports the same witness storage:

```text
solver STATES_FILE [shrink] [load] \
  [witness_log] [witness_resume] [witness_index] [witness_max_records]
```

## Coordinate handling

The recursive solver may reach a state in any rotated or reflected orientation.
Before recording a witness it:

1. identifies the transform that produced the canonical state;
2. transforms the selected move through the same symmetry;
3. stores the canonical 128-bit state and canonical point ID.

The saved point ID is therefore directly legal on the canonical state later
reconstructed by the certificate exporter.

## Append-only log format

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

## mmap index format

When `witness_index` is supplied, lookups use an open-addressed mmap hash table
instead of loading every record into an `unordered_map`.

The 64-byte index header stores:

```text
magic[8] = "KYOENWI"
u32 version = 1
u32 slot_size = 24
u64 capacity
u64 max_records
u64 indexed_records
u64 unique_count
u64 log_record_size
u64 reserved
```

Each 24-byte slot stores the 128-bit state, witness, rank, and occupancy status.
The capacity is the smallest power of two large enough to keep the configured
maximum load below roughly two thirds. For example, a 10,000-record limit uses
16,384 slots and a 393,280-byte index file.

The append-only log remains the source of truth. The mmap index is a rebuildable
cache:

- if the index exists and covers the whole log, startup performs no log scan;
- if the log contains additional complete records, only that tail is indexed;
- if the index is missing, it is rebuilt from every complete log record;
- if the index claims to cover more records than the log contains, startup
  rejects the inconsistent pair;
- if `max_records` differs from the value stored in an existing index, startup
  rejects it instead of silently using the wrong capacity.

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
| Witness-index size at 10,000 limit | n/a | 393,280 bytes |
| Witness hits during export | 0 | 2,046 |
| Witness misses during export | n/a | 0 |

The proof is smaller because the search-selected witness may lead to a smaller
valid losing subproof than the exporter's previous first-legal-move scan.
The independent Rust verifier accepts the resulting 3,214-node DAG.

CI verifies both lookup modes. For mmap lookup it additionally checks:

1. direct reuse in another process with `rebuilt_records=0`;
2. deletion and complete reconstruction of all 6,776 index entries;
3. catch-up when the log is one complete record ahead of the index;
4. identical `KYOENC4` header and node set in every case.

## Trust boundary

The witness log and its mmap index are performance hints, not trusted proof
input. The exporter checks that the saved point is legal, and the completed
`KYOENC4` DAG is then validated independently by Rust. A wrong saved move
therefore cannot make an invalid game result pass verification.

## Current scaling boundary

Both the proof-node index and the winning-witness lookup can now remain
disk-backed. The main remaining cost for early-game roots is the exact search
itself and the number of LOSS obligations that must appear in the final proof.

Before attempting every previously solved three-stone branch, the next useful
step is to benchmark seven- and six-stone roots with witness retention enabled,
record proof size, witness-log growth, page-cache pressure, elapsed time, and
peak RSS, and then choose practical checkpoint and shard sizes for the full
campaign.
