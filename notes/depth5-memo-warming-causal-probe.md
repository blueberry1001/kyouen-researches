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

### Implementation refinement before data collection: bounded physical-slot provenance

The previous draft proposed sparse logical-key provenance with `unordered_map<Bits, uint8_t, BitsHash>`. Existing fixed-root artifacts show that this representation is not safely bounded enough for the largest run: baseline `0,11,35` at `shrink=0` finishes with 85,151,103 memo entries, and one observed depth-5 node alone accounts for 5,951,125 visited nodes. A node-local hash map could therefore contain millions of 128-bit keys; allocator/bucket overhead can exceed the cost of a compact sidecar and can become a new memory bottleneck. This was discovered before collecting any provenance results, so the intervention and interpretation remain frozen while only the bookkeeping representation changes.

Use **one provenance byte per physical memo slot** instead. The maximum `shrink=0` capacity over all depth-9..17 tables is 671,612,928 slots = 640.5 MiB of provenance bytes; smaller shrink settings use correspondingly less. This is a deterministic upper bound rather than workload-dependent hash-map overhead.

Expose the physical slot reached by `get`/`try_put` through an instrumentation-only API. Depths 11..14 have two backing tables, so the returned identity must retain the backing-table identity as well as the slot. The production lookup/insert semantics and packed memo entries themselves remain unchanged.

Encode the current depth-5 sibling owner in the low seven bits of the provenance byte (`1..100` fits). Reserve the high bit as **rederived in the current child**. This avoids a second side table:

- when a new memo slot is first inserted while child `j` is active, write owner `j` to its provenance byte and append that byte's address/slot identity to a `node_touched` list;
- a hit with owner `< active_child` and high bit clear is a prior-sibling hit;
- in Probe B such a hit is blocked and treated as a miss;
- if recomputation later reaches `put` for that already-existing prior-sibling slot, set the high bit and append it to a `child_rederived` list;
- while the high bit is set, subsequent accesses inside the same child are allowed as within-child reuse;
- before the next sibling, clear the high bit for `child_rederived` only;
- after the depth-5 node finishes, clear provenance bytes in `node_touched` only, rather than scanning the full sidecar.

Because the real memo never relocates or replaces occupied entries, stored slot identities remain stable. The touched lists make reset cost proportional to entries actually created/rederived in that depth-5 node, while the provenance storage itself remains a fixed one-byte-per-slot bound.

A useful simplification follows from solver control flow: every **completed earlier sibling** of a currently explored child is necessarily WIN. A LOSS sibling would have caused the parent to return immediately, so there can be no later sibling. Therefore `prior-sibling hit` and `prior-WIN-sibling hit` are identical on the actually observed search path; no separate sibling-outcome provenance field is required.

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

A subtlety matters: if the current child recomputes a blocked key and reaches `put` for that same key, the counterfactual state must treat the key as re-derived by the current child. Use the high-bit mechanism described above so subsequent accesses inside this child are allowed; when a later sibling starts, clear the rederived high bits and expose the original low-bit sibling owner again. Merely ignoring the hit forever would also suppress legitimate within-child reuse and would not isolate cross-sibling warming.

The intervention therefore represents: **memo knowledge may enter a child from before the current depth-5 node or from computation inside that child, but not from another child of the same depth-5 node.**

Apply this rule to both memo access sites in `win`: the entry lookup for the current state and the child prefetch lookup used to set `Child.cached`. Blocking only one site is incomplete because sibling warming can affect both immediate returns and child ordering/cached-child shortcuts.

## Fixed roots and run protocol

Use the same four roots as the previous fixed-four experiment:

- `14,64,74`
- `12,32,55`
- `13,52,57` (previous holdout)
- `0,11,35`

For each root, baseline, attribution-only, and causal-blocking runs must use fresh processes and identical `shrink/load` settings. Preserve the existing TableFull retry policy (`shrink=3 -> 2 -> 1 -> 0`) and compare a set only when all compared modes finish at the same setting.

## Preregistered interpretation

The memo-warming mechanism is supported if:

1. attribution-only exactly reproduces baseline outcome and visited count;
2. cutoff LOSS children consume nonzero prior-sibling memo hits in multiple roots; and
3. causal blocking increases total visited nodes with unchanged game outcome in at least 3 of 4 fixed roots.

A stronger result is obtained if the causal-blocking slowdown is largest in roots where the cutoff LOSS children consume the most prior-sibling hits or where those hits occur at shallower memoized depths.

If attribution is large but causal blocking does not increase visited, raw hit counts are not a sufficient explanation; ordering effects or memo knowledge created before the depth-5 node become more plausible. If attribution is near zero, the current memo-warming hypothesis is directly weakened despite the earlier A/B reversal.

Do not tune the blocking rule after seeing fixed-root results. Any narrower intervention (for example only depth 9, only WIN entries, or only the final cutoff child) is a separate follow-up experiment.
