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

- a newly inserted memo key gets origin `j`;
- a memo hit whose origin is nonzero and `< active_child` is a **prior-sibling hit**;
- origin `== active_child` is within-child reuse and is not counted as warming;
- no origin record means the entry predated this depth-5 node and is not attributed to its siblings.

After the depth-5 node returns, discard the provenance scratch state. Do not clear or alter the real memo table.

### Implementation refinement before data collection: sparse logical-key provenance

The intervention does **not** require exposing physical hash-table slots. The solver already has the exact canonical `Bits key` at both memo access sites, and a state's stone count determines its memo depth. Use the canonical state itself as the provenance identity, e.g. `unordered_map<Bits, uint8_t, BitsHash> origin` for keys first produced during the active depth-5 node.

This is equivalent to physical-slot attribution for this experiment because the production memo has no eviction/replacement and because provenance is only queried for exact canonical states that the solver is already looking up. It is also substantially less invasive: `RankCompactTable`, `RankFlat17`, and `MultiDepthMemo100` need no slot-aware API, and the previous 100 MiB (`shrink=3`) to 640 MiB (`shrink=0`) byte sidecars are avoided.

A genuinely new memo key can be detected without modifying `try_put`: each `win` call already performs its entry lookup before expansion. Save that **raw physical memo result** in the stack frame. If it was a miss and the call later reaches `memo_.put(key, depth, outcome)`, the key is newly produced by this computation and `origin.try_emplace(key, active_child)` records its first sibling. Recursion only increases the stone count, so a descendant cannot independently insert the same `(state, depth)` between that entry miss and this call's return.

If the raw entry lookup was a prior-sibling hit that Probe B deliberately blocked, recomputation reaches `put` while the physical memo still contains the old entry. In that case do not change `origin`; instead add the canonical key to a per-child `rederived` set. Later accesses to a key in `rederived` are allowed inside the same child. Clear `rederived` before starting each next depth-5 sibling. This preserves the frozen counterfactual: physical knowledge from another sibling is unavailable, but knowledge recomputed inside the current child may be reused.

This refinement changes only bookkeeping representation, not the preregistered intervention or success criteria, and is fixed before collecting provenance results.

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

A subtlety matters: if the current child recomputes a blocked key and reaches `put` for that same key, the counterfactual state must treat the key as re-derived by the current child. Maintain the per-child `rederived` set described above so subsequent accesses inside this child are allowed; when a later sibling starts, `rederived` is cleared and that physical entry is again prior-sibling state and is blocked. Merely ignoring the hit forever would also suppress legitimate within-child reuse and would not isolate cross-sibling warming.

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
