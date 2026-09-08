# 10×10 parent benchmark: mechanism refinement

Base: `a3916b0` (`preregister-10x10-v2-10k-parent-benchmark`).

This note is post-hoc mechanism analysis only.  It does not change the failed
preregistered endpoint.

## Key refinement

The final benchmark report correctly establishes that 10k memo-root ordering
loses against the native parent solver.  However, the phrase "shared-memo
interference" is too broad as the main explanation.

From `parent_benchmark_results.csv`:

- 12 total parents.
- **9/12 have `A_entered = B_entered = 1`**.
- Only 3 parents have a multi-root-child pattern in either condition:
  - `0,11,35`: A=6, B=3
  - `12,32,55`: A=1, B=5
  - `4,24,26`: A=9, B=4

For the 9 parents where both conditions enter exactly one root child, there is
no previously solved root child whose memo entries could influence a later
root child: there is no later root child.  Therefore their A/B cost difference
must be attributed to **which first LOSS child was chosen and the internal cost
of proving that child**, not to cross-root-child memo pollution.

The exact-only visited ratios for these 9 parents are:

`1.2230, 2.2652, 1.1363, 0.8332, 4.1699, 1.6029, 1.7911, 2.0505, 2.3968`

Summary:

- median = **1.7911**
- geometric mean ≈ **1.7505**
- native better = **8/9**
- memo-root better = **1/9**

Thus the dominant failure mode is not merely "memo order finds LOSS too late".
On these parents both orders find a LOSS immediately, but the 10k memo rule
selects a **more expensive LOSS proof**.

The 3 multi-entry parents remain the place where cross-root-child memo
interaction can matter and should be analyzed separately.

## Consequence for the research target

The original probe question was essentially classification/ranking:

> which child is LOSS?

That is no longer sufficient for solver acceleration.  The useful target is
cost-sensitive:

> among LOSS children, which one gives the cheapest proof in the shared native
> solver?

A heuristic can have excellent LOSS AUC/first-LOSS rank and still make the
parent solver slower if it selects an expensive LOSS witness.

This explains how V2 can simultaneously show:

- strong 10k LOSS ranking (first LOSS rank ≤ 5 for every parent), and
- failed native parent acceleration (median work ratio 1.84).

## Next highest-value analysis (no new exact solves required)

Before spending compute on another probe budget or C-K10 cohort, use the
already complete V2 child-level exact table and probe table to analyze **LOSS
proof cost conditional on outcome**.

For each parent, restrict to exact LOSS children and compare exact `visited`
against:

1. native static key: legal-move count (ascending), then canonical key;
2. 10k `memo_used`;
3. 1M `memo_used` (secondary, if available);
4. optional probe depth/memo shape features already recorded.

Report within-parent rank correlation and, more importantly:

- rank of the native first LOSS among LOSS children by exact proof cost;
- rank of the 10k-memo first LOSS by exact proof cost;
- cheapest-LOSS / selected-LOSS cost ratio;
- how often native selects the cheapest or near-cheapest LOSS.

This analysis distinguishes two hypotheses:

- **H-cost-static:** native legal-move ordering already predicts cheap LOSS
  proofs.  Then future work should improve that cost heuristic, not add a
  generic LOSS probe.
- **H-cost-probe:** probe statistics contain residual information about proof
  cost after conditioning on legal-move count.  Then a cost-aware hybrid may
  still help, but the target must be proof cost rather than LOSS probability.

Do not launch a new blind C-K10 validation before this conditional cost analysis;
C-K10 was selected post-hoc and its original mechanism story is now incomplete.

## Reproduction helper

`scripts/analyze_parent_benchmark_mechanism.py` reproduces the 9-vs-3
decomposition directly from the committed benchmark CSVs.
