# KYOENC4 certificate format

`KYOENC4` is the 128-bit successor to `KYOENC3`. It is intended for
independently checkable WIN/LOSS proof DAGs on square boards with at most
128 points, including 10×10 and 11×11.

All integer fields are little-endian. Files contain one fixed-size header
followed by `node_count` fixed-size nodes. No compiler padding is present.

## Header: 48 bytes

| Offset | Size | Field | Meaning |
|---:|---:|---|---|
| 0 | 8 | `magic` | ASCII `KYOENC4` followed by NUL |
| 8 | 4 | `version` | `4` |
| 12 | 4 | `board_size` | Side length `N`; `N² <= 128` |
| 16 | 8 | `node_count` | Number of following nodes |
| 24 | 8 | `root_lo` | Root state bits 0–63 |
| 32 | 8 | `root_hi` | Root state bits 64–127 |
| 40 | 8 | `forbidden_count` | Number of concyclic/collinear quadruples |

Unlike `KYOENC3`, the root need not be empty. This is essential for split
10×10 proofs: each two-stone or three-stone branch can be certified as its own
DAG without rebuilding one enormous empty-board certificate.

The root must be a legal canonical state and must occur among the nodes.

## Node: 24 bytes

| Offset | Size | Field | Meaning |
|---:|---:|---|---|
| 0 | 8 | `state_lo` | State bits 0–63 |
| 8 | 8 | `state_hi` | State bits 64–127 |
| 16 | 1 | `outcome` | `1 = LOSS`, `2 = WIN` for the player to move |
| 17 | 1 | `witness` | Winning move ID, or `255` for LOSS |
| 18 | 1 | `rank` | `N² - popcount(state)` |
| 19 | 1 | `flags` | Must be zero in version 4 |
| 20 | 4 | `reserved` | Must be zero |

Every state is stored in the minimum numeric representative under the eight
symmetries of the square. Numeric comparison treats the 128-bit state as an
unsigned integer, so `state_hi` is compared before `state_lo`.

## Proof obligations

The checker reconstructs legal moves from the occupied set and does not trust
any legal-move mask from the generator.

For every WIN node:

1. `witness` is a legal move.
2. The canonical child obtained by adding the witness exists in the file.
3. That child is LOSS.
4. The child rank is exactly one less.

For every LOSS node:

1. `witness == 255`.
2. Every distinct canonical legal child exists in the file.
3. Every such child is WIN.
4. Every child rank is exactly one less.

Because rank strictly decreases along every edge, these local checks establish
the root result without running a game-tree search.

## Current implementation boundary

The Rust verifier reads node records in two streaming passes and does not retain
the raw certificate bytes. It currently keeps a compact state-to-node index in
RAM, so memory use is still linear in the number of DAG nodes. Chunked external
indexes and cross-file references are deliberately left for a later format or
an optional container layer; the on-disk `KYOENC4` node semantics above remain
suitable for individual 10×10 branch certificates.

## Smoke test

`cpp/certificate/kyouen_certgen_v4_smoke.cpp` constructs a legal 10×10 terminal
position by a deterministic legal walk. It emits a two-node proof:

- root: WIN, with one legal witness;
- witness child: terminal LOSS.

The generator requires the resulting certificate to use the high 64-bit word,
so CI exercises the 100-bit state representation rather than only the header.
