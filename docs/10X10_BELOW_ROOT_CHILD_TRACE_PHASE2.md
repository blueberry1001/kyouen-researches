# 10x10 below-root phase 2: depth-5 child trace preregistration

## Motivation

Phase 1 found that, for the three completed fixed parents, 28.29%, 43.81%, and 48.05% of the measured depth-5 recursive work entered children that eventually returned WIN before the cutoff LOSS child was reached. This is diagnostic only: rejected-WIN work can warm the memo table, so it is not a causal speedup bound.

A code audit gives a stronger simplification at depth 5. `MultiDepthMemo100::get` returns 0 outside depths 9--17. Therefore the depth-5 parent sees every depth-6 child as uncached. The current comparator at depth 5 is consequently exactly:

1. smaller `child.count = popcount(child_legal)` first;
2. canonical child key as the tie-breaker.

Thus the phase-1 depth-5 waste is not evidence against a memo-derived ranking. It is direct evidence that the existing **minimum-next-legal-moves** heuristic sometimes explores expensive WIN children before the needed LOSS child.

## What phase 2 may and may not infer

A baseline solve only reveals outcomes for recursively entered children up to the first LOSS child of a WIN node. Children after that cutoff are censored: their final outcomes are unknown.

Therefore a child trace must **not** be used to claim a global `first LOSS rank`, or to estimate how often a proposed rule would promote some unvisited suffix child. Doing so would introduce selection/censoring bias.

The valid diagnostic question is narrower:

> Among the children that the baseline actually had to recurse into at a depth-5 WIN node, can a feature available before recursion rank the eventual cutoff LOSS child ahead of the rejected WIN children?

This is an observed-prefix pairwise-repair test. It is useful for choosing a candidate heuristic, but it is not the performance result.

## Minimal trace

Only expanded nodes at `depth == 5` need to be traced initially. For every *unknown* child actually recursed into, record:

- root input state identifier;
- monotonically assigned depth-5 node identifier;
- canonical parent bits (`lo`, `hi`);
- child order index under the frozen baseline comparator;
- raw/canonical move identifier if available, otherwise canonical child bits;
- `child.count` (legal moves after the child), computed before recursion;
- canonical child bits (`lo`, `hi`), computed before recursion;
- returned outcome, written only after recursion;
- `visited_delta = st.visited_after - st.visited_before`, written only after recursion;
- whether this child caused the WIN-node cutoff.

Pre-recursion columns and post-recursion labels must remain visibly separate. A ranking rule may use only the former.

Cached children are absent at depth 6 by construction under the current memo policy. If that policy changes, the trace format must record the pre-recursion cache class explicitly and phase 2 must be re-preregistered.

## Invariants

For each completed traced depth-5 WIN node:

- child order indices are strictly increasing;
- every non-cutoff recursively entered child returns WIN;
- exactly one recursively entered child returns LOSS and it is the final row for that node;
- the LOSS row has `cutoff = 1`;
- no recursively entered row follows the cutoff;
- every `visited_delta >= 1` because these children are uncached at depth 6 under the current memo policy.

The trace is incomplete for depth-5 LOSS nodes by design: they have no cutoff and all children must return WIN. Such nodes were absent in the three phase-1 completed parents, but the checker must not silently reinterpret them as WIN nodes.

## Candidate scoring and split discipline

The first candidate family should be deliberately cheap and computed offline from the pre-recursion columns / board geometry. Do not reuse `memo_used`, probe-final `visited`, returned outcome, `visited_delta`, or any descendant statistic as an input feature.

Development and validation must split at the **root-parent level**, not at child or depth-5-node level, because nodes from the same root share substantial search history and geometry. The fixed parent used for final validation must not influence score selection, feature choice, tie-breaking, or thresholds.

The baseline comparator itself (`child.count`, then canonical key) is the mandatory control. A proposed score is interesting only if it improves pairwise ordering of the cutoff LOSS child versus rejected WIN children on held-out roots without using post-recursion information.

## Definitive experiment

Even a perfect observed-prefix score is not a speedup claim. After freezing one rule, compare:

- baseline solver;
- solver differing only in the depth-5 child comparator.

Run each parent in a separate fresh process with identical memo parameters and empty initial memo state. Require identical root outcome. Primary endpoint is total root `visited`; wall-clock time is secondary. This full rerun automatically includes both the saved rejected-WIN work and any lost memo warming caused by changing the order.

The rule is useful only if fresh-process total `visited` decreases on held-out roots. Phase-1 `work_into_win_child` must never be subtracted from baseline `visited` to predict that decrease.
