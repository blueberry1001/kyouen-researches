# Frozen reserve validation: C-K10-asc staged search

Status: preregistered before inspecting or generating any exact/probe outcomes for reserve parents ranks 13-24.

## Motivation

The exploratory primary-12 analysis found a strong staged-search candidate:

1. rank all legal 4-stone children by cheap geometric `legal_move_count` ascending;
2. retain the first K=10 (ties by the existing frozen child/file order);
3. run an independent fresh-process 10,000-node probe only for those 10 children;
4. sort those 10 by `(memo_used ascending, move ascending)`;
5. exact-solve that sorted head until the first LOSS;
6. if the head contains no LOSS, continue exact solving the remaining children in their original frozen child/file order, excluding the already-tested head.

This rule is named `C-K10-asc`. K, direction, tie-breaking, probe budget, fallback order, and endpoints below are frozen here and must not be changed after reserve results are observed.

## Holdout cohort

Use only the pre-sampled reserve half of `holdout_v2_parents_extended24.csv`, ranks 13-24:

- `12,21,58`
- `0,19,95`
- `2,11,61`
- `1,27,61`
- `1,68,74`
- `0,7,67`
- `1,12,80`
- `2,43,60`
- `23,37,45`
- `1,6,51`
- `12,13,67`
- `12,25,71`

Do not substitute parents, remove difficult parents, or add parents after any reserve result is seen.

## Comparator

Baseline is fresh-process exact search of the same legal children in the existing deterministic frozen child/file order, stopping at the first LOSS. Probe time is zero for the baseline.

For `C-K10-asc`, total cost is:

`sum(10k probe wall time for selected 10) + sum(fresh exact wall time until first LOSS in staged order)`.

Also record visited-node totals separately so wall-clock conclusions can be checked against machine noise.

## Primary endpoint

Per parent compute

`ratio = staged_total_seconds / baseline_exact_seconds`.

Confirmatory success requires all of:

1. median ratio across the 12 reserve parents < 0.75;
2. at least 9/12 parents have ratio < 1.0;
3. aggregate staged seconds / aggregate baseline seconds < 0.75;
4. no reserve parent has ratio > 2.0.

These thresholds are intentionally much weaker than the exploratory primary-12 effect and are frozen before reserve outcomes are inspected.

## Secondary diagnostics

Report, without changing the primary decision:

- first-LOSS position in baseline and staged order;
- whether the selected geometric top-10 contains at least one LOSS;
- first-LOSS position within the probed head when applicable;
- 10k `memo_used` values and ordering gaps;
- probe seconds, exact seconds, and visited nodes separately;
- median and aggregate ratios versus the exploratory all-child 10k strategy if that comparator is later run on the reserve cohort.

## Failure interpretation

- If criterion 1 or 2 fails, treat the primary-12 C-K10-asc result as insufficiently general and do not tune K/direction on these same reserve parents.
- If only criterion 3 fails, inspect whether a small number of expensive parents dominate aggregate time, but do not modify the frozen rule and call it confirmatory.
- If criterion 4 fails, treat the strategy as unsafe for deployment even if the median is favorable.
- Any revised rule after this test requires another untouched cohort.
