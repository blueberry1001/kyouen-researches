# 10×10 exact solver KYOENC4 export

`cpp/solvers/kyouen_solver_10_kyoenc4.cpp` is the exact 10×10 solver used by
the branch-by-branch exploration, extended with proof-DAG export.

The original batch interface remains available:

```bash
kyouen-solver-10-kyoenc4 states.txt [shrink=3] [load=80]
```

To solve one legal position and export a `KYOENC4` certificate rooted at that
position using an in-memory proof index:

```bash
kyouen-solver-10-kyoenc4 \
  --certificate \
  '7,16,17,28,30,33,41,48,54,68,69,71,81,92' \
  proof.cert \
  3 80 1000
```

To place the proof-node index in an mmap-backed file, add the index path:

```bash
kyouen-solver-10-kyoenc4 \
  --certificate \
  '7,16,17,28,30,33,41,48,54,68,69,71,81,92' \
  proof.cert \
  3 80 1000 proof.index
```

The full certificate-mode argument list is:

```text
STATE OUTPUT.cert shrink load max_nodes proof_index_file resume checkpoint_after
```

The final three arguments are optional:

- `proof_index_file`: mmap index path; omit it to use RAM;
- `resume`: `1` reopens an existing compatible index, `0` recreates it;
- `checkpoint_after`: intentionally stop after approximately this many completed
  proof nodes; `0` disables the checkpoint.

The solver first computes the exact root outcome. It then traverses only the
proof DAG required for that outcome:

- WIN node: retain one legal move to a LOSS child;
- LOSS node: retain every distinct canonical legal child, all of which must be WIN.

When a needed child is no longer directly available through the compact memo
layout, the solver recomputes that child exactly. The exporter reports the
number of such recomputations.

## Disk-backed proof index

When an index path is supplied, proof membership and metadata use a fixed-size,
open-addressed hash table in a sparse mmap file instead of a C++
`unordered_map`.

Each 24-byte slot stores:

- 128-bit canonical state;
- outcome;
- witness;
- rank;
- lifecycle status.

The lifecycle statuses are:

1. `complete`: all proof obligations below the node are present;
2. `pending`: extraction entered the node but did not finish it;
3. `tombstone`: a pending record discarded during resume while preserving the
   open-addressing probe chain.

The table is sized to keep its maximum load below roughly two thirds. For
example, `max_nodes=1000` creates a 2048-slot index of 49,216 bytes including
the header. A 100-million-node limit selects 268,435,456 slots, requiring about
6.0 GiB of virtual file space. The file can be sparse, but touched pages still
consume storage and operating-system page cache.

## Checkpoint and resume

A controlled checkpoint is useful for testing or for dividing a long run:

```bash
kyouen-solver-10-kyoenc4 \
  --certificate \
  '90,61,2,73,69,66,13,91' \
  proof.cert \
  3 80 10000 proof.index 0 100
```

A checkpoint exits with status code `4`, writes `proof_checkpoint=1` to stderr,
and leaves the mmap index intact. The final certificate is not written because
the root proof is not yet complete.

Resume with the same root and `max_nodes`:

```bash
kyouen-solver-10-kyoenc4 \
  --certificate \
  '90,61,2,73,69,66,13,91' \
  proof.cert \
  3 80 10000 proof.index 1 0
```

On open, the exporter validates the index version, slot size, capacity, root,
maximum node count, and file size. Complete nodes are reused. Pending nodes from
the interrupted call stack are changed to tombstones and recomputed, because
their descendants may be incomplete.

The log reports:

- `resumed_nodes`: complete nodes retained from the previous run;
- `discarded_pending`: interrupted nodes converted to tombstones.

The exact root search itself currently runs again after restart. Resume applies
to proof-DAG extraction, which is the persistent stage.

## Independent validation

CI tests all of the following:

1. a two-node proof with the in-memory index;
2. the same proof with the mmap index;
3. a 6,524-node eight-stone LOSS proof;
4. an interrupted and resumed extraction of that same 6,524-node proof.

Every completed certificate passes the independent Rust verifier. The clean and
resumed medium certificates are also compared as an unordered set of 24-byte
nodes and must be identical.

This tests the full chain:

```text
exact C++ search
→ proof-DAG extraction
→ checkpointed mmap index
→ KYOENC4 serialization
→ independent Rust local-proof verification
```

## Remaining scaling boundary

Restartable disk indexing is now available, but the exporter may still need to
recompute many descendants because the search memo stores only compressed
outcomes and not witnesses. For the previously solved three-stone 10×10
branches, proof extraction can therefore approach another large search.

The next major optimization is to retain the selected WIN witness during the
original search, preferably in an append-only checkpoint file. That would avoid
re-searching many WIN nodes when constructing very large certificates.
