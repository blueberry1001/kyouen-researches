# Structural equivalence of loss-first-only and full cache-aware ordering

Base: `224f0dae89f95bfafa20290e872d96b9567dc6d7`

The confirmatory endpoint at `ec2d69f` found exact `visited` equality between
loss-first-only (L) and full cache-aware (F) on all 12 frozen parents. This
note strengthens that observation: under the current solver semantics, L and F
are structurally equivalent for `visited`, returned outcome, and recursive
unknown-child order. The 12/12 equality is therefore expected, not an
independent empirical effect of the cohort.

## Definitions

At a below-root nonterminal node, let B be the blind total order
`(legal_move_count, canonical_key)`.

- L sorts by B, finds the B-earliest child whose prefetched memo value is LOSS,
  and rotates that one child to index 0.
- F partitions children by cached class `LOSS < unknown < WIN` and sorts each
  class by the same B key.

Cached child outcomes are consumed directly from the prefetched value. Only an
unknown child is entered recursively. A cached LOSS makes the current node WIN
and returns immediately; a cached WIN merely continues the child loop.

## Theorem: L and F are visited-equivalent

Consider any visited nonterminal node.

### Case 1: at least one cached LOSS exists

L and F choose the same first child: the B-minimum cached LOSS. Its cached
outcome is consumed without recursion and the current node returns WIN
immediately. No second child is inspected. Therefore all remaining ordering is
irrelevant.

### Case 2: no cached LOSS exists

L is exactly B. F removes/interleaves cached-WIN children by moving every
unknown child ahead of them, while preserving B order inside the unknown
bucket.

This does not change recursive work. Under L, every cached-WIN child encountered
before the next unknown child is consumed without recursion and cannot cause a
return; it only continues the loop. Thus the sequence of recursively entered
unknown children under L is exactly the B-projection onto unknown children.
F visits exactly that same unknown projection, in exactly the same order.
Cached-WIN evaluations do not increment `visited` and do not create a recursive
memo update.

Inductively, both policies therefore enter the same recursive unknown states in
the same order, see the same memo evolution at each recursive boundary, and
return the same outcome with the same `visited` count.

So cached-WIN demotion cannot improve `visited` in this solver. The only
semantically active ordering operation in F is selecting the B-earliest cached
LOSS before any recursive unknown work; L implements exactly that operation.

## Existing instrumentation is consistent with the theorem

The frozen 12-parent memo-instrumentation run contains 193,606,274 visited
nonterminal nodes. It reports:

- `nodes_cache_changes_first_child = 41,677,154`;
- `actual_first_cached_loss = 80,710,588`;
- `fallback_first_cached_loss = 60,736,764`.

The first-child changes attributable to LOSS promotion are therefore
`80,710,588 - 60,736,764 = 19,973,824`. The remaining
`41,677,154 - 19,973,824 = 21,703,330` first-child changes (11.21% of all
visited nonterminal nodes) are consistent with the no-LOSS cached-WIN-demotion
case.

That residual class is not rare. Yet the preregistered endpoint still has
L == F exactly on all 12 parents. This is what the theorem predicts: moving a
zero-recursion cached WIN out of the way can change the literal first child
without changing the first recursively entered unknown child or `visited`.

The older `full-change = 65,256,722` versus `first-change = 41,677,154` gap is
also no longer a reason to expect a residual visited effect. Reordering later
cached children can be syntactically common while remaining observationally
irrelevant once recursive unknown order is unchanged.

## Consequence for follow-up work

Do not spend a new cohort measuring whether cached-WIN demotion explains the
L/F difference: for `visited`, there is no such mechanism under these solver
semantics. A small safety harness may still be useful to mechanically verify
the theorem over synthetic child-class patterns and guard future solver
changes, but it is not a research experiment.

The mechanistic research question moves one level earlier:

> Why does the memo contain a reusable cached LOSS at the right nodes, and what
> search-DAG convergence or parent-to-child reuse creates those LOSS hits?

The highest-value new instrumentation is therefore canonical parent→child reuse
(depth 7/8 or the already identified high-impact depths), recording distinct
parent counts and later reuse as cached LOSS/WIN. That targets the origin of
the active signal rather than an ordering component now eliminated
analytically.

This refinement does not alter any frozen endpoint or success criterion.
