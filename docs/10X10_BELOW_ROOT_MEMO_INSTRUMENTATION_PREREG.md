# 10x10 below-root memo instrumentation preregistration

Branch: `preregister-10x10-below-root-memo-instrumentation`
Base: `70befc94e43112bd7853d4c809fa5b8579eabdea`

This document freezes the first below-root mechanism measurement **before any
instrumented parent result is inspected**.  It is diagnostic only: no new root
ordering rule is proposed here, and no 100k/1M probe cohort is authorized by
this preregistration.

## Motivation

The completed V2 parent benchmark and conditional-LOSS analysis established:

- 10k memo-ascending is a useful LOSS classifier but a poor root proof-cost
  ordering;
- native `(legal_move_count, canonical key)` is already close to the cheapest
  LOSS available at the root (median about 1.12x oracle);
- the 12-parent benchmark is explained by the entered root prefix to within
  about 2%, so cross-root-child memo pollution is not the primary failure mode;
- root-only heuristic headroom is therefore small.

The next question is not another root heuristic.  It is:

> Where, and by what mechanism, does the solver's shared memo actually save
> exact work below the root?

The current recursive solver performs two logically different memo lookups:

1. **node-entry lookup**: when `win(state, ...)` starts, return immediately if
   that state has already been solved;
2. **child-prefetch lookup**: while constructing a node's unique children, read
   each child's cached outcome and use it both for ordering and possibly to
   avoid a recursive call.

It then stores a WIN or LOSS result with a **memo put**.  These events must be
measured separately.  A single aggregate `memo_used` number cannot distinguish
reuse from new storage and cannot say whether a hit changed search order.

## Frozen cohort

The first instrumented cohort is the same 12 frozen clean V2 3-stone parents
used by the completed native parent benchmark.  No parent may be added, removed,
or replaced after instrumented outputs are seen.

Root ordering remains the existing native ordering.  No 10k probe ordering is
used in the primary instrumentation run.

The instrumented build must use the same game predicate, canonicalization,
child deduplication, memo implementation/settings, and recursive ordering as the
native benchmark solver.  Instrumentation must not alter any branch decision.

## Required semantic parity before mechanism interpretation

For every instrumented parent run, compare against the existing uninstrumented
native benchmark record.

Required exact invariants:

- outcome identical;
- root unique-child count identical;
- root entered-child count identical;
- root first-child canonical key identical;
- root witness identical where recorded;
- exact `visited` identical;
- exact final `memo_used` identical.

If any invariant fails, the instrumented result is invalid for mechanism
analysis.  Wall-clock and solver seconds are explicitly *not* parity criteria,
because counters add overhead.

## Counters to add

All counters are integer-only and aggregated by search depth.  Do not log a
per-state trace in the primary run.

### A. Node-entry memo lookup

For each depth:

- `entry_lookup_calls`
- `entry_hit_win`
- `entry_hit_loss`
- `entry_miss`

A hit here means an attempted recursive node evaluation was avoided immediately.

### B. Child-prefetch lookup

For each child depth:

- `prefetch_calls`
- `prefetch_hit_win`
- `prefetch_hit_loss`
- `prefetch_miss`

These are counted after canonical child deduplication, exactly where the native
solver currently reads the child memo value used by ordering.

### C. Memo writes

For each solved-state depth:

- `put_win`
- `put_loss`

These counters measure newly completed work, not reuse.  They must be kept
separate from lookup hits.

### D. Recursive child evaluations avoided

For each parent-node depth:

- `child_eval_from_cache_win`
- `child_eval_from_cache_loss`
- `child_eval_recursive`

A child counts as `from_cache_*` only when the evaluation loop consumes the
prefetched cached outcome instead of calling `win(child, ...)`.

### E. Ordering influence

At each visited nonterminal node, compute the order that would result from the
cache-blind fallback `(legal_move_count, canonical key)` **without changing the
actual evaluation order**.

Count by node depth:

- `nodes_with_any_prefetch_hit`
- `nodes_cache_changes_first_child`
- `nodes_cache_changes_full_order`
- `actual_first_cached_loss`
- `fallback_first_cached_loss`

`nodes_cache_changes_full_order` means the sequence of canonical child keys under
native cache-aware ordering differs anywhere from the cache-blind fallback.

This is a diagnostic counterfactual only.  It must not be used to reorder the
run being measured.

### F. Immediate WIN short-circuit from cached LOSS

Count by node depth:

- `win_return_from_cached_loss_child`

This is the strongest direct form of below-root memo benefit: the current node
is proved WIN because its selected child is already cached LOSS, with no
recursive call for that child.

## Derived metrics frozen in advance

Compute both overall and by depth:

1. entry hit rate
   `entry_hits / entry_lookup_calls`;
2. prefetch hit rate
   `prefetch_hits / prefetch_calls`;
3. cached child-evaluation fraction
   `(child_eval_from_cache_win + child_eval_from_cache_loss) /
    total child evaluations consumed`;
4. cache-order first-child change rate
   `nodes_cache_changes_first_child / visited_nonterminal_nodes`;
5. cache-order any-change rate
   `nodes_cache_changes_full_order / visited_nonterminal_nodes`;
6. cached-LOSS WIN-short-circuit rate
   `win_return_from_cached_loss_child / solved_WIN_nodes`;
7. write/reuse ratio
   `(put_win + put_loss) / (entry_hits + prefetch_hits)`.

No single arbitrary threshold defines success.  This is a mechanism study, not
a treatment benchmark.  Interpret effect sizes and depth concentration.

## Predeclared interpretation cases

### M1: reuse is large and concentrated below root

Evidence:

- substantial entry/prefetch hit rates;
- many child evaluations avoided;
- or many WIN returns directly from cached LOSS children.

Next priority: exploit memo layout / lookup / persistence / cross-branch reuse,
not root ordering.

### M2: hits are common but mostly do not alter work

Evidence:

- high prefetch hit rate;
- low cached-evaluation fraction and low ordering-change rate.

Next priority: distinguish informational memo hits from actionable hits; avoid
optimizing raw hit rate.

### M3: cache-aware ordering changes many nodes

Evidence:

- meaningful `nodes_cache_changes_first_child` or full-order rate.

Next experiment may compare cache-aware vs cache-blind ordering below root, but
that treatment must be separately preregistered before running it.

### M4: reuse is weak

Evidence:

- low entry/prefetch hit rates and few avoided evaluations at all depths.

Then memo optimization is unlikely to be the main remaining lever.  Shift to
proof/certificate structure, stronger lower-level ordering, or representation
cost.

## What this preregistration does NOT permit

Do not, on the basis of these counters alone:

- change root ordering;
- run another 10k/100k/1M probe-all cohort;
- disable memo and call the resulting slowdown a causal estimate;
- introduce per-state tracing into the primary 12-parent measurement;
- tune instrumentation definitions after seeing results.

A memo-disabled or cache-blind solver is a separate causal treatment and needs a
new frozen experiment because it can radically change traversal and memory
pressure.

## Implementation rule

Instrumentation should live in a dedicated solver variant or be guarded by a
compile-time flag defaulting OFF.  The ordinary solver's behavior must remain
unchanged.  Counter reporting goes to a separate machine-readable CSV/JSON
section/file, not mixed into existing primary CSV columns in a way that breaks
old parsers.

The first code commit after this document may implement the counters, but no
instrumented 12-parent outcomes should be committed before this preregistration
commit exists on the branch.
