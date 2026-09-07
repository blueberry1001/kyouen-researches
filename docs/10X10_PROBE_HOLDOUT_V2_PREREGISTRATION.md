# 10x10 fresh-memo probe clean holdout V2 preregistration

Base branch: `blind-probe-holdout-validation`
Base SHA: `2bcd387102874ee20ee641ebd7311c0101d849b5`

This document freezes the second independent confirmatory holdout **before collecting any V2 probe rows or full exact child labels**. V2 reuses the successful V1 rule without changing its direction or primary endpoint.

## Independence from earlier work

V2 excludes every 3-stone parent D4 orbit that appeared in the pre-V1 blind parent-selection table. This covers both the exploratory parents and all 11 V1 confirmatory parents. The 20 source rows in that old table collapse to 19 distinct D4 orbits because `0,31,36` occurred in both source groups.

The excluded representatives are:

- `2,9,33`
- `4,9,33`
- `9,12,33`
- `9,19,33`
- `9,23,33`
- `0,31,36`
- `0,36,43`
- `0,36,44`
- `0,36,50`
- `9,33,54`
- `0,1,13`
- `0,7,31`
- `0,17,31`
- `0,13,34`
- `0,13,44`
- `0,2,13`
- `0,3,13`
- `0,10,13`
- `0,13,21`

Exclusion is by D4-canonical parent identity, not merely by the listed orientation.

## Outcome-blind V2 parent selection

The fixed source pool is the pre-existing rows of:

- `results/10x10/two-stone-90-66-child-proof.csv`
- `results/10x10/two-stone-90-61-child-proof.csv`

Only the parent `state`, source file, and source row index are used for selection. Existing witness-child fields are not used to choose among eligible parents, choose orientation, choose a ranking direction, or tune any metric.

Selection algorithm:

1. take every 3-stone parent row in the two fixed source files;
2. D4-canonicalize each parent on the 10x10 board;
3. remove every canonical orbit listed in the independence exclusion above;
4. deduplicate equal canonical triples across and within source files;
5. sort lexicographically by canonical triple;
6. take the first 20 canonical parents;
7. for each selected orbit, retain the earliest source occurrence of that orbit as the execution orientation.

The resulting identities are frozen in `results/10x10/holdout-v2-parent-selection-preregistered.csv`. No V2 parent may be removed, replaced, reordered, or subset after probe or exact outcomes are observed.

## Candidate children

For each selected safe 3-stone parent, candidate children are generated deterministically in ascending added-cell order. A fourth stone is included iff the resulting four points are neither collinear nor concyclic, tested by the exact integer determinant

```text
| x^2+y^2  x  y  1 |
```

being nonzero. This is the game legality rule specialized to a 3-stone parent, so no outcome information is involved. The complete ordered task sequence is hashed into each run protocol.

## Primary probe protocol

Primary budget: **1,000,000 visited states per child**.

Every candidate child is probed in a fresh solver process / fresh `Solver` instance. No transposition table, cumulative timer, or solver state may be shared between candidates.

Fixed probe parameters remain V1-compatible:

- shrink: `3`
- load: `80`
- budget: `1,000,000`

Secondary budgets, after the primary V2 result is frozen: `10,000` and `100,000` visited states per child. They are stability diagnostics and do not replace the primary result.

## Frozen ranking rule

For each parent's candidate children:

1. probe-proved `LOSS` first;
2. otherwise unresolved (`PROBE`) children by ascending independent `memo_used`;
3. probe-proved `WIN` last;
4. ties by ascending added cell index.

The direction is not allowed to change after V2 outcomes are seen.

Comparators are unchanged:

- independent-memo descending;
- solver/default child order;
- reverse default order;
- uniformly random permutation reference.

## Primary endpoint

For every selected parent, compute the rank of the first exact-`LOSS` child under the frozen ranking.

For `m` candidate children and `l` exact-`LOSS` children:

`E[R] = (m+1)/(l+1)`

and

`P(R <= r) = 1 - C(m-r,l)/C(m,l)`.

Use the exact random median from this distribution. Across parents classify the frozen rank as better / tie / worse than that median. The primary directional test is a **one-sided exact sign test**, excluding ties. Always report all parent-level ranks and effect sizes.

As in V1, also compute the exact convolution null for the sum of first-LOSS ranks as a within-parent random-order benchmark; it is not a population-generalization p-value.

## Secondary endpoint

For each parent containing at least one exact `LOSS` and one exact `WIN`, compute candidate-level AUC from the frozen ordering. Report every parent AUC plus mean and median. A pooled AUC, if reported, is secondary only.

## Diagnostic work (P4-P7)

After the primary V2 result is immutable, run:

- 10k / 100k rank-stability analysis;
- depth-wise diagnostic instrumentation (`visited_by_depth`, memo lookup/hit/put, generated-child count, proof termination depth) without changing primary ranking;
- additional descriptive metrics that do not replace the primary endpoint;
- exact-search node-count ordering as an explicitly exploratory mechanism test;
- provenance / coverage verification for all probe and exact rows.

Any heuristic discovered from V2 is exploratory and requires a later independent holdout for confirmation.
