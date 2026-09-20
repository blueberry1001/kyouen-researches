# 10x10 below-root instrumentation amendment 2

This amendment is made **before any below-root instrumented parent result is inspected**.
It fixes a memo-timing ambiguity that is not visible from the existing counters.

## Problem: a child can become memo-cached after prefetch

The current solver performs child memo lookup while constructing the complete child array:

```text
cv = memo_.get(child_key, depth + 1)
```

It then sorts all children and enters them later. For a child whose `cv == 0` at construction time, an earlier sibling's recursive search may populate the same canonical child state (or an equivalent transposition) before this child is eventually entered.

Therefore this existing path:

```text
prefetch miss -> recurse with win(child) -> win() returns from its node-entry memo lookup
```

is possible.

Such a call has:

```text
st.visited_after - st.visited_before == 0
```

because `st.visited` increments only after a node-entry memo miss.

This means the phase-1 wording "entered uncached child" is ambiguous: `cached == 0` means **uncached at child-prefetch time**, not necessarily uncached when recursion actually begins.

## Why this matters

Without separating these late memo hits, a depth can look as though many unknown children were recursively attempted while in fact a substantial fraction were made free by transpositions discovered by earlier siblings.

That distinction changes the mechanism diagnosis:

- high positive-work failed-WIN recursion => ordering really spends search work on bad candidates;
- many zero-work calls after prefetch miss => transposition reuse is already rescuing the ordering, and improving memo/prefetch representation may matter more than changing child order.

## Frozen additional counters

Keep all previously frozen counters. Add, per parent depth `d`:

- `late_entry_hit_win[d]`
- `late_entry_hit_loss[d]`

Definition: for a child with `ch[i].cached == 0`, snapshot `st.visited`, call `win(...)`, then compute the delta. If the delta is zero, increment exactly one of these counters according to the returned child outcome.

These are not new solver decisions. They are derived from the already planned before/after visited snapshots and therefore do not change search semantics.

Required consistency checks:

```text
late_entry_hit_win[d] <= calls_into_win_child[d]
late_entry_hit_loss[d] <= calls_into_loss_child[d]
```

and the positive-work recursive-call counts are:

```text
positive_work_win_calls[d] = calls_into_win_child[d] - late_entry_hit_win[d]
positive_work_loss_calls[d] = calls_into_loss_child[d] - late_entry_hit_loss[d]
```

## Miss counters need not be stored separately

The original plan names `entry_miss` and `child_miss` in consistency equations but does not list them as output columns. That is acceptable if they are derived exactly as:

```text
entry_miss[d] = entry_get[d] - entry_hit_loss[d] - entry_hit_win[d]
child_miss[d] = child_get[d] - child_hit_loss[d] - child_hit_win[d]
```

No extra miss counters are required.

## Reporting amendment

For each depth, report all three quantities together:

1. `unique_visited_fraction[d] = expanded[d] / sum(expanded)` — where unique search work occurs;
2. `failed_win_fraction[d]` from positive visited deltas — how much launched subtree work goes into children that end WIN;
3. `late_entry_hit_fraction[d] = (late_entry_hit_win + late_entry_hit_loss) / (calls_into_win_child + calls_into_loss_child)` — how often a prefetch miss becomes free before entry.

The existing >=25% continuation threshold is evaluated using visited work, so zero-work late hits do not contribute to its numerator or denominator. This amendment only prevents the call-count interpretation from conflating true recursive expansion with late transposition hits.
