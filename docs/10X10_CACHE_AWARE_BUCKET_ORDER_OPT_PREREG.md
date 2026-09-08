# Preregistration: 10x10 cache-aware ordering implementation optimization

Date: 2026-09-08
Base: `e9d0460b55b7f058379da2a843ecea33525b86ea`
Status: frozen before any bucket-implementation solver timing result exists.

## Objective

C1 and the independently pre-frozen capacity-rescued confirmation both showed that using cached child outcomes in below-root ordering reduces exact visited work. The confirmed rule is:

`cached LOSS < unknown < cached WIN`, then `legal_move_count ascending`, then canonical key ascending.

The current implementation realizes this as one `std::sort` whose comparator recomputes the 3-way cached priority on every comparison. This experiment asks a different question: can the **identical total order** be implemented more cheaply by separating cached classes once, then sorting only within each class?

This is an implementation-performance experiment, not a new search heuristic.

## Frozen implementations

Use one binary with a runtime switch `--cache-aware-order-impl sort|bucket`.

### S: sort baseline

Exactly the current cache-aware implementation from base `e9d0460`:

1. `cached LOSS`
2. `unknown`
3. `cached WIN`
4. `legal_move_count ascending`
5. canonical key ascending

implemented by a single `std::sort` comparator.

### B: bucket implementation

Only for cache-aware nodes strictly below frozen root depth 3:

1. partition the existing `Child[0:n)` range into three contiguous classes in the same priority order: cached LOSS, unknown, cached WIN;
2. sort each class subrange independently by exactly `(legal_move_count ascending, canonical key ascending)`;
3. concatenate implicitly by the contiguous subranges.

Root-depth behavior remains the historical S implementation. Cache-blind behavior is untouched.

No child may be dropped, duplicated, newly memo-looked-up, or have `cached/count/key` recomputed differently.

Because canonical child keys are unique after the existing duplicate-elimination stage, `(class, count, key)` is a total order. Therefore B is intended to be order-equivalent to S, not merely outcome-equivalent.

## Forbidden changes

Before this endpoint completes, do not change:

- memo capacities, shrink, or load;
- memo lookup/prefetch/put semantics;
- cached outcome encoding;
- duplicate elimination;
- canonicalization;
- game rules;
- root ordering;
- legal-move-count calculation;
- witness logic;
- instrumentation semantics;
- search stopping rules.

The implementation diff must be limited to selecting S versus B for the already-confirmed cache-aware ordering implementation and associated provenance/tooling.

## Static/order equivalence gate

Before any timing endpoint run:

1. Add a deterministic unit test that generates synthetic child arrays covering all three cached classes, ties in `count`, and adversarial input permutations.
2. Require the exact ordered sequence of canonical keys from S and B to match for every fixture.
3. Include exhaustive permutations for small synthetic arrays where practical.
4. Fail closed on any order mismatch.

## Solver semantic parity gate

Use the original C1 12-parent cohort (`d9b9a0f`) because it is fixed, already exact, manageable in cost, and was not selected for this implementation optimization.

Run B once per parent and compare with the frozen historical cache-aware S result. Require exact equality for all 12 on:

- outcome;
- exact visited;
- exact memo used;
- maxdepth;
- depth_visited vector;
- root unique/entered/first/witness;
- memo instrumentation counters, except any newly added implementation-only timing/comparison counters.

If any semantic/work counter differs, the optimization endpoint is FAIL-SAFETY and no speed claim may be made.

## Timing benchmark cohort

If and only if semantic parity passes 12/12, benchmark the same fixed C1 12 parents.

For each parent perform 3 paired repetitions of S and B in fresh processes, serially, using one byte-identical binary. Counterbalance within each repetition:

- odd parent rank: S->B for repetitions 1 and 3, B->S for repetition 2;
- even parent rank: B->S for repetitions 1 and 3, S->B for repetition 2.

No parallel endpoint runs.

For each parent and implementation, define timing as the median solver-reported seconds over the 3 repetitions. Wall time is secondary.

## Primary performance endpoint

For parent i:

`T_i = median_seconds_S / median_seconds_B`

B is faster iff `T_i > 1`.

Performance PASS requires both:

1. median `T_i > 1` across the 12 parents;
2. B faster on at least 7 of 12 parents.

There is no minimum effect-size threshold. Exact visited parity remains a mandatory prerequisite and cannot be traded against time.

If semantic parity fails, timing is not interpreted.

## Secondary outputs

After all paired runs complete:

- parent-level T;
- geometric/arithmetic mean T;
- aggregate solver-seconds S/B;
- wall-time ratios;
- faster/tie/slower counts;
- paired sign test on direction;
- optional comparator-call and partition-move counts if implemented before execution freeze;
- speedup versus child count / cached-hit fraction, descriptive only.

## Execution provenance

Before endpoint timing runs, seal:

- source and include SHA256;
- binary SHA256;
- compiler version and full flags;
- runtime-switch definitions;
- cohort/order;
- unit-test receipt;
- 12/12 semantic-parity receipt;
- runner/verifier/analyzer hashes.

Use fresh output directories. Do not reuse historical timing as an endpoint timing observation.

## Interpretation

### PASS

The confirmed cache-aware search rule can be implemented with lower runtime without changing the exact search tree. The bucket implementation becomes the preferred implementation candidate.

### FAIL

Retain the current single-sort implementation. The causal cache-aware ordering result remains unchanged.

### FAIL-SAFETY

Any exact-order or exact-search-work mismatch means B is not a pure implementation optimization; do not interpret timing and do not silently repair after looking at performance results. A revised implementation requires a new freeze.
