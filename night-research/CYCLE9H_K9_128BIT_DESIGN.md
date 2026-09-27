# Cycle 9H — design notes: 128-bit max-safe solver for K9 (design only)

Status: **historical design / regression plan; project-level question superseded**.
The later related-work audit established that **K9=18 was already published in
2018**. Do not treat K9∈{17,≥18} as open. This file remains useful only as a
128-bit implementation/regression plan for independently reproducing the known
value or as groundwork for n≥10 maximum-safe searches.

## Why 128-bit

- n=9 ⇒ V=81 cells. A safe set does not fit in `uint64_t`.
- Certificates independently show K9 ≥ 17 = 2n−1. The published extremal
  value is K9=18; a 128-bit max-safe solver can independently reproduce an
  18-stone witness, but it is no longer needed to decide an unknown K9 value.
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

## K9 independent-reproduction protocol (optional)

1. Implement Mask128 solver + unit tests (popcount/ctz/subset).
2. Pass n=6/n=7 regression table.
3. n=8: confirm first@15 witness; optional short count sample.
4. n=9: search for a size-18 witness as an independent reproduction of the
   published K9=18 value. If not found after an agreed budget, record
   **incomplete**, not a contradiction of the published value.
5. Do **not** spend resources on UNSAT@18: K9=18 already supplies a size-18
   witness externally, so UNSAT@18 would target a false statement.

## Explicit non-claims

- This historical file does **not** establish K9 by itself.
- Certificate lower bound K9≥17 is inherited, not re-proved here.
- Project-level status uses the prior published value **K9=18** documented in
  `docs/RELATED_WORK.md`.
- Do not start K9 UNSAT@18; use the design only for witness reproduction or
  larger-board tooling.
