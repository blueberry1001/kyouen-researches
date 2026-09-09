# 10x10 below-root instrumentation amendment 2

This amendment is made **before any below-root instrumented parent result is inspected**.
It fixes a second attribution ambiguity that remains after Amendment 1.
The frozen four-parent cohort and the continuation thresholds are unchanged.

## Problem: child outcome alone does not identify ordering waste

The phase-1 plan pools recursive work only by the outcome of the entered child:

```text
work_into_win_child[d]
work_into_loss_child[d]
```

and Amendment 1 proposed the depth-local quantity

```text
work_into_win_child[d]
/ (work_into_win_child[d] + work_into_loss_child[d])
```

as a failed-WIN fraction.

That interpretation is not valid unless the **parent outcome** is also known.

For a WIN parent, WIN children entered before the first LOSS child are failed
candidate searches. Their work is potentially avoidable by a better ordering.

For a LOSS parent, however, every child is WIN and every unique child must be
proved WIN. Work spent in those WIN children is mandatory for the LOSS proof;
it is not failed witness-search work and cannot be removed merely by reordering.

Pooling these two cases can therefore overstate the amount of work available to
an ordering improvement, especially at depths where LOSS parents are common.

## Required parent-outcome stratification

Keep the original pooled counters for compatibility, but add the following
counters by parent depth `d`:

```text
win_parent_work_into_win_child[d]
win_parent_work_into_loss_child[d]
loss_parent_work_into_win_child[d]

win_parent_calls_into_win_child[d]
win_parent_calls_into_loss_child[d]
loss_parent_calls_into_win_child[d]
```

For completed exact search,

```text
loss_parent_work_into_loss_child[d] == 0
```

by game semantics, so it need not be a stored counter. The same is true for the
corresponding call count. It may optionally be asserted as zero in debug code.

Required consistency checks:

```text
work_into_win_child[d]
  == win_parent_work_into_win_child[d]
   + loss_parent_work_into_win_child[d]

work_into_loss_child[d]
  == win_parent_work_into_loss_child[d]

calls_into_win_child[d]
  == win_parent_calls_into_win_child[d]
   + loss_parent_calls_into_win_child[d]

calls_into_loss_child[d]
  == win_parent_calls_into_loss_child[d]
```

for every depth in every completed diagnostic solve.

## Semantics-preserving implementation

The parent outcome is known only when the node returns, so do not change child
selection or add memo lookups. Instead, accumulate recursive deltas in local
per-invocation variables while the existing child loop runs:

```text
local_work_win_child
local_work_loss_child
local_calls_win_child
local_calls_loss_child
```

After an uncached child returns, update only these locals according to `cw`.

If `!cw` causes the existing WIN return, flush the locals to the
`win_parent_*[d]` counters immediately before returning.

If all children are WIN and the existing LOSS return is reached, flush the
locals to `loss_parent_*[d]`. In a correct completed solve,
`local_work_loss_child` and `local_calls_loss_child` must then be zero.

Cached children still count in `children_entered`, exactly as in the original
plan, but contribute no recursive visited delta and therefore do not enter these
work counters.

This adds observation only; it must not alter sorting, memo access, recursion,
or return decisions.

## Correct derived quantities

Amendment 1's pooled `failed_win_fraction[d]` is retained only as a descriptive
child-outcome composition and must **not** be called ordering waste.

The primary ordering-waste quantity is instead:

```text
avoidable_ordering_work_share[d] =
    win_parent_work_into_win_child[d]
    /
    (win_parent_work_into_win_child[d]
     + win_parent_work_into_loss_child[d]
     + loss_parent_work_into_win_child[d])
```

when the denominator is nonzero.

This asks:

> Of recursive subtree work launched by expanded nodes at this parent depth,
> what fraction was spent on WIN children of nodes that eventually found a LOSS
> witness and therefore could, in principle, have been avoided by perfect child
> ordering?

Also report the conditional ordering quality among WIN parents:

```text
win_parent_failed_fraction[d] =
    win_parent_work_into_win_child[d]
    /
    (win_parent_work_into_win_child[d]
     + win_parent_work_into_loss_child[d])
```

This second quantity is mechanistically useful but is not a measure of total
solver headroom because it excludes mandatory LOSS-parent work.

Unique-work localization remains exactly as fixed in Amendment 1:

```text
unique_visited_fraction[d] = expanded[d] / sum_d expanded[d]
```

Recursive work deltas remain inclusive and must never be summed across depth.

## Continuation rule interpretation

The numerical threshold from the original preregistration is unchanged. Its
first clause is evaluated using `avoidable_ordering_work_share[d]`, not the
pooled child-outcome fraction:

- continue deeper-layer ordering research if avoidable ordering work is >=25%
  in a depth band shared by >=6/12 parents; or
- continue if mean first-LOSS cutoff index is >=2.0 in a depth band shared by
  >=6/12 parents.

This preserves the intended question—whether a material fraction of current
solver work is plausibly removable by ordering—without counting mandatory work
needed to prove LOSS parents.

## Output amendment

Append these columns to each depth row and TOTAL row in the machine-readable
instrumentation output:

```text
win_parent_work_into_win_child,
win_parent_work_into_loss_child,
loss_parent_work_into_win_child,
win_parent_calls_into_win_child,
win_parent_calls_into_loss_child,
loss_parent_calls_into_win_child
```

Derived summaries must record both amendment commit SHAs before any instrumented
parent result is interpreted.