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

Arguments after the output path are:

1. memo-table shrink value;
2. memo-table load limit percentage;
3. maximum proof-node count;
4. optional mmap proof-index path.

The solver first computes the exact outcome. It then traverses only the proof
DAG required for that outcome:

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
- occupancy marker.

The table is sized to keep its maximum load below roughly two thirds. For
example, `max_nodes=1000` creates a 2048-slot index of 49,216 bytes including
the header. A 100-million-node limit selects 268,435,456 slots, requiring about
6.0 GiB of virtual file space. The file can be sparse, but touched pages still
consume storage and operating-system page cache.

The mmap table removes the requirement that every proof node live in the C++
heap. It does not make disk access free: very large extractions should use a
fast local SSD, and random lookups may still pressure the page cache.

The current index is recreated for each export. Crash-safe resume and merging
multiple branch indexes are separate future extensions.

## Independent validation

CI uses a real 14-stone 10×10 position. The exact solver visits two states,
classifies the root WIN, and exports the same two-node `KYOENC4` DAG twice:

1. using the in-memory index;
2. using the mmap-backed index.

Both certificates pass the independent Rust verifier. CI also compares their
headers and node sets while ignoring serialization order. This tests the full
chain:

```text
exact C++ search
→ proof-DAG extraction
→ memory or mmap index
→ KYOENC4 serialization
→ independent Rust local-proof verification
```

## Remaining scaling boundary

The proof-node index is now disk-backed, but the exporter may still need to
recompute many descendants because the search memo stores only compressed
outcomes and not witnesses. For the previously solved three-stone 10×10
branches, proof extraction can therefore approach another large search.

The next useful measurements are:

1. export several late-game and medium-size roots;
2. record DAG nodes, recomputation count, index size, elapsed time, and peak RSS;
3. decide whether to retain witnesses during the original search or checkpoint
   them into a separate append-only file;
4. add restart support before attempting all 98 children of a two-stone proof.
