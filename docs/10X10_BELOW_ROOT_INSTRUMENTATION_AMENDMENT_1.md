# 10x10 below-root instrumentation amendment 1

This amendment is made **before any below-root instrumented parent result is inspected**.
It corrects one ambiguity in `10X10_BELOW_ROOT_INSTRUMENTATION_PLAN.md` without changing the frozen cohort, counters, or continuation thresholds.

## Problem: recursive visited deltas overlap across depth

For an uncached child, the planned measurement

```text
before = st.visited
cw = win(child, depth + 1, st)
after = st.visited
work = after - before
```

is the full visited size of that child's recursive subtree.
That is useful when conditioning on the **parent depth**, because sibling child subtrees entered from nodes at the same depth are disjoint in the actual depth-first execution.

However, the same visited node also lies inside the recursive subtree measured for its parent, grandparent, etc. Therefore `work_into_*[d]` must **not be summed across d** and interpreted as unique solver work. Such a cross-depth sum double-counts nested recursion.

Example: if a depth-4 child call visits 100 nodes and, inside it, a depth-5 child call visits 70 nodes, the depth-conditioned counters legitimately record 100 at parent depth 4 and 70 at parent depth 5. The solver did not perform 170 unique visits.

## Frozen interpretation

Keep the planned counters unchanged. Interpret them as conditional subtree-cost measurements:

```text
failed_win_fraction[d] =
    work_into_win_child[d]
    / (work_into_win_child[d] + work_into_loss_child[d])
```

when the denominator is nonzero.

This answers the intended mechanistic question at each parent depth:

> Of recursive subtree work launched by expanded nodes at this depth, what fraction was spent proving children that ultimately turned out WIN and therefore did not provide the node's winning cutoff?

Likewise, compare `work_into_win_child[d]` and `work_into_loss_child[d]` only within the same parent depth, or parent-by-parent at a fixed depth.

## Unique-work localization

For statements about where the solver's **unique** visited work occurs, use the already planned `expanded[d]` counts instead:

```text
unique_visited_fraction[d] = expanded[d] / sum_d expanded[d]
```

`st.visited` increments exactly once on a node-entry memo miss, so `expanded[d]` should equal the number of unique visited events attributed to depth `d` by the instrumentation. Required invariant:

```text
sum_d expanded[d] == st.visited
```

for a completed solve (assuming instrumentation increments `expanded[d]` immediately after the entry memo miss, at the same point as `++st.visited`).

This new invariant is stronger than a cross-depth sum of recursive deltas and should be checked for every diagnostic parent.

## Decision-rule clarification

The preregistered continuation rule remains unchanged, but its first clause is evaluated **per depth band**, never after summing recursive work over depths:

- continue if failed-WIN-child recursion is >=25% at a shared depth band for >=6/12 parents; or
- continue if mean first-LOSS cutoff index is >=2.0 at a shared depth band for >=6/12 parents.

For reporting, include both:

1. `unique_visited_fraction[d]` from `expanded[d]`, showing where unique search nodes occur; and
2. `failed_win_fraction[d]`, showing the composition of child-subtree work launched at that depth.

Together these distinguish a depth with a high failure fraction but negligible search mass from a depth that is both expensive and poorly ordered.
