# 10x10 corrected independent probe vs solver-default order

This note derives a paired comparison that was not summarized in `results/10x10/blind-probe-corrected/corrected-analysis.json`.

The historical 3-stone blind result at `b5172a4` cannot be used as evidence for the probe heuristic because the reported `memo` feature was cumulative shared-solver occupancy and therefore order-confounded. The corrected rerun uses an independent fresh solver per candidate.

For each of the seven LOSS parents in the corrected rerun, compare the first-LOSS rank from the independent-probe ordering (`corrected_indep_rank`) with the first-LOSS rank in solver-default order (`solver_rank`). Lower is better.

| parent | independent probe | solver default | delta = independent - solver |
|---|---:|---:|---:|
| 2,9,33 | 9 | 2 | +7 |
| 4,9,33 | 19 | 3 | +16 |
| 9,12,33 | 20 | 18 | +2 |
| 9,19,33 | 16 | 8 | +8 |
| 9,23,33 | 15 | 3 | +12 |
| 0,31,36 | 2 | 1 | +1 |
| 0,36,44 | 9 | 6 | +3 |

All seven deltas are positive: the corrected independent-probe ordering finds the first LOSS later than solver-default order on every tested parent. The deltas are `[7,16,2,8,12,1,3]`, with median `+7` and total `+49` ranks. A two-sided exact sign test for seven same-direction differences gives `p = 2/2^7 = 0.015625`; the one-sided probability of seven independent-probe losses under a 50:50 paired null is `1/2^7 = 0.0078125`.

The corrected analysis already reports that independent probe is worse than the random-order median on all seven parents as well (`0 better, 7 worse, 0 ties`, two-sided sign-test `p=0.015625`). Thus the corrected evidence is stronger than merely "the heuristic no longer beats random": at the tested 1M budget and current memo-based rule, it is consistently worse than both the random-median benchmark and the solver's native candidate order.

The two previously highlighted counterexamples remain informative but are no longer exceptional enough to explain the failure by themselves. `4,9,33` worsens from solver rank 3 to independent-probe rank 19 (`+16`), and `9,19,33` from 8 to 16 (`+8`); however every other tested parent also moves in the same adverse direction.

## Consequence

The current hypothesis should be narrowed. The data do not support "larger/smaller independent memo occupancy at 1M is a useful first-LOSS ordering signal". Further exact-parent discovery should not be prioritized to validate that rule.

The next useful experiment is feature diagnosis on the already-labelled seven parents, without new exact solving: test whether `visited`, `maxdepth`, terminal probe status, or simple combinations of child-local features contain signal after conditioning on solver-default rank. Any replacement rule should be selected with leave-one-parent-out evaluation and compared directly against solver-default order, not only random order.
