# Depth-5 memo warming causal probe

Status: preregistered before collecting provenance results.

## Motivation

The frozen depth-5 rule `child_count DESC, canonical key DESC` moved every observed cutoff LOSS child ahead of all previously explored WIN children (training 917/917 pair repairs; holdout 146/146), yet fresh-process A/B made all four fixed roots slower, with total visited nodes increasing from 108,412,449 to 391,367,803 (3.610x). The leading explanation is that earlier WIN siblings are not wasted work: they populate the depth-9..17 memo and later siblings reuse those entries.

This probe tests that mechanism directly without changing child order.

## Important implementation fact

`RankCompactTable::try_put` and `RankFlat17::try_put` do not evict/replace an occupied key. They either insert into an empty slot, find the same key/outcome, or fail because the table is full. Therefore provenance only needs to identify which depth-5 sibling first made an entry available during the current depth-5 node; there is no replacement history to reconstruct.

## Context carried during one depth-5 node

Depth-5 nodes cannot nest: recursion from a depth-5 node starts at depth 6 and only increases depth. Thus provenance scratch state may be reused for one depth-5 node at a time.

Before entering child `j` of a depth-5 node, set `active_child = j` (1-based). During recursive work at memoized depths 9..17:

- a newly inserted memo slot gets origin `j`;
- a memo hit whose origin is nonzero and `< active_child` is a **prior-sibling hit**;
- origin `== active_child` is within-child reuse and is not counted as warming;
- origin zero means the entry predated this depth-5 node and is not attributed to its siblings.

After the depth-5 node returns, clear only the origin bytes touched while processing that node. Do not clear or alter the real memo table.

Use one byte of origin per physical memo slot, not a widened memo entry. This keeps the production memo layout unchanged. A touched-slot list permits O(number of new entries) clearing rather than clearing whole sidecars. Child count is < 100, so an 8-bit 1-based child index is sufficient.

Approximate sidecar capacity from the current table powers is 100 MiB at `shrink=3` and 640 MiB at `shrink=0`; this is preferable to a 32-bit node-id sidecar (about 400 MiB and 2.5 GiB respectively). No node id is required because sidecars are cleared after each depth-5 node.

## Probe A: attribution only

Keep solver semantics unchanged. Record, separately for entry lookups and child prefetch lookups:

- prior-sibling memo hits, split by hit outcome and memo depth;
- within-child hits;
- preexisting hits;
- newly inserted entries per sibling and depth;
- for each depth-5 child, `visited_delta` and final child WIN/LOSS as evaluation labels.

For each cutoff LOSS child, report how many memo hits came from earlier WIN siblings. This mode must reproduce baseline outcome and **exactly the same visited count** for every fixed root. Any mismatch invalidates the instrumentation.

Primary descriptive quantity:

`prior_sibling_hits_consumed_by_cutoff_loss / all_memo_hits_consumed_by_cutoff_loss`.

Also report counts rather than only fractions, because a small number of high-level memo hits may save very large subtrees.

## Probe B: causal blocking

Child order and the physical memo table remain unchanged. A memo result attributed to an earlier sibling of the same depth-5 node is treated as a miss for the current child. Preexisting memo entries and within-child reuse remain available.

A subtlety matters: if the current child recomputes a blocked key and reaches `put` for that same key, the counterfactual state must treat the key as re-derived by the current child. Maintain a shadow origin for the current depth-5 node so subsequent accesses inside this child are allowed; when a later sibling starts, that re-derived entry is again prior-sibling state and is blocked. Merely ignoring the hit forever would also suppress legitimate within-child reuse and would not isolate cross-sibling warming.

The intervention therefore represents: **memo knowledge may enter a child from before the current depth-5 node or from computation inside that child, but not from another child of the same depth-5 node.**

Apply this rule to both memo access sites in `win`: the entry lookup for the current state and the child prefetch lookup used to set `Child.cached`. Blocking only one site is incomplete because sibling warming can affect both immediate returns and child ordering/cached-child shortcuts.

## Fixed roots and run protocol

Use the same four roots as the previous fixed-four experiment:

- `14,64,74`
- `12,32,55`
- `13,52,57` (previous holdout)
- `0,11,35`

For each root, baseline, attribution-only, and causal-blocking runs must use fresh processes and identical `shrink/load` settings. Preserve the existing TableFull retry policy (`shrink=3 -> 2 -> 1 -> 0`) and compare a pair only when all compared modes finish at the same setting.

## Preregistered interpretation

The memo-warming mechanism is supported if:

1. attribution-only exactly reproduces baseline outcome and visited count;
2. cutoff LOSS children consume nonzero prior-WIN-sibling memo hits in multiple roots; and
3. causal blocking increases total visited nodes with unchanged game outcome in at least 3 of 4 fixed roots.

A stronger result is obtained if the causal-blocking slowdown is largest in roots where the cutoff LOSS children consume the most prior-sibling hits or where those hits occur at shallower memoized depths.

If attribution is large but causal blocking does not increase visited, raw hit counts are not a sufficient explanation; ordering effects or memo knowledge created before the depth-5 node become more plausible. If attribution is near zero, the current memo-warming hypothesis is directly weakened despite the earlier A/B reversal.

Do not tune the blocking rule after seeing fixed-root results. Any narrower intervention (for example only depth 9, only WIN entries, or only the final cutoff child) is a separate follow-up experiment.