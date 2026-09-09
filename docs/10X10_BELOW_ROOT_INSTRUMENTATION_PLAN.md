# 10x10 below-root instrumentation plan

## Motivation

Existing V2 analysis shows that root ordering is no longer the main target:

- native root order selects a LOSS at median 1.12x the cheapest-LOSS oracle;
- 10k memo ordering loses because memo predicts LOSS much better than it predicts
  LOSS proof cost;
- entered-prefix independent-exact proxy reproduces parent exact-only ratios to
  about 2%, so root-order behavior itself is already well explained.

The next question is therefore not "which root child first?" but:

> Where, by depth and node type, does the native exact solver spend work, and
> how much of that work is avoided by memo hits / cached-child ordering / early
> discovery of a LOSS child?

This document freezes the first instrumentation design before looking at any
new instrumented parent results.

## P0. Non-negotiable invariants

Instrumentation must not change search semantics.

For every regression state, instrumented and uninstrumented builds must agree
on:

1. WIN/LOSS outcome;
2. `visited` exactly;
3. `maxdepth` exactly;
4. final memo used exactly;
5. root diagnostics (`unique`, `entered`, first key, witness) when enabled.

Wall time is diagnostic only. Counter overhead is expected, so speed comparisons
must use the uninstrumented solver unless a paired overhead check is explicitly
being performed.

## P1. Separate memo access sites

The current solver calls `memo_.get` at two logically different places:

- **node-entry lookup**: the canonical state at entry to `win`;
- **child-prefetch lookup**: each unique child while constructing/sorting the
  child array.

These must be counted separately; otherwise one state can contribute both a
prefetch lookup and a later recursive entry lookup and the hit rate is hard to
interpret.

For each depth `d`, collect:

- `entry_get[d]`
- `entry_hit_loss[d]`
- `entry_hit_win[d]`
- `child_get[d]` (children generated from parent depth d)
- `child_hit_loss[d]`
- `child_hit_win[d]`
- `put_loss[d]`
- `put_win[d]`

`entry_get = entry_miss + entry_hit_loss + entry_hit_win` and similarly for
`child_get` are required consistency checks.

## P2. Expansion and ordering counters

For every actually expanded node (entry memo miss), collect by depth:

- `expanded[d]`
- `terminal[d]` (`legal` empty)
- `unique_children[d]` total
- `cached_loss_children[d]`
- `cached_win_children[d]`
- `unknown_children[d]`
- `children_entered[d]`: number of sorted children whose outcome must be
  consumed before the node returns
- `cutoff_index_sum[d]` for WIN nodes, 1-based index of first LOSS child
- `win_nodes[d]`
- `loss_nodes[d]`

For a WIN node, `children_entered` is the first LOSS position in the sorted
order. For a LOSS node it is all unique children. A cached child counts as
entered when its cached outcome is consumed.

This directly measures whether native ordering remains near-oracle below root
or whether the 1.12x root headroom hides much larger deeper-layer waste.

## P3. Visited-work attribution

For each entered **uncached** child, snapshot `st.visited` immediately before
and after the recursive call and attribute the delta to the parent depth.
Collect separately:

- `work_into_win_child[d]`
- `work_into_loss_child[d]`
- `calls_into_win_child[d]`
- `calls_into_loss_child[d]`

The outcome is known after the call returns, so no semantic change is needed.

Interpretation:

- large `work_into_win_child` means failed candidate exploration dominates;
- large `work_into_loss_child` means proving the eventual witness LOSS dominates;
- depth localization tells us where a deeper ordering experiment could have
  positive expected value.

These counters intentionally use the solver's existing `visited` metric rather
than wall time.

## P4. Derived quantities (computed after the run)

Do not add extra solver decisions for these; derive them from counters.

Per depth:

1. entry memo hit rate;
2. child-prefetch hit rate;
3. cached LOSS fraction among generated children;
4. average entered children per WIN node;
5. average entered children per LOSS node;
6. mean WIN cutoff index;
7. fraction of recursive visited spent inside ultimately-WIN children;
8. fraction spent inside ultimately-LOSS children;
9. `put / expanded` sanity ratio;
10. cumulative work by depth.

Primary mechanistic endpoint:

> fraction of total recursive visited attributable to failed WIN children,
> stratified by parent depth.

Secondary endpoint:

> mean first-LOSS cutoff index on expanded WIN nodes, stratified by depth.

## P5. First cohort

Use existing V2 parent states only; no new cohort selection based on instrumented
results.

Initial four-state diagnostic cohort is frozen as:

- `12,32,55` — worst 10k parent benchmark case;
- `14,64,74` — large pure LOSS-selection failure;
- `0,11,35` — case where WIN-prefix waste dominated at root;
- `13,52,57` — only clean single-entry case where 10k selection beat native.

This cohort spans the already-known root mechanisms and is for mechanism
localization, not confirmatory performance claims.

If invariants pass and counters are nontrivial, run the same instrumentation on
all 12 V2 parents. Do not change the counter set after viewing the four-state
results; additions require an amendment and a fresh output file.

## P6. Output format

Emit one machine-readable CSV row per depth and parent, plus one TOTAL row.
Suggested columns:

```text
state,depth,visited,expanded,terminal,
entry_get,entry_hit_loss,entry_hit_win,
child_get,child_hit_loss,child_hit_win,
put_loss,put_win,unique_children,
cached_loss_children,cached_win_children,unknown_children,
children_entered,win_nodes,loss_nodes,cutoff_index_sum,
work_into_win_child,work_into_loss_child,
calls_into_win_child,calls_into_loss_child
```

Keep raw rows immutable. Derived summaries belong in a separate analysis file.

## P7. Implementation locations

The current `win` routine provides all required hooks without changing
algorithmic decisions:

1. immediately around `memo_.get(key, depth)` — node-entry counters;
2. around `memo_.get(nk, depth+1)` during child construction — child-prefetch
   counters;
3. after unique-child construction — generated/cached/unknown counts;
4. immediately before and after recursive `win(...)` — visited-delta work;
5. at the successful `!cw` return — WIN cutoff index and `put_win`;
6. at terminal LOSS and all-children-WIN return — `put_loss`.

Do not instrument `MultiDepthMemo100::get` globally in phase 1. Site-specific
counters are needed to distinguish ordering-prefetch benefit from ordinary
transposition hits.

## P8. Decision rule after all 12 parents

Continue with deeper-layer ordering research only if either of these is true:

- failed-WIN-child recursion accounts for >=25% of total visited in at least
  one depth band shared by >=6/12 parents; or
- mean first-LOSS cutoff index is >=2.0 in a depth band shared by >=6/12
  parents.

If neither is true, deprioritize ordering and move to proof/certificate reuse or
memo representation/lookup efficiency instead.

This threshold is a research-priority rule, not a statistical significance
claim.

## P9. Explicitly not tested yet

This phase does **not** test a new ordering heuristic. In particular, do not
inject memo10k, new geometry features, or oracle information below root. The
purpose is to locate avoidable work before designing the next intervention.
