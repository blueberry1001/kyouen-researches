# Depth-8 -> depth-9 LOSS-memo causal ablation

## Status

Preregistered mechanism follow-up. Do not run this before the generic cached-LOSS-prefix BPF implementation and its safety suite are working. This document fixes the intervention before looking at its result.

## Question

Existing depth-resolved comparisons localize the first cache-aware/blind behavioural divergence to child handling at depth 8, with visited-node divergence appearing one level later. The loss-first-only endpoint also matches the full cache-aware endpoint on the frozen confirmatory cohort. These observations motivate a narrower causal question:

> Is memoized LOSS state produced while solving depth-9 children of one depth-8 parent causally useful to later depth-8 parents?

A producer/consumer counter alone cannot answer this because observed later hits are trajectory-dependent. Use deletion/forgetting as the primary test.

## Frozen interventions

Run the existing blind-order baseline `B` and two paired variants, preserving all move ordering and all non-target memo behaviour.

### D9LF: depth-9 LOSS forget

Define a depth-8-parent ownership event when recursion enters a depth-8 state. Memo entries first created during evaluation of that parent's immediate depth-9 children are tagged with that depth-8 parent event and producer depth.

When that depth-8 parent returns, logically invalidate exactly the still-live tagged entries satisfying both:

- state depth is 9; and
- memo value is LOSS.

Do not invalidate pre-existing entries merely touched during the event. Do not invalidate depth-9 WIN entries or entries at any other depth. Retain all downstream consequences after invalidation.

### D9WF: depth-9 WIN forget control

Identical to D9LF except invalidate only depth-9 WIN entries. This is the value-label control.

Use the same tombstone/lazy-invalidation semantics and physical-vs-logical occupancy accounting already frozen for BPF. A slot's owner describes the insertion that created its current live occupant, not the most recent same-key update.

## Primary quantities

For each frozen parent report:

```
d9_loss_future_value = visited(D9LF) - visited(B)
d9_win_future_value  = visited(D9WF) - visited(B)
```

Also report paired relative effects, totals, medians, and sign counts over the frozen 12-parent cohort.

No pass/fail threshold is introduced. The qualitative mechanism prediction is `D9LF - B` positive and materially larger than `D9WF - B`; this is a prediction, not a criterion to relabel the experiment after seeing results.

## Attribution counters (secondary only)

For target entries record:

- number newly created;
- number surviving until producer-parent exit;
- later prefetch hits from a different depth-8 parent;
- later cached-LOSS immediate cutoffs for LOSS entries;
- distinct producer -> consumer depth-8 parent pairs.

These counters explain a causal effect if one exists; they are not substitutes for the paired forgetting endpoint.

## Safety checks

Before cohort execution require:

1. intervention disabled reproduces `B` exactly;
2. B and each variant have identical solver-visible traces through the first targeted producer-parent exit, permitting divergence only after the invalidation;
3. D9LF never changes the logical set of live depth-9 WIN entries at the intervention point, and D9WF never changes the logical set of live depth-9 LOSS entries;
4. neither variant invalidates any depth != 9 entry;
5. a depth-9 target entry that predates the current depth-8 parent survives a same-key update inside that parent;
6. a newly produced target entry is forgotten at producer-parent exit, while a newly produced non-target value at the same depth survives;
7. lazy invalidation matches an eager reference map on randomized small-table traces, including collision chains, wrap-around probing, full-table tombstone reuse, and same-key reinsertion;
8. logical occupancy drops by exactly the number of surviving target-owned entries invalidated at the boundary while physical occupancy retains its production meaning;
9. zero-target producer-parent exits are metamorphically inert: complete subsequent trace and endpoint must equal baseline until a non-empty intervention occurs.

## Interpretation

A large positive D9LF effect with a small D9WF effect would support the specific mechanism that cross-parent reuse of depth-9 LOSS results is a major source of the cache-aware advantage. Similar D9LF and D9WF effects would instead point to generic memo investment/reuse rather than LOSS-specific reuse. Near-zero effects for both would falsify this localization even if observational producer/consumer reuse counts are large.

Do not infer additivity with BPF or with the loss-first endpoint: each intervention can change the downstream search DAG.
