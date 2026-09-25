# Cached-LOSS prefix provenance: nesting amendment

Branch: `preregister-cached-loss-prefix-provenance`
Base preregistration: `06ed46f9519525f7070b5d5105165b14613059a3`

This amendment is frozen before any cohort result is inspected.

## Problem found during implementation audit

`pre_cached_loss_prefix` regions can nest. An unknown child explored inside an
outer prefix can itself encounter a node with a cached LOSS behind unknown
children, creating an inner prefix event.

The original minimal strategy (`prefix_depth` plus a provenance bit/epoch) is
underspecified for this case. In particular, assigning a memo insertion to the
innermost prefix and counting a hit after the inner prefix exits would classify
a hit that still occurs inside the outer prefix as downstream reuse. That is
wrong for the causal question: loss-first at the outer node removes the entire
outer prefix, including both the inner event and any reuse that occurs before
the outer prefix exits.

## Frozen ownership rule

For provenance/reuse purposes, every memo entry first inserted while one or more
prefixes are active is owned by the **outermost active prefix event**.

A hit on that entry counts as `later` only after execution has exited that
outermost owning prefix. Therefore:

- insertion in outer prefix, hit in same outer prefix: not later reuse;
- insertion in nested inner prefix, hit after inner exit but before outer exit:
  not later reuse;
- insertion in nested inner prefix, hit after outer exit: later reuse;
- insertion with no active prefix: not prefix-origin.

This ownership rule applies to both entry hits and child-prefetch hits and to
WIN/LOSS splits.

For by-parent-depth summaries, attribute a prefix-origin insertion and its later
hits to the depth of its outermost owning prefix. Nested prefix events may still
be counted in `prefix_events`, but their memo insertions must not be double
counted in provenance denominators.

## Implementation consequence

A scalar `prefix_depth` is sufficient only for deciding whether execution is in
some prefix; it is not sufficient to determine ownership/exiting under nesting.
Maintain an active-prefix stack (or equivalent outermost-event token). Each new
prefix-origin memo slot stores the token of the outermost active event. Mark
that token exited only when its outer prefix ends. A stored slot becomes
eligible for later-hit counting only after its owner token has exited.

If retaining event tokens per memo slot is too invasive, an equivalent monotone
outer-prefix generation scheme is acceptable, but it must pass the nesting
regressions below.

## Added mandatory regressions

Before the 12-parent cohort is run, add synthetic tests for:

1. outer prefix -> inner prefix -> insertion -> inner exit -> hit -> outer exit:
   the hit is **not** later reuse;
2. outer prefix -> inner prefix -> insertion -> inner exit -> outer exit -> hit:
   the hit **is** later reuse exactly once;
3. a nested insertion contributes once to `prefix_new_memo_puts`, attributed to
   the outermost owner's parent depth;
4. nested prefix event counting does not change outcome, `visited`, memo
   replacement behavior, or the original B/L ordering.

## Interpretation

The scientific target is reuse that survives removal of the skipped outer
prefix. The outermost-ownership rule makes the measured numerator match that
target. Without it, nested search can inflate `later_reuse_per_prefix_put` and
can incorrectly push the preregistered 0.05 decision rule toward the expensive
DAG-analysis branch.
