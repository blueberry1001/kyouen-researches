# 10x10 below-root memo instrumentation preregistration

Branch: `instrument-10x10-below-root-memo`

This document freezes the next mechanism-measurement plan before any new
instrumented solver result is inspected. It does **not** change any previous
parent-benchmark endpoint and does not authorize a new 100k/1M probe cohort.

## Motivation

The completed V2 proof-cost analysis showed:

- native root ordering selects a LOSS at median 1.12x the cheapest exact LOSS;
- 10k memo ordering selects a LOSS at median 1.79x oracle;
- `legal_move_count` predicts exact LOSS proof cost much better than 10k memo;
- an additive entered-prefix proxy reproduces parent exact-work ratios to about
  2%, so root-order failure is already explained without a cross-child memo term.

The remaining high-value question is therefore not root ranking but where memo
reuse saves work *inside* the recursive solver.

## Frozen counters

Instrumentation must not alter ordering, memo contents, stopping conditions, or
returned outcomes. Counters are observational only.

For every exact solve, collect at least:

1. `entry_memo_queries`: calls to memo lookup on entry to `win`.
2. `entry_memo_hits`: nonzero entry lookups.
3. `entry_memo_hit_win` / `entry_memo_hit_loss`.
4. `child_memo_queries`: lookups while constructing unique children.
5. `child_memo_hits`, split into WIN and LOSS.
6. `memo_put_win` / `memo_put_loss`.
7. `children_generated`: legal moves considered before D4 deduplication.
8. `children_unique`: unique canonical children retained.
9. `children_duplicate`: canonical duplicates removed.
10. `children_recurred`: children actually entered recursively because they were
    not already memo-cached and were reached before cutoff.
11. `winning_cutoffs`: WIN nodes that stop after discovering a LOSS child.
12. depth-indexed versions of entry queries/hits, child queries/hits, puts, and
    recursive entries for depths 0..19.

Primary derived quantities:

- entry hit rate = `entry_memo_hits / entry_memo_queries`;
- child pre-hit rate = `child_memo_hits / child_memo_queries`;
- LOSS-hit share among memo hits;
- recursive-entry avoidance = `1 - children_recurred / children_unique_reached`;
- canonical-dedup fraction = `children_duplicate / children_generated`;
- per-depth contribution of memo hits and puts.

## First validation, before any cohort run

Use only tiny regression states already present in repository tests/examples.
For each state, instrumented and uninstrumented builds must agree on:

- outcome;
- `visited`;
- `maxdepth`;
- final `memo_used`;
- root diagnostics when enabled.

Counters must satisfy:

- `entry_memo_hits <= entry_memo_queries`;
- `child_memo_hits <= child_memo_queries`;
- WIN+LOSS hit splits equal total hits;
- WIN+LOSS puts equal total puts;
- depth sums equal global counters;
- `children_unique + children_duplicate == children_generated` for generated
  canonical child candidates;
- no counter overflow in the intended 64-bit range.

Any disagreement in solver outcome or `visited` invalidates the instrumented
build until explained.

## First scientific use

Do **not** begin with the full 12-parent benchmark. Start with existing mechanism
cases chosen before seeing instrumentation results:

- `14,64,74`: single-entry, native oracle LOSS, 10k selected ~4.17x-cost LOSS;
- `3,53,84`: single-entry, native oracle LOSS, 10k selected ~2.05x-cost LOSS;
- `13,52,57`: single-entry exception where 10k selected a cheaper LOSS;
- `12,32,55`: multi-entry worst case with four WINs before B's first LOSS.

The first question is descriptive:

> Which memo events distinguish cheap and expensive LOSS proofs, after root
> ordering has already selected the child?

No success threshold is preregistered yet. This stage is mechanism discovery,
not a confirmatory speed claim.

## Hypotheses to test, without changing them after seeing results

H1. Cheap LOSS proofs have a higher *useful memo-hit density* than expensive
LOSS proofs, where density is measured per visited state rather than final memo
size.

H2. The strongest separation occurs below the root, especially in child
pre-hits and entry hits at intermediate depths, not in final `memo_used`.

H3. If memo hit-rate profiles are weak or inconsistent across the frozen four
cases, root ordering should remain deprioritized and attention should move to
proof/certificate structure rather than another probe budget.

These are exploratory mechanism hypotheses. Any later predictor or optimization
must be frozen on a new cohort before being called confirmatory.
