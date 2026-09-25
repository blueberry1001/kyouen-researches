# Cached-LOSS prefix memo causal ablation

## Motivation

The provenance counters preregistered on this branch answer an observational
question: are memo entries first created inside a blind-order prefix reused
after that prefix exits?

That is not yet the causal quantity needed for the mechanism claim. A tagged
entry can have zero direct later hits but still alter later search indirectly,
and a later hit can occur on a path that would disappear if the prefix-created
memo were absent. `later_reuse_any` and `later_reuse_outside_prefix` therefore
remain diagnostics, not estimates of saved work.

## Causal intervention

Add a paired blind-order run, identical to the ordinary blind solver except for
one intervention:

1. When outer cached-LOSS-prefix depth changes `0 -> 1`, start one ownership
   event, using the already-preregistered owner bookkeeping.
2. Every memo slot first inserted while that outer event is active is marked as
   owned by the event. Nested prefixes share the outer owner.
3. On the matching outer exit (`1 -> 0`), invalidate exactly the memo entries
   still occupying slots owned by that event.
4. Do not undo visited work, counters, or memo entries that predate the event.
   Do not invalidate slots that have been cleared/reused since their tagged
   insertion.
5. Continue the search normally. Future consequences of the invalidation,
   including changed paths and changed later memo creation, are intentionally
   retained.

Call this condition **blind-prefix-forget** (`BPF`). The ordinary blind run is
`B`.

The intervention is deliberately at outer exit rather than at insertion: work
inside the prefix is kept identical for as long as possible. The contrast
therefore targets the *future value of memo state produced by that prefix*, not
the immediate cost of traversing the prefix.

## Invalidation implementation constraint

The owner-event sidecar is sufficient for provenance counting, but by itself it
does not provide an efficient way to enumerate every entry owned by one event
at outer exit. Do **not** silently reintroduce an O(table-size) scan at every
outer exit merely to implement step 3 above.

Prefer lazy logical invalidation. In BPF mode, after an outer event exits, a
lookup must behave as though any still-current entry with

```
origin_outer_event != 0 && origin_outer_event <= last_exited_outer_event
```

is absent. A slot whose payload has been cleared/replaced must also have its
owner metadata cleared/replaced, so a later occupant is never rejected because
of an old owner id.

The production `Memo` in `cpp/solvers/kyouen_solver_verify.cpp` is linear
probing: `get` continues while `v[i] != 0` and stops at the first physically
empty slot; `put` likewise probes occupied slots and inserts only at a physical
empty slot. It has no deletion/tombstone path. Therefore merely suppressing a
forgotten slot as a hit while leaving it permanently occupied is **not** an
exact implementation of eager forgetting: forgotten entries would consume
capacity forever, lengthen later probe chains, and could change insertion
behaviour independently of the intended memo-state intervention.

For BPF, treat a logically forgotten slot as a tombstone with the following
frozen semantics:

- lookup: it is never a hit, but probing continues through it;
- insertion: remember the first logically forgotten slot encountered, continue
  probing far enough to preserve ordinary same-key/update semantics, and if no
  live copy of the key is found before the first true empty slot, insert into
  the remembered forgotten slot (or the true empty slot if there was none);
- **all BPF probe loops must be bounded to at most one complete table cycle.**
  A tombstone may coexist with no physically empty slot: lazy invalidation does
  not clear `v[i]`, so the original production loop's `while(v[i])` stopping
  rule is no longer sufficient. If insertion completes a full cycle without a
  true empty slot and has remembered a forgotten slot, insert into that slot.
  If no forgotten slot exists either, fail explicitly as a genuinely full
  table. Lookup likewise returns miss after one complete cycle. Never spin
  waiting for a physical empty slot;
- **updating an already-live copy of the same key is not a new insertion and
  must preserve its existing owner metadata.** In particular, an entry that
  predates the current prefix must remain owner zero (or its prior still-live
  owner) when `put` touches it inside the prefix; otherwise BPF would wrongly
  erase pre-prefix memo state at outer exit;
- replacement/reinsertion into a true empty or logically forgotten slot must
  write new owner metadata from the *current* context: current outer event id
  when inside a prefix, otherwise zero. It must never inherit the forgotten
  occupant's owner id;
- a stale copy of the same key is not a live existing memo entry. Recomputing
  that state may make it live again, and the new value/owner must then be
  observable normally;
- **do not reuse the production `Memo::u` counter as BPF logical occupancy.**
  In the current table `u` increases only when a physical empty slot is first
  occupied. Lazy forgetting leaves that slot physically occupied, so a later
  tombstone reuse must not increment physical occupancy; conversely, logical
  live occupancy must decrease when an owner becomes stale even though no slot
  is touched at that moment. Keep the original physical-use counter semantics
  unchanged for implementation diagnostics and maintain a separate BPF logical
  live-entry count (or derive it only in an explicitly labelled audit scan).
  Any reported B/BPF memo-size comparison must use the logical count, not `u`;
- **a separate logical-live counter still needs event-local accounting.** Lazy
  invalidation deliberately avoids enumerating an event's slots at outer exit,
  so `logical_live` cannot be decremented correctly from the owner sidecar alone
  without either an O(table-size) scan or an additional count. Maintain
  `active_owned_live`: reset it to zero on outer `0 -> 1`; increment it only
  when a new live entry is inserted with the current active owner; decrement it
  if such a currently-active-owned entry is cleared/replaced before outer exit;
  do not change it for same-key live updates. On the matching `1 -> 0`, perform
  `logical_live -= active_owned_live` in O(1), then advance
  `last_exited_outer_event` and clear `active_owned_live`. Reinserting into an
  old tombstone after that exit increments `logical_live` normally and, if it
  occurs inside a later outer event, increments that later event's
  `active_owned_live`. Assert `0 <= active_owned_live <= logical_live` and that
  it is zero whenever outer depth is zero.

Thus ownership is a property of the insertion that created the currently-live
entry, not of the most recent `put` call that mentioned its key. This is needed
to keep the implementation identical to causal step 2 ("first inserted") and
step 4 (pre-existing entries survive).

This gives forgotten slots the standard open-addressing tombstone role while
allowing their capacity to be reclaimed. It is required for the lazy BPF table
to represent the same logical map as eager deletion without breaking collision
chains. A permanently occupied stale-slot implementation is prohibited even
if its lookup hit/miss answers initially agree with an eager reference.

This is an implementation constraint, not a change to the intervention: BPF
must expose exactly the same memo state to subsequent solver logic as eager
invalidation would, modulo representation-internal tombstones/occupancy needed
to preserve lookup correctness.

## Primary causal quantity

For each frozen parent, report

```
future_memo_value = visited(BPF) - visited(B)
relative_future_memo_value = (visited(BPF) - visited(B)) / visited(B)
```

Positive values mean that prefix-created memo pays back later; zero means no
net future value at visited-node resolution. Negative values are allowed and
would mean the retained memo state is, on balance, harmful to the subsequent
search order/cache trajectory.

This quantity includes downstream cascades. That is intentional: it is the
causal effect of retaining the prefix-produced memo state, not a sum of direct
memo hits.

## Relationship to the loss-first gain

Keep the existing loss-first run `L` unchanged. For each parent also report

```
immediate_plus_trajectory_gain = visited(B) - visited(L)
```

Do **not** assert the identity

```
visited(B) - visited(L)
  = prefix_visited - future_memo_value
```

because loss-first changes the prefix itself and therefore the later search
trajectory. BPF is a mechanism probe, not an additive decomposition of the
B-vs-L endpoint.

The useful interpretation is narrower:

- if `future_memo_value` is tiny while B->L is large, the hypothesis that blind
  prefixes are valuable mainly as memo investment is weakened;
- if `future_memo_value` is substantial and positive, the memo-investment
  counterforce is real and a trajectory/DAG analysis is justified.

## Frozen cohort and reporting

Use the same 12-parent frozen cohort and solver settings as the existing
loss-first confirmatory endpoint. Do not select parents based on provenance
results. Report all 12 paired B/BPF values, median relative effect, total
visited effect, and the sign count (BPF > B / = / <).

No new pass/fail threshold is introduced here. The previously preregistered
`later hits / put < 0.05` rule remains unchanged and applies only to its stated
observational diagnostic. BPF is a separate causal follow-up.

## Required safety checks before the 12-parent run

1. Instrumentation/ablation disabled reproduces the existing blind endpoint
   exactly.
2. A synthetic single outer prefix with one inserted entry invalidates that
   entry at outer exit.
3. A nested prefix does not invalidate at inner exit.
4. A pre-existing memo entry touched inside the prefix survives outer exit;
   assert explicitly that a same-key `put` inside the prefix leaves its owner
   unchanged as well as leaving the value live.
5. A tagged slot cleared/reused before outer exit is not used to invalidate the
   replacement entry.
6. A run containing no cached-LOSS prefix is bit-for-bit/endpoint identical
   between B and BPF.
7. For the production linear-probing table, construct a collision chain A -> B
   where A is prefix-owned and B is not; after A is forgotten, B must remain
   findable.
8. Force insertion after a forgotten A in a collision chain and verify that A's
   slot is reclaimable rather than permanently consuming capacity, while later
   colliding live entries remain findable.
9. Forget key A, recompute A, and insert it once outside a prefix and once inside
   a new prefix. Both must become live again with owner zero / the new owner,
   respectively; the old owner must not survive.
10. Compare lazy invalidation against a small reference memo that eagerly
    removes forgotten entries over randomized insert/lookup/clear/outer-exit
    traces. Compare not only hit/miss/value answers but also logical live-entry
    count; periodically force enough insertions to exercise stale-slot reuse.
11. Fill a small physical table completely, make at least one slot logically
    forgotten while leaving no `v[i] == 0` slot, then verify that lookup of an
    absent key terminates and that insertion reuses the remembered forgotten
    slot after at most one full probe cycle. Repeat with a completely live full
    table and require an explicit full-table failure rather than an infinite
    probe.
12. On at least one real parent that contains a cached-LOSS prefix, run B and
    BPF with a temporary deterministic trace digest over solver-visible events
    (visited state/key, memo hit/miss/value, generated child order, memo writes,
    and cached-LOSS prefix enter/exit). Require the digests and event counts to
    be identical through and including the final solver-visible event before
    the first outer `1 -> 0` invalidation point. Permit divergence only after
    that intervention. This guards against owner bookkeeping, BPF-aware probing,
    or instrumentation accidentally perturbing the very prefix whose future
    memo value the experiment is supposed to isolate.
13. On a tiny table, record physical `u`, logical live-entry count, and
    `active_owned_live`. Insert multiple current-event entries, perform a
    same-key live update and remove/reuse one current-owned entry before exit,
    and require `active_owned_live` to track exactly the surviving current-owner
    entries. At outer exit require `logical_live` to drop by exactly that count
    in O(1) while `u` remains unchanged and `active_owned_live` resets to zero.
    After reusing a stale tombstone, require `u` still unchanged while logical
    live count increases by one. Compare the logical count against the
    eager-deletion reference. This checks both occupancy meaning and the
    no-table-scan accounting needed by lazy invalidation.
14. Add a metamorphic zero-intervention test: execute a trace containing one or
    more genuine outer cached-LOSS prefixes but arrange that every such prefix
    exits with `active_owned_live == 0` (for example, prefixes that create no
    new memo entries, plus a synthetic case where every current-owner entry is
    removed/reused before exit). BPF and B must then remain identical for the
    complete remaining trace: same live logical map, hit/miss/value answers,
    insertion success/failure, solver-visible event digest, outcome, and
    `visited`. This is stronger than the no-prefix test in item 6: it verifies
    that merely entering/exiting prefixes and advancing owner-event bookkeeping
    is observationally inert when the intervention removes no surviving state.

The last property follows inductively: before the first zero-owned outer exit,
B and BPF are identical; that exit invalidates no live entry, so their logical
maps remain identical; repeating the argument over subsequent zero-owned exits
preserves equivalence. A failure therefore localizes an implementation leak in
owner/tombstone/accounting machinery rather than a real causal effect.

## Priority

Implement BPF only after the owner-state model tests already on this branch
pass. It has higher inferential value than adding more direct-hit counters,
because it measures the downstream consequence of prefix-produced memo rather
than treating observed reuse as a proxy for that consequence.
