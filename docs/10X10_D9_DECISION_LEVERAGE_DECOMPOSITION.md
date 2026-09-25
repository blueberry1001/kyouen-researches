# D9 one-shot read-mask: decision-leverage decomposition

Status: analysis plan frozen before D9LM1R/D9WM1R cohort execution.

## Mechanistic hypothesis

A LOSS-valued child and a WIN-valued child are not symmetric facts for the parent search.
In the production negamax-style loop, a cached child value avoids recursion in either case,
but a cached LOSS child additionally proves the current parent WIN and can terminate the
remaining sibling scan immediately. A cached WIN child only proves that this particular
move is not a winning witness for the parent; search continues.

This gives a concrete alternative to the vague statement that "LOSS memo entries are more
valuable": the excess value may be **decision leverage** (probability of causing an immediate
parent cutoff), rather than greater computational cost to recompute a LOSS state itself.
The existing loss-first-only endpoint strongly motivates this decomposition: promoting only
the B-earliest cached LOSS recovered the full cache-aware visited reduction on all 12 frozen
parents, while cached-WIN demotion contributed no residual visited benefit.

## Frozen measurements

For every selected D9LM1R / D9WM1R key, record the following without changing selection:

1. `first_consumption_site`: `entry` or `child_prefetch`.
2. `first_prefetch_parent_rank` and the child's sibling index in that parent's actual order.
3. `siblings_remaining_at_first_consumption` immediately after that child.
4. `first_consumption_causes_parent_cutoff`: true iff consuming the memo value makes that
   parent return WIN without examining another sibling.
5. `recompute_visited_inclusive`: number of newly visited nodes between entry and return of
   the frame entered because this key is masked. This deliberately includes descendant work.
6. `recompute_visited_exclusive`: newly visited nodes charged to this masked key after
   subtracting intervals owned by nested masked-key recomputations. Ownership follows the
   innermost active masked recomputation frame, so every visited node is charged to at most
   one selected key.
7. `nested_masked_recomputations`: number of other selected masked keys whose genuine
   recomputation starts while this key's recomputation frame is active.
8. `post_recompute_parent_cutoff`: whether the recomputed value causes the same immediate
   parent cutoff at that consumption site.
9. `masked_key_reuses_before_retirement`: number of suppressed reads of the same epoch-0
   fact before its genuine recomputation retires the mask.

Instrumentation must be observational: no ordering, memo bytes, occupancy, mask selection,
or retirement rule may depend on these measurements.

### Non-overlap rule for recomputation cost

Several keys are masked simultaneously. Therefore a masked depth-9 frame can recursively
enter another selected masked depth-9 key before returning. A raw frame-entry-to-return
counter is then *inclusive*: summing it across keys double-counts the nested subtree and can
make one treatment arm appear intrinsically more expensive merely because its selected keys
nest more often.

Keep the inclusive counter as a useful per-key latency-like diagnostic, but do not sum it or
interpret its arm total as work. The additive recomputation-cost endpoint is
`recompute_visited_exclusive`, with innermost-frame ownership as defined above. As a check,
the sum of exclusive charges must not exceed the treatment run's total visited count, and a
synthetic nested-mask test must show that the inner interval is counted once, not once for
each active masked frame.

## Frozen summaries

Report LOSS and WIN separately for:

- fraction first consumed by child-prefetch;
- fraction whose first consumption causes an immediate parent cutoff;
- median `recompute_visited_inclusive`;
- median and total `recompute_visited_exclusive`;
- fraction of recomputations containing at least one nested masked recomputation;
- median `siblings_remaining_at_first_consumption`;
- median suppressed reads before retirement.

Then stratify the one-shot treatment effect by `first_consumption_causes_parent_cutoff` using
only the baseline / pre-intervention consumption classification where available. Do not
reselect keys from treatment traces.

## Interpretation

- If LOSS has much larger cutoff incidence but comparable exclusive recomputation cost, the
  primary mechanism is decision leverage: LOSS facts are valuable because they terminate
  parent search, not because LOSS states are intrinsically more expensive to solve.
- If cutoff incidence is comparable but LOSS exclusive recomputation cost is much larger,
  intrinsic recomputation cost is the stronger explanation.
- If both are larger for LOSS, report both mechanisms; do not collapse them into a single
  "LOSS value" claim.
- If neither differs materially while D9LM1R still exceeds D9WM1R, the remaining candidate
  is reuse topology / downstream path divergence and requires a separate decomposition.
- A LOSS/WIN difference visible only in inclusive cost, together with different nesting
  rates, is evidence for recomputation topology rather than intrinsic per-key cost.

## Important asymmetry in causal interpretation

`first_consumption_causes_parent_cutoff` is partly determined by the memo value itself, so it
is a mechanism variable, not a pretreatment covariate suitable for a clean subgroup causal
claim. The stratified treatment-effect table is descriptive only. The primary causal
contrast remains the preregistered matched one-shot LOSS-vs-WIN intervention; this document
only decomposes why that contrast may differ.
