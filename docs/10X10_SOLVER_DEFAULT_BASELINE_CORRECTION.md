# 10x10 solver-default baseline correction

## Finding

The `solver_default_rank` column in `results/10x10/blind-probe-rankings.csv` must not be interpreted as the legal-move-count ordering used inside the recursive solver.

For every parent in the saved ranking table, `solver_default_rank` is exactly the candidate-generation position 1..20. Recomputing the number of legal next moves for each child gives a non-monotone sequence for all seven parents that contain a LOSS. Therefore the saved `solver_default_rank` baseline and a `legal_move_count`-ascending baseline are distinct orderings.

This corrects the previous interpretation that the independent probe's loss against `solver_default_rank` demonstrated a loss against the solver's legal-move heuristic. What it actually demonstrates is a loss against the saved candidate-generation order.

## Parent-level check

For each LOSS parent, the exact labels in `blind-probe-rankings.csv` were combined with an independently recomputed legal-next-move count. Because ties in legal count are not resolved here, the legal-count baseline is represented by the best/worst possible first-LOSS rank within the relevant tie group.

| parent | saved `solver_default` first LOSS | legal-count first LOSS interval |
|---|---:|---:|
| `2,9,33` | 2 | 1--1 |
| `4,9,33` | 3 | 3--3 |
| `9,12,33` | 18 | 17--19 |
| `9,19,33` | 8 | 9--13 |
| `9,23,33` | 3 | 1--2 |
| `0,31,36` | 1 | 1--1 |
| `0,36,44` | 6 | 6--7 |

The median of both legal-count interval endpoints is 3, coincidentally the same headline median as the saved candidate-generation baseline. The parent-level behavior is nevertheless different. In particular, `9,19,33` proves the two orders cannot be identified: its saved baseline finds the LOSS at rank 8, whereas legal-count ordering cannot place it earlier than rank 9. Conversely, `2,9,33` has a guaranteed legal-count first LOSS at rank 1 while the saved baseline finds one at rank 2.

## Consequence for the probe hypothesis

The corrected independent-probe result (7/7 worse than the saved `solver_default_rank`) remains evidence against using the 1M `memo_used` score as a wholesale replacement for candidate-generation order. It is **not** evidence that the score loses 7/7 against `legal_move_count` ordering.

The existing `scripts/analyze_blind_legal_move_baseline.py` is therefore a genuinely separate baseline analysis rather than a reconstruction of `solver_default_rank`.

One further caution: that script currently uses the historical `fixed_rank` as the tie-breaker for equal legal counts. The historical fixed ranking is precisely the ranking affected by the shared-memo/order-contamination audit, so it cannot establish that an *independent* probe contributes useful information inside legal-count ties.

## Highest-priority follow-up

Before collecting more parents, evaluate this clean hierarchy on the already labelled seven LOSS parents:

1. candidate-generation order (`solver_default_rank` in the saved table);
2. deterministic `legal_move_count` order with an explicit state/move tie-break;
3. the same legal-count primary key, but use the **independent fresh-solver probe score only within equal-legal-count groups**.

The decisive comparison is 2 vs 3. It asks a narrower question than the failed wholesale reranking: does the independent probe contain residual information after the strong, cheap structural feature `legal_move_count` has already been fixed? If 3 does not improve over 2, `memo_used` should be deprioritized. If it does, the probe may still be useful as a secondary tie-break signal even though using it as the primary ranking is harmful.
