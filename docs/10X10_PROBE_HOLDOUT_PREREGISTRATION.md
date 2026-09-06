# 10x10 fresh-memo probe holdout preregistration

Base branch: `audit-blind-probe-and-move-ordering`
Base SHA: `9d2e4e6987e89c88b7f9cb591f1f7824ea806171`

This file fixes the confirmatory design **before inspecting outcomes of the new holdout parents**.

## Prior exploratory data excluded

The following parents were used to discover/correct the probe direction and are excluded from confirmatory analysis:

- `2,9,33`
- `4,9,33`
- `9,12,33`
- `9,19,33`
- `9,23,33`
- `0,31,36`
- `0,36,44`

Any additional parent explicitly used in `docs/10X10_CORRECTED_PROBE_DIRECTION_EXPLORATORY.md` or `scripts/analyze_corrected_probe_auc.py` is also excluded.

## Holdout-parent selection

Use 3-stone 10x10 parents only. From the available classified LOSS-parent pool after exclusions, D4-canonicalize parents, deduplicate, sort lexicographically by canonical triple, and take the first 20 eligible parents. If fewer than 20 eligible LOSS parents are available, use every eligible parent; the confirmatory set must not be enlarged or subset after probe outcomes are inspected.

The selection script/output must be committed before outcome analysis. Parent identity may be known for scheduling work; child-level LOSS/WIN outcomes must not be used to alter the parent set or ranking rule.

## Probe protocol

Primary budget: **1,000,000 visited states per child**.

Each candidate child is probed in a fresh solver process / fresh `Solver` instance. No transposition table, cumulative timer, or solver state may be shared between candidates.

Secondary budgets, if compute permits: 10,000 and 100,000 visited states per child. They are exploratory/secondary and do not replace the 1M primary result.

## Preregistered ranking

For each parent's candidate children:

1. child for which the probe proves LOSS: first;
2. otherwise unresolved children: ascending independent `memo_used`;
3. child for which the probe proves WIN: last.

Tie-break: ascending move/cell index.

For unresolved children that all hit the same visited budget, ascending `memo_used` is equivalent to descending `visited - memo_used`; `visited-memo` must not be interpreted as a memo-hit count.

The ranking direction must not be reversed after observing holdout outcomes.

## Comparators

Report the same children under:

- preregistered corrected ranking above;
- independent-memo descending ranking;
- solver/default child order;
- reverse default/file order;
- random permutation baseline.

## Primary endpoint

For each LOSS parent, measure the rank of the first exact-LOSS child under the preregistered corrected ranking.

For a parent with `m` candidates and `l` LOSS children, the random-permutation reference is

`E[R] = (m+1)/(l+1)`

and

`P(R <= r) = 1 - C(m-r,l)/C(m,l)`.

Compute the exact random median from this distribution rather than simulation.

Across parents classify corrected rank relative to exact random median as better / tie / worse. The primary directional test is a **one-sided exact sign test**, excluding ties, for the preregistered hypothesis that corrected ranking is better than random.

Always report effect sizes and the individual parent ranks, regardless of p-value.

## Secondary endpoint

For each parent containing at least one LOSS and one WIN child, calculate candidate-level AUC using score `-memo_used` for unresolved candidates, respecting proved-LOSS/proved-WIN ordering. Report individual-parent AUCs plus their mean and median. A pooled-across-parent AUC is secondary only because LOSS density differs by parent.

## Diagnostic instrumentation

Instrumentation such as `visited_by_depth`, `memo_lookup_by_depth`, `memo_hit_by_depth`, `memo_put_by_depth`, generated-child count, and proof termination depth may be collected. It is diagnostic only and must not change the primary ranking, parent set, budget, or endpoint for this holdout.

## Interpretation rule

- A favorable result supports the corrected fresh-memo direction on a genuinely new holdout.
- A null or adverse result falsifies/weakens that hypothesis; do not rescue it by changing direction, budget, parent subset, or primary statistic on the same holdout.
- Any new heuristic discovered from this holdout becomes exploratory and requires another future holdout.

## 9x9 scope guard

The old audit-branch statement `O=0` / pair-sum equals true mobility is not part of this experiment and must not be reused. It resulted from the filtered `response_sets` definition documented in `docs/9X9_PAIRSUM_METRIC_DEFINITION_CORRECTION.md`. The intended 9x9 raw-pair analysis is the main-branch decomposition `raw_pair = T + E + O`.
