# 10x10 cache-aware vs cache-blind below-root ordering benchmark — preregistration

Branch: `preregister-10x10-cache-aware-vs-blind-below-root`
Base: `80b734b265a698370c33631bc8c9771c8fc645e2`

This document freezes the causal follow-up to the completed below-root memo
instrumentation study before any cache-blind parent result is run or inspected.

## Motivation and already-observed evidence

The preceding instrumentation experiment on the frozen 12 clean-V2 parents
passed semantic parity 12/12 and found, overall:

- child-prefetch memo hit rate: about 23.79%;
- cached child-evaluation omission rate: about 34.94%;
- cache-aware ordering changed the first child at about 21.53% of visited
  nonterminal nodes and changed the full child order at about 33.71%;
- about 52.73% of solved WIN nodes returned immediately from a cached LOSS
  child;
- the actual cache-aware first child was cached LOSS at about 41.69% of
  nonterminal nodes, versus about 31.37% for the diagnostic cache-blind
  fallback order.

The preregistered mechanism cases therefore triggered M1 and M3.  M3 explicitly
called for a separately preregistered cache-aware versus cache-blind ordering
comparison below the root.

The causal question is:

> Holding the memo table, lookups, writes, cached-result reuse, root ordering,
> game logic, canonicalization, and all other solver behavior fixed, does using
> prefetched cached outcomes to *order* children below the root reduce exact
> search work?

This is **not** a new blind/generalization cohort.  The same 12 parents have
already been examined extensively.  The purpose of this experiment is a paired
mechanism intervention on those fixed states.  If the treatment effect is
promising, a later experiment on a new frozen cohort is required before making
a generalization claim.

## Frozen cohort

Use exactly the 12 clean-V2 3-stone parents used by the native parent benchmark
and memo-instrumentation run:

- `0,11,35`
- `11,38,44`
- `11,78,87`
- `12,24,68`
- `12,32,55`
- `13,52,57`
- `14,64,74`
- `23,44,45`
- `3,47,63`
- `3,53,84`
- `4,24,26`
- `4,42,54`

No parent may be added, removed, replaced, or excluded after cache-blind results
are seen.  Complete all 12 unless a correctness failure invalidates the run.

## Conditions

Use one solver source and preferably one binary with a runtime switch so that
A and B differ only in the below-root child comparator.

### A — native cache-aware ordering

This is the current native behavior.

At every node, after canonical child deduplication and child memo prefetch,
children are ordered by:

1. cached LOSS;
2. uncached/unknown;
3. cached WIN;
4. legal move count ascending;
5. canonical child key ascending.

The root (the 3-stone parent node, depth 3) remains native.

### B — cache-blind ordering below the root

At the root node (depth 3), use **exactly the same native cache-aware ordering
as A**.

At every visited nonterminal node with node depth >= 4, sort children only by:

1. legal move count ascending;
2. canonical child key ascending.

Crucially, B does **not** disable memoization and does **not** discard the
prefetched cached outcome.  For every child it must still:

- perform the same memo prefetch lookup as A;
- retain whether that child is cached WIN, cached LOSS, or unknown;
- when that child is reached in the evaluation loop, consume a cached outcome
  without recursive evaluation exactly as A does;
- perform the same memo writes after solving states.

Thus the intervention removes cached outcome only from the **ordering key**.
It does not remove transposition reuse, cached evaluation omission, or cached
LOSS short-circuiting when the relevant child is eventually reached.

Differences in the memo table that arise later because A and B visit states in
different orders are part of the causal effect of the ordering intervention and
must not be artificially synchronized.

## What must remain identical

Between A and B, keep fixed:

- forbidden-set/game predicate;
- canonicalization and D4 handling;
- root child set and canonical deduplication;
- memo implementation, table sizes, shrink/load settings;
- memo lookup and put semantics;
- legal-move-count calculation;
- terminal handling;
- root ordering;
- compilation flags;
- initial empty/fresh memo state per parent;
- no 10k/100k/1M external probe ordering;
- no certificate/witness reuse from previous parent processes unless the native
  benchmark already requires it; default is fresh independent parent process.

No heuristic discovered after looking at B results may be inserted into this
experiment.

## Implementation guard

Prefer a switch such as:

`--below-root-order cache-aware|cache-blind`

with `cache-aware` as the default/native behavior.

The comparator branch should be as narrow as possible.  In cache-blind mode,
`Child.cached` must still be populated and later consumed; only its priority in
the sort comparator is ignored at node depth >= 4.

Instrumentation counters may remain compiled in if they are runtime-disabled by
default.  The primary benchmark should use the same instrumentation setting in
A and B, preferably OFF, because primary work is exact visited nodes rather than
counter values.

## Required pre-result regression

Before running the 12-parent B cohort:

1. Build the benchmark binary and freeze source/binary digests.
2. Run A (`cache-aware`) on at least the three previously used regression
   states and verify exact equality to the frozen native/reference solver for:
   - outcome;
   - visited;
   - final memo used;
   - max depth;
   - root unique child count;
   - root entered child count;
   - root first canonical child;
   - root witness where available.
3. Verify on a small deterministic test that A and B enumerate exactly the same
   unique child set at every checked node; only order may differ.
4. Verify that cache-blind mode still consumes cached WIN/LOSS children without
   recursion when such cached entries are encountered.
5. Freeze a protocol manifest before the first full B result is inspected.

If A fails native parity, stop and repair before collecting B data.

## Execution

For each of the 12 parents run both A and B from a fresh solver/memo state.

Primary correctness requirement:

- A outcome == B outcome for 12/12;
- both agree with the existing exact parent outcome.

Run all 12 regardless of early effect direction.  Do not stop for apparent
success or failure.

Wall-clock measurements should avoid simultaneous A/B runs for the same parent.
If timing is recorded, counterbalance A/B execution order across parents or run
under comparable machine load.  Timing is secondary; exact visited work is the
primary endpoint.

## Primary endpoint

For each parent define:

`R_i = visited_cache_blind / visited_cache_aware`.

A value > 1 means native cache-aware ordering saves search work relative to
cache-blind ordering.

Report:

- all 12 `R_i` values;
- median ratio;
- geometric mean ratio;
- arithmetic mean ratio;
- aggregate visited ratio;
- number of parents with R > 1, R = 1, R < 1.

The preregistered directional criterion for a practically consistent M3 effect
is:

- median `R_i > 1`, **and**
- cache-aware improves at least 7 of 12 parents (`R_i > 1`).

If both hold, interpret the fixed-cohort causal result as support that
cache-aware below-root ordering contributes useful search reduction.  This does
not by itself establish out-of-cohort generalization.

If either fails, do not claim that the observed diagnostic ordering-change
rates translate into a consistent search-work benefit.

Also report the exact paired sign-test p-value as a secondary descriptive
statistic; the experiment is not powered around a fixed significance threshold.

## Secondary endpoints

Report for A and B:

- exact solver seconds and wall-clock ratio;
- final memo used;
- maximum depth;
- root unique and entered children;
- root first child and witness;
- if instrumentation is collected secondarily, prefetch hit rate, cached child
  omission fraction, cached-LOSS shortcut fraction, and depth profiles.

If B changes root child set, root native ordering, outcome, or any game-semantic
quantity, treat that run as invalid rather than interpreting its speed.

## Mechanism decomposition

If the primary result supports A, use existing or newly collected counters only
for decomposition, not for redefining the endpoint.

Predeclared questions:

1. Does the benefit concentrate at depths 11–14, where the preceding study saw
   most reuse volume?
2. Is loss of cached-LOSS-first behavior the main driver of extra B work?
3. Does B retain similar raw prefetch hit availability but convert fewer hits
   into immediate WIN shortcuts?
4. Does ordering alter later memo population enough to amplify the direct
   comparator effect?

Any additional depth threshold or new heuristic suggested by these results is
exploratory and requires separate validation.

## Interpretation cases

### C1 — cache-aware ordering clearly helps

Median B/A > 1 and >=7/12 parents favor A.

Conclusion: M3 has causal work value on the fixed cohort.  Next priority is a
new-cohort confirmation and then investigation of cheaper ways to expose or
preserve cached-LOSS-first ordering.

### C2 — effect is weak/inconsistent

Median near 1 or fewer than 7/12 favor A.

Conclusion: M1 reuse/omission is the important mechanism, while reordering is
secondary.  Prioritize memo representation, lookup cost, persistence/reuse, or
proof/certificate reuse rather than comparator tuning.

### C3 — cache-blind is better

Median B/A < 1 with a majority favoring B.

Conclusion: the diagnostic first/full-order change rates were not evidence of
beneficial ordering.  Investigate why cached-result priority can be harmful;
do not optimize for more cache-aware reordering without a new hypothesis.

## Explicitly prohibited before primary completion

Do not:

- alter root ordering;
- disable memo lookup or memo writes in B;
- clear memo between children within a parent;
- add external 10k/100k/1M probe scores;
- tune depth cutoffs after seeing B results;
- test only the previously easiest or hardest parents;
- replace the cohort;
- run a new heuristic treatment and mix it into this result.

## Required artifacts

Commit, in causal order:

1. implementation and regression tests;
2. frozen protocol manifest and binary/source digests;
3. complete raw A/B outputs for 12/12;
4. verifier output;
5. analysis CSV/JSON and final Markdown report.

Keep `main` untouched.  Push the experiment branch.

## Final report checklist

Report:

1. branch, start SHA, end SHA, commits;
2. implementation delta and exact comparator definition;
3. regression/native parity result;
4. 12/12 completion, failures/timeouts;
5. A/B outcome agreement;
6. per-parent B/A visited ratios;
7. median/geometric/arithmetic/aggregate ratios;
8. improved/tie/worse counts;
9. sign-test p-value;
10. seconds/wall-clock ratios;
11. whether root behavior stayed identical;
12. whether the preregistered M3 criterion passed;
13. mechanism/depth decomposition if available;
14. unresolved risks;
15. whether a new-cohort confirmation is justified;
16. pushed SHA and confirmation that `main` is untouched.
