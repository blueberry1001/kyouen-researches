# Preregistration: 10x10 cache-aware no-hit fast path

Date: 2026-09-09
Branch: `preregister-10x10-cache-aware-nohit-fastpath`
Base: `d3b5e8ba02a6581787a444e463ff16766d1babfd`
Status: **FROZEN BEFORE ANY FAST-PATH TIMING RESULT EXISTS**

## Objective

The confirmed cache-aware below-root ordering remains unchanged:

`cached LOSS < unknown < cached WIN < legal_move_count asc < canonical key asc`.

The previous bucketization optimization preserved semantics but slowed the solver. Its frozen mechanism analysis found that 36.0% of cache-aware nonterminal nodes have no cached child at all, while 76.2% of children are unknown. This experiment tests a narrower implementation optimization: when every generated child has `cached == 0`, skip cached-class comparisons and sort directly by `(legal_move_count, canonical key)`. At any node with at least one cached child, use the historical single-sort comparator unchanged.

This is an implementation optimization only; it must preserve the exact child sequence and exact search tree.

## Implementations

- **S (baseline):** historical single `std::sort` comparator using `(cached_class, count, key)` at every cache-aware below-root node.
- **F (fast path):** while generating children, accumulate `any_cached |= (cv != 0)` from the already-required memo prefetch result `cv`. If `any_cached == false`, sort by `(count, key)` only. Otherwise run the exact historical S comparator.

No extra memo lookup is allowed.

Root depth 3 and cache-blind behavior are identical in S and F.

## Why the order is exactly equivalent

If `any_cached == false`, every child has cached class `unknown`, so the first component of the historical `(cached_class, count, key)` key is equal for all children. Therefore sorting by `(count, key)` produces exactly the same total order. If `any_cached == true`, F invokes the historical comparator unchanged.

## Forbidden changes

- cache-aware ordering semantics
- root ordering
- cache-blind ordering
- memo capacity / shrink / load
- memo lookup, prefetch, put, reuse, recursive omission, or cached-LOSS shortcut semantics
- duplicate elimination
- canonicalization
- game rules
- legal-move-count definition
- witness logic
- stopping rules
- instrumentation semantics
- compiler flags except unavoidable documented environment differences

## Order-equivalence gate

Before exact timing, deterministic synthetic tests must compare S and F final child key sequences, including:

- all unknown
- mixed cached classes
- n=0/1
- equal counts with key ties resolved
- reversed/adversarial inputs
- fixed-seed random fixtures

Any order mismatch => **FAIL-SAFETY**, no timing interpretation.

## Semantic parity hard gate

Use the frozen C1 12-parent cohort from `d9b9a0f`. Run S and F in fresh processes using one binary and a runtime switch.

Require exact equality for all 12 parents on:

- outcome
- exact visited
- exact memo
- maxdepth
- all depth_visited values
- root unique / entered / first / witness
- memo instrumentation counters
- memo used-by-depth/capacity diagnostics where available

Any mismatch => **FAIL-SAFETY**, no timing interpretation.

## Timing endpoint

Only after semantic parity PASS:

- 12 parents × 2 implementations × 3 repetitions = 72 fresh serial runs
- same binary, machine, compiler and flags
- deterministic counterbalanced implementation order frozen before timing
- no historical timing reuse
- primary per-parent value = median solver-reported seconds over 3 repetitions

For parent i:

`T_i = median_seconds_S / median_seconds_F`

F is faster iff `T_i > 1`.

Primary PASS requires both:

1. median parent `T_i > 1`
2. F faster on at least 7 of 12 parents

No effect-size threshold is added.

## Secondary outputs

After primary only:

- parent T values
- geometric/arithmetic mean
- aggregate solver/wall ratio
- faster/tie/slower
- exact paired sign test
- absolute seconds saved
- fraction of nodes taking the no-hit fast path
- if instrumentable without contaminating primary timing: comparisons or ns/node by no-hit fraction

## Interpretation

- parity PASS + timing PASS: exact same search tree with lower runtime from the no-hit comparator fast path.
- parity PASS + timing FAIL: retain historical single-sort; negative optimization result.
- parity FAIL: FAIL-SAFETY; no timing claim.

Negative results must be committed and pushed. `main` must remain untouched.