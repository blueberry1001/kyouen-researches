# 10x10 clean holdout V2: 10k probe cost preregistration

Base evidence branch: `10x10-clean-holdout-v2` at `451ece8674e167d9a3dec5dbc29c16518b8ab6fb`.

This document fixes the analysis before any V2 fresh-10k probe result is inspected. Existing 1M probe and exact outcomes are already known and are used only to define comparison metrics, not to tune the 10k rule.

## Fixed sample and rule

- Sample: the existing 12 primary V2 parents and exactly 1,136 child tasks.
- No parent or child may be added, removed, replaced, or reordered after seeing 10k outcomes.
- Probe budget: 10,000 visited per child.
- Fresh solver/process per child; no memo sharing across children.
- Ranking rule: ascending `memo`; ties are broken by the existing deterministic task order `(batch, batch_position, state)`.
- Primary cost includes the full cost of probing every child of a parent before exact search begins.

The 10k raw probe file must first be committed complete. Exact labels are joined only after all 1,136 probe rows are present.

## Integrity gates

Analysis aborts unless all of the following hold:

1. exactly 1,136 unique states;
2. exactly 12 parents;
3. state set equals `results/10x10/clean-holdout-v2/exact_outcomes.csv` exactly;
4. every row has a successful probe outcome and a nonnegative finite `seconds` value;
5. no duplicate `(parent,state)` pair;
6. parent membership agrees between probe and exact files.

Any deviation is reported as a protocol failure rather than repaired post hoc.

## Primary estimand: end-to-end first-LOSS cost

For each parent, compare:

- **File order baseline:** cumulative exact `seconds` in fixed task order until the first exact LOSS.
- **10k memo strategy:** sum of all 10k probe `seconds` for that parent plus cumulative exact `seconds` in ascending-memo order until the first exact LOSS.

Primary ratio:

`R = total_cost_10k_memo / total_cost_file_order`

Primary aggregate summaries:

- median R;
- geometric mean R;
- number of parents with R < 1, R = 1, R > 1;
- aggregate seconds ratio `sum(total_cost_10k_memo) / sum(total_cost_file_order)`.

### Decision rule

The 10k probe-all strategy is called practically successful only if both hold:

1. median R < 1;
2. at least 7 of 12 parents have R < 1.

This is deliberately stricter than merely predicting LOSS well.

If median R is near 1 but the rank signal remains strong, 100k is a reasonable follow-up. If median R is clearly above 1, probe-all is considered the wrong architecture and the next experiment should reduce the number of probed children rather than increase the per-child budget.

## Secondary ranking metrics

For each parent report:

- number of children and LOSS children;
- first-LOSS rank under 10k memo order;
- normalized first-LOSS rank;
- AUC for lower memo predicting LOSS;
- top-1 outcome;
- number of LOSS children in top 5.

Across parents report first-LOSS rank list, sum, median, maximum, mean AUC and median AUC.

## Existing 1M comparison

The same state set may be joined to `independent_probe_1000000.csv` after the 10k primary calculation. Report:

- 10k versus 1M first-LOSS rank by parent;
- 10k versus 1M AUC;
- probe-time ratio;
- total end-to-end cost ratio.

This comparison is secondary; the primary question is whether 10k beats file order after paying its own probe cost.

## Exploratory work allowed only after primary output is frozen

Candidate-subset or staged strategies (for example top K children only) may be simulated only after the complete 10k primary table and summary are saved. Such results must be labelled exploratory and must not replace the preregistered 10k-all result.
