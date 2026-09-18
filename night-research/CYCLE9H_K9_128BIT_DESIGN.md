# Cycle 9H — design notes: 128-bit max-safe solver for K9 (design only)

Status: **design / regression plan only**. Do **not** launch long K9 UNSAT
until n=7/n=8 known-value regression tests pass on the new representation.

## Why 128-bit

- n=9 ⇒ V=81 cells. A safe set does not fit in `uint64_t`.
- Certificates already show K9 ≥ 17 = 2n−1; deciding K9 ∈ {17, ≥18} needs
  a max-safe solver that can try size 18 (existence) or prove UNSAT@18.
- n=8 K=15 is proven (Cycle 5/6). n=7 K=14 proven.

## State representation

```
struct Mask128 { uint64_t lo, hi; };  // bit i of board = cell id i
// cell id = y*9+x, 0..80; lo holds bits 0..63, hi bits 64..80
```

Operations needed: `popcount`, `ctz`, `and/or/andnot`, `get/set`, `subset`.

## Geometry

- Same integer determinant test: rows `[x²+y², x, y, 1]`, det=0 ⇒ forbidden quad.
- Precompute `triples_by_point[81]`: each entry a vector of Mask128 “other 3”
  of every forbidden quad through that point.
- Expected forbidden-quad count on 9×9: 29,152 (from certificate table).

## Search

Reuse Cycle 6/8 enum-style DFS:

```
dfs(cand, count, chosen, ccount):
  if count == K: record; return
  if popcount(cand) + count < K: return
  for u in ctz-iterate(cand):
    take u; update ccount for triples completing 2-in-chosen
    dfs(newcand, count+1, chosen|u)
    undo; drop u from cand
```

Branch-and-bound for **max** size:

- `best` lower bound from known witnesses (seed 17 on n=9).
- Prune when `count + popcount(cand) <= best`.
- Optional D4 canonical filter for counting distinct max sets.

Constraints (port of `cycle8_b_maxsafe`):

- `--force` / `--forbid` / `--forbid-orbit` / `--require-orbit` / `--corners`
- Node budget + `complete` flag (never claim UNSAT on incomplete runs).

## Regression tests (must pass before K9 UNSAT)

| board | expected | source |
|---|---|---|
| n=6 K=11 count | 464 | complete enum Cycle 6 |
| n=7 K=14 count | 16 | complete enum Cycle 6 |
| n=7 force center count@14 | 8 | Package B COMPLETE |
| n=7 force (2,2) count@14 | 0 | Package B COMPLETE |
| n=7 max with (2,2) | 13 | Package B COMPLETE |
| n=8 K=15 first | witness exists (e.g. cycle6 json / `3120140120888207`) | proven K8=15 |
| n=8 K=16 | UNSAT only after long run — **not** a cheap regression | — |

Cross-check: Python `cycle8_lib` geometry vs C++128 on n=7 quad count = 6364
and n=8 = 14564.

## K9 experiment protocol (when authorized)

1. Implement Mask128 solver + unit tests (popcount/ctz/subset).
2. Pass n=6/n=7 regression table.
3. n=8: confirm first@15 witness; optional short count sample.
4. n=9: search for size-18 witness with high node budget; if found, K9≥18.
   If not found after agreed budget, record **incomplete**, not UNSAT.
5. Full UNSAT@18 only with logging, checkpointing, and independent re-run plan.

## Explicit non-claims

- This file does **not** decide K9.
- Certificate lower bound K9≥17 is inherited, not re-proved here.
- Do not start overnight K9 UNSAT from this design alone.
