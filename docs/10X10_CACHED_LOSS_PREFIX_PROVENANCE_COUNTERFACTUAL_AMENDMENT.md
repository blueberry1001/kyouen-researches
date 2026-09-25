# Cached-LOSS prefix provenance: counterfactual-survival amendment

Branch: `preregister-cached-loss-prefix-provenance`
Previous executable reference model: `e2a09449225dd299fc3e404fd15179c2657ee925`

This amendment is frozen before the 12-parent cohort is inspected.

## Problem

The current owner-event predicate correctly answers a temporal question:

`origin_outer_event != 0 && origin_outer_event <= last_exited_outer_event`

means that a memo entry is hit after the outermost prefix that created it has exited.

That is not identical to the stronger counterfactual question needed for causal interpretation: would that hit still occur if cached-LOSS-first ordering removed all removable prefixes?

A concrete case is already present in the reference regression. Entry A is created in outer event A, A exits, outer event B starts, and A is hit while B is active. The current model deliberately counts this as later reuse. Temporally this is correct. But if B itself is a cached-LOSS-before prefix that disappears under the loss-first intervention, that hit occurs inside work which would also disappear. Counting it as preserved memo value can therefore overstate the opportunity cost of deleting A's prefix.

This is a second-order effect: an old prefix-generated memo can be reused inside a later removable prefix.

## Frozen measurement refinement

Do not change or discard the original preregistered `later reuse` metric or its 0.05 threshold. Add a strictly more conservative secondary metric:

- `later_reuse_any`: the existing owner-event predicate;
- `later_reuse_outside_prefix`: the existing predicate **and current prefix depth == 0**.

Record both separately for entry hits and child-prefetch hits, with the same denominator of first insertions attributed to cached-LOSS-before outer prefixes.

Thus for every run:

`later_reuse_outside_prefix <= later_reuse_any`.

The difference

`later_reuse_inside_later_prefix = later_reuse_any - later_reuse_outside_prefix`

measures reuse that is temporally later than the origin prefix but occurs inside another currently removable prefix.

## Interpretation

The original metric remains the preregistered decision metric. The new metric is diagnostic and must not retroactively change the 0.05 gate.

- If `later_reuse_any` is already small, the original conclusion is robust.
- If `later_reuse_any` is material but `later_reuse_outside_prefix` is small, much of the apparent memo investment value is second-order reuse inside other removable work; a full DAG experiment becomes less urgent than the original metric alone would suggest.
- If both are material, prefix-generated memo has clear reuse outside currently removable prefixes and a stronger counterfactual/DAG experiment is justified.

`later_reuse_outside_prefix` is still not an exact intervention estimate: loss-first ordering can alter which later prefixes exist and when entries are generated. It is a conservative structural diagnostic, not a substitute for actually running the alternative ordering.

## Mandatory regression additions

Extend the independent owner-model test before solver integration:

1. A insertion -> A exit -> no active prefix -> hit A: `any=true`, `outside=true`.
2. A insertion -> A exit -> B active -> hit A: `any=true`, `outside=false`.
3. B nested prefix exits while B outer remains active -> hit old A: still `outside=false`.
4. B exit -> hit A: `any=true`, `outside=true`.
5. For every randomized step and slot, assert `outside => any`.

No cohort membership, ordering rule, outcome metric, or original threshold is changed by this amendment.
