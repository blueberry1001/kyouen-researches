# 10×10 exact solver KYOENC4 export

`cpp/solvers/kyouen_solver_10_kyoenc4.cpp` is the exact 10×10 solver used by
the branch-by-branch exploration, extended with proof-DAG export.

The original batch interface remains available:

```bash
kyouen-solver-10-kyoenc4 states.txt [shrink=3] [load=80]
```

To solve one legal position and export a `KYOENC4` certificate rooted at that
position:

```bash
kyouen-solver-10-kyoenc4 \
  --certificate \
  '7,16,17,28,30,33,41,48,54,68,69,71,81,92' \
  proof.cert \
  3 80 1000
```

Arguments after the output path are:

1. memo-table shrink value;
2. memo-table load limit percentage;
3. maximum number of proof nodes retained in RAM.

The solver first computes the exact outcome. It then traverses only the proof
DAG required for that outcome:

- WIN node: retain one legal move to a LOSS child;
- LOSS node: retain every distinct canonical legal child, all of which must be WIN.

When a needed child is no longer directly available through the compact memo
layout, the solver recomputes that child exactly. The exporter reports the
number of such recomputations.

## Independent validation

CI uses a real 14-stone 10×10 position. The exact solver visits two states,
classifies the root WIN, exports a two-node `KYOENC4` DAG, and passes the file
to the independent Rust verifier. This tests the full chain:

```text
exact C++ search
→ proof-DAG extraction
→ KYOENC4 serialization
→ independent Rust local-proof verification
```

## Current scaling boundary

The exporter currently keeps `state -> outcome/witness/rank` for the extracted
proof DAG in an in-memory `unordered_map`. This is suitable for testing and for
small or moderate late-game roots. It is not yet suitable for the previously
solved three-stone 10×10 branches, whose proof DAGs may contain tens or hundreds
of millions of nodes.

Before exporting the complete 10×10 classification, this in-memory proof index
should be replaced or supplemented by a disk-backed index. The search memo may
remain compact and depth-specific; only the extracted proof records and
membership lookups need external storage. The `max_nodes` argument prevents an
accidental unbounded allocation while that work is incomplete.
