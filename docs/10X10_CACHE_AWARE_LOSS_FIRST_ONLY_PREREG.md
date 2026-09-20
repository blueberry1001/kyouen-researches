# Preregistration: 10x10 cache-aware loss-first-only ablation

Date: 2026-09-20
Branch: `preregister-10x10-loss-first-only`
Base: `599e57b32cf577a6ba283a9e0579bbbfe1932c7a`
Status: **FROZEN BEFORE ANY LOSS-FIRST-ONLY ENDPOINT RESULT EXISTS**

## Question

Confirmed full cache-aware below-root ordering is:

`cached LOSS < unknown < cached WIN < legal_move_count asc < canonical key asc`.

The causal mechanism is still compressed poorly: does almost all of the search-tree benefit come from putting one already-known LOSS child first, or do cached-WIN demotion and full cached-class sorting materially contribute?

## Implementations

Use one binary with a runtime switch and otherwise identical solver semantics.

- **B (blind):** historical cache-blind below-root ordering `(legal_move_count, canonical key)`; memo semantics remain enabled exactly as in the existing blind comparison.
- **L (loss-first-only):** begin from exactly B order. If one or more children have a prefetched cached LOSS, select the cached-LOSS child that is earliest under B order and move only that single child to position 0. Preserve the relative order of every other child exactly. Cached WIN receives no ordering penalty.
- **F (full-aware):** confirmed historical ordering `cached LOSS < unknown < cached WIN < legal_move_count < canonical key`.

No extra memo lookup is allowed. L must reuse the same already-required child memo prefetch value used by F.

Root ordering, memo capacity, memo lookup/put/reuse semantics, canonicalization, duplicate elimination, game rules, stopping rules, legal-move-count definition, compiler flags, and all non-ordering logic are frozen.

## Safety gates

Before endpoint runs, deterministic order tests must verify L exactly:

1. no cached LOSS => byte-for-byte B child sequence;
2. one cached LOSS => only that child is moved to index 0;
3. multiple cached LOSS => B-earliest cached LOSS moves to index 0; all remaining children retain B relative order;
4. n=0/1, equal legal counts, key tie resolution, reversed/adversarial inputs, and fixed-seed random fixtures.

For all three implementations, outcome must agree on every endpoint parent. Any outcome mismatch is **FAIL-SAFETY** and invalidates performance interpretation.

## Cohort and run discipline

Reuse the already frozen C1 original 12-parent cohort used by the cache-aware below-root and no-hit experiments. Do not resample parents and do not inspect L results before the complete cohort is collected.

Run fresh processes, serially, from empty process state. Counterbalance implementation order deterministically before execution. The primary endpoint is exact `visited`, not wall time; timing is secondary because L and F intentionally produce different search trees.

## Primary estimand: recovery of full-aware search reduction

For each parent i, let `V_B`, `V_L`, `V_F` be exact visited counts.

Define aggregate recovery over the whole frozen cohort:

`Recovery = (sum(V_B) - sum(V_L)) / (sum(V_B) - sum(V_F))`.

Interpret only when the denominator is positive, as already established by the prior frozen B-vs-F experiment.

Primary success criterion:

- `Recovery >= 0.80`, and
- L improves over B (`V_L < V_B`) on at least 10 of 12 parents.

This 80% threshold is fixed before any L endpoint result is observed. It means the minimal one-child promotion recovers at least four-fifths of the previously observed full-aware aggregate search reduction.

## Secondary estimands

Report all, regardless of primary result:

- per-parent `V_L / V_B`, `V_L / V_F`, and per-parent recovery where defined;
- median and geometric mean ratios;
- count of parents where L equals F exactly in visited;
- fraction of nonterminal nodes with >=1 cached LOSS;
- among L-vs-F divergent nodes, whether divergence is caused by multiple cached LOSS ordering or cached-WIN demotion;
- solver seconds and wall seconds, clearly secondary;
- exact outcome parity.

No post-hoc parent exclusion is allowed.

## Mechanistic interpretation

- **Recovery >= 0.80:** most of the confirmed cache-aware benefit can be compressed to one B-earliest cached-LOSS promotion. Optimize this narrow mechanism next; full cached-class sorting is not necessary for most of the search reduction.
- **Recovery < 0.80:** second-order ordering information matters. Instrument L-vs-F first-divergence nodes before proposing another heuristic.
- **L worse than B on aggregate:** reject the compression despite any isolated wins.

A useful structural expectation, not a success criterion: at a WIN node with a sound cached LOSS, moving any cached LOSS to the front should allow immediate resolution; therefore remaining L-vs-F differences should concentrate in nodes without cached LOSS, especially where cached-WIN demotion changes memo evolution.

## Interaction with no-hit fast path

Do not combine this ablation with the pending no-hit timing endpoint. First estimate L's search-tree recovery in isolation. The no-hit fast path preserves F's order and addresses implementation cost; L changes ordering semantics and addresses mechanism compression. They are separate questions.

Negative results must be retained. `main` must remain untouched.
