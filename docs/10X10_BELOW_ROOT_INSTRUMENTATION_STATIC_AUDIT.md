# 10x10 below-root instrumentation: static accounting audit

This audit is performed before any below-root instrumented parent result is
observed.  It does not change the frozen four-parent cohort or the P8 decision
thresholds in `10X10_BELOW_ROOT_INSTRUMENTATION_PLAN.md`; it fixes accounting
semantics that are ambiguous in the first plan.

## 1. `work_into_*[d]` is inclusive candidate cost, not an additive depth decomposition

The planned measurement snapshots `st.visited` immediately before and after an
uncached recursive child call.  Therefore the delta for a child entered from
parent depth `d` contains *all* memo-miss visits in that child's recursive
subtree, including visits later attributed again to calls from depths `d+1`,
`d+2`, ... .

Consequences:

- for a fixed `d`, sibling call intervals are disjoint and
  `work_into_win_child[d] + work_into_loss_child[d] <= total_visited` is a useful
  inclusive cost attribution;
- values from different depths are nested and **must not be summed** as shares of
  total work;
- the P8 test remains well-defined when applied separately at each parent depth;
- the planned "cumulative work by depth" must not be interpreted as an additive
  decomposition.

The additive depth distribution is already available from
`Stats::depth_visited`: each memo-miss increments exactly one depth bucket.
Report both quantities, but name the recursive-delta quantity `inclusive_work`
in derived output.

Primary derived endpoint is therefore frozen as

```
failed_win_inclusive_share[d] = work_into_win_child[d] / total_visited
```

for each depth independently.  Do not sum these shares over `d`.

## 2. Freeze `expanded` versus `terminal`

In the current `win` implementation a memo miss increments `st.visited`, then a
node with empty `legal` returns LOSS without child generation.  To avoid making
`expanded` simultaneously mean "memo miss" and "generated children", define:

- `terminal[d]`: memo-miss node with empty `legal`;
- `expanded[d]`: memo-miss node with nonempty `legal`, i.e. child generation is
  actually entered.

For a completed exact run (no `ProbeExhausted` / `TableFull` exception), require

```
depth_visited[d] == terminal[d] + expanded[d]
```

at every depth.

## 3. `children_entered` includes cached children; recursive-call counters do not

`order_children` may put cached LOSS children first.  Consuming such a child can
immediately determine a WIN node without calling `win` recursively.

Freeze the semantics as:

- `children_entered[d]`: every child whose outcome is consumed in order,
  including cached children;
- `calls_into_win_child[d]`, `calls_into_loss_child[d]`: only actual recursive
  `win(...)` calls;
- `work_into_*[d]`: only those recursive calls, and may be zero if a child that
  was unknown at prefetch becomes memo-cached before its recursive entry.

Hence `children_entered` must **not** be required to equal
`calls_into_win_child + calls_into_loss_child`.

The existing `root_children_entered_` diagnostic increments only when
`!ch[i].cached`; it is therefore a recursive-entry diagnostic, not the oracle
for the new all-consumed `children_entered` counter when cached root children
exist.

## 4. `put_*` must distinguish logical completion from actual memo storage

`MultiDepthMemo100::put` is a no-op outside depths 9..17:

```
if(n<9||n>17)return;
```

The studied parents start at depth 3.  Counting every source-level `memo_.put`
call as a memo insertion would therefore falsely report storage at depths 3..8.

Freeze `put_loss[d]` / `put_win[d]` as **actual memo-store attempts only**, so
increment them only for `9 <= d <= 17`.  If logical node outcomes are useful,
they are already represented by `win_nodes`, `loss_nodes`, and `terminal`.

For a completed run, an additional consistency check at memo-supported depths
is:

```
put_loss[d] + put_win[d] == depth_visited[d]    (9 <= d <= 17)
```

provided every memo-miss node at those depths completes normally.  At depths
outside 9..17 both `put_*` must be zero.

## 5. Implementation gate before the four-state cohort

Before collecting the frozen four-parent diagnostic cohort, synthetic/regression
states must satisfy all of the following in addition to the original P0
invariants:

1. `depth_visited == terminal + expanded` per depth;
2. `put_loss + put_win == depth_visited` for depths 9..17 and `put_* == 0`
   elsewhere;
3. `children_entered >= calls_into_win_child + calls_into_loss_child` per depth;
4. each `failed_win_inclusive_share[d]` is reported independently and no
   cross-depth sum is emitted;
5. instrumented and uninstrumented `outcome`, `visited`, `maxdepth`, memo usage,
   and root diagnostics remain bit-for-bit identical.

These checks turn the instrumentation from a collection of plausible counters
into an auditable accounting system before any mechanistic conclusion is drawn.
