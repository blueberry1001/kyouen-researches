# 10x10 corrected probe: exploratory score-direction check

## Status

Exploratory / post-hoc.  This is **not** a rescue of the original blind result.
The ascending direction below was proposed only after the corrected independent
`memo`-descending rule was observed to perform badly.

The original `b5172a4` success-C claim therefore remains withdrawn.

## Question

After isolating the memo table per candidate, the originally intended rule
(larger `memo` first) gave first-LOSS ranks

`9, 19, 20, 16, 15, 2, 9`

for the seven batch0 LOSS parents and was worse than the random median in all
seven parents.

That directional failure raises a separate question: does the bounded probe
contain useful information with the opposite sign?

For unresolved candidates every corrected probe has exactly 1,000,000 visited
nodes.  Therefore, within those candidates,

`1,000,000 - memo`

is a simple proxy for revisits / transposition convergence.  Sorting `memo`
ascending is equivalent to sorting this proxy descending.

## Re-analysis without new solving

The already stored 140 independent probes were joined to the already stored
exact batch0 outcomes.  No solver was rerun.

| parent | LOSS children | memo-desc | memo-asc | outcome-aware asc | exact random median |
|---|---:|---:|---:|---:|---:|
| 2,9,33 | 6 | 9 | 1 | 1 | 2 |
| 4,9,33 | 2 | 19 | 1 | 1 | 6 |
| 9,12,33 | 1 | 20 | 1 | 1 | 10 |
| 9,19,33 | 1 | 16 | 5 | 5 | 10 |
| 9,23,33 | 2 | 15 | 5 | 5 | 6 |
| 0,31,36 | 15 | 2 | 2 | 1 | 1 |
| 0,36,44 | 4 | 9 | 1 | 1 | 3 |

`outcome-aware asc` means:

1. a child proved LOSS inside the bounded probe goes first;
2. unresolved (`PROBE`) children are ordered by smaller memo first;
3. a child proved WIN inside the bounded probe goes last.

The only bounded probe that terminated early in these 140 rows is
`0-16-31-36`, proved WIN after 493,259 visited nodes with memo 487,509.  Plain
memo-ascending incorrectly puts that known WIN first.  Demoting proved WINs
moves the first LOSS for parent `0,31,36` from rank 2 to rank 1.

The exact random median is computed from

`P(R <= r) = 1 - C(m-r,l) / C(m,l)`

rather than from a Monte-Carlo simulation.  For the seven parents it is

`2, 6, 10, 10, 6, 1, 3`.

Against those exact medians:

- independent memo-desc: 0 better / 7 worse / 0 tie;
- memo-asc: 6 better / 1 worse / 0 tie;
- outcome-aware memo-asc: 6 better / 0 worse / 1 tie.

For the six non-tied parents of the outcome-aware rule, an exact two-sided sign
test gives `p = 0.03125`.

This p-value is **descriptive only** because the score direction was selected
post-hoc.  It must not be reported as a confirmatory significance result.

## New hypothesis

A fresh hypothesis suitable for a new blind test is:

> Among 10x10 three-stone parents with multiple unresolved legal children,
> children whose fixed-budget independent search visits fewer distinct memo
> states (equivalently, has more revisits / transposition convergence at the
> same visited-node budget) are more likely to be LOSS children.

The important quantity is therefore not raw cumulative memo size.  It is the
candidate-local convergence statistic under a fresh memo table.

A more explicit score for an unresolved candidate is

`redundancy = visited - memo`.

At a fixed 1M budget this has exactly the reverse ordering of `memo`.

## Highest-value confirmatory test

Do **not** tune on the seven parents above.  Freeze the rule now:

1. use fresh solver/memo per candidate;
2. same shrink/load/budget as the corrected run unless resource constraints
   require a separately declared experiment;
3. proved LOSS first, proved WIN last;
4. unresolved children sorted by `visited - memo` descending;
5. deterministic tie-break fixed before exact outcomes are inspected;
6. evaluate on new LOSS parents / batches not used to choose this direction;
7. compare first-LOSS rank against the exact random order-statistic baseline
   and solver-default ordering.

A second useful endpoint is candidate-level discrimination (LOSS vs WIN) using
`visited-memo`, evaluated by rank/AUC across each parent.  This uses all exact
children instead of only the first LOSS and can reveal whether the signal is
broad or driven by one unusually easy LOSS.

## Reproduction helper

`scripts/analyze_corrected_probe_direction.py` performs the stored-data join,
computes exact random medians, writes
`results/10x10/blind-probe-corrected/probe-direction-analysis.csv`, and reports
the sign-test summaries.

## Interpretation

The corrected result is therefore more interesting than simply "the 1M probe
failed".  The originally chosen sign failed badly, but the independent probe
appears to contain an opposite-direction structural signal.  The seven parents
are now training/exploratory data for that hypothesis.  Only a new blind set can
determine whether the signal generalizes.
