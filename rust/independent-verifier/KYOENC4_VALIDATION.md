# KYOENC4 validation record

GitHub Actions on 2026-08-01 compiled the C++ smoke generator and the Rust
independent verifier, then generated and checked a real 100-bit `KYOENC4`
proof DAG.

## Generated proof

The C++ generator performed a deterministic legal walk on the 10×10 board
until no legal move remained. It selected a walk whose canonical states use
the high 64-bit word, then emitted:

- a 14-stone WIN root;
- witness move ID `95`;
- a 15-stone terminal LOSS child;
- two DAG nodes in total.

Generator output:

```text
KYOENC4 smoke certificate written
board=10x10 nodes=2 forbidden=54441
root_stones=14 terminal_stones=15 witness=95
root_hi=268566704 terminal_hi=269222052
```

The nonzero `root_hi` and `terminal_hi` values confirm that the test exercises
bits 64–99 rather than only parsing a 10×10 header around a 64-bit state.

## Independent Rust result

```text
CERTIFICATE VALID
format=KYOENC4
board=10x10
nodes=2
losing_nodes=1
winning_nodes=1
forbidden_quadruples=54441
root_state=0x00000000100200b00041020250030080
root_stones=14
root_outcome=WIN
conclusion=PLAYER TO MOVE WINS
```

The Rust verifier independently rebuilt the 54,441 forbidden quadruples,
checked that both states were legal and canonical, reconstructed legal moves,
validated witness 95, found the terminal child in the DAG, and confirmed the
rank decrease from root to child.

The same CI run also revalidated C++-generated `KYOENC3` certificates for
1×1 through 6×6, so the new parser remains backward compatible.

## What this establishes

This run establishes that:

- the 128-bit disk layout is implemented consistently by C++ and Rust;
- arbitrary nonempty roots work;
- high-word point IDs work;
- local WIN and LOSS proof obligations work on 10×10;
- `KYOENC3` compatibility remains intact.

It does not yet establish the previously computed full 10×10 classification.
That requires modifying the large 10×10 solver to retain witnesses/outcomes and
emit `KYOENC4` branch DAGs for the completed two-stone and three-stone proofs.
