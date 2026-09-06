# 10×10 legal-move-count + independent memo tie-break: next fresh holdout preregistration

Date fixed: 2026-09-07
Base commit: `4be5fcf5b3d866f67db5dc179b7095f43c2a540f`

## Scope

This document fixes a confirmatory test for a **future fresh 10×10 holdout only**. Any parent or child whose exact WIN/LOSS outcome was observed before this commit is excluded. In particular, the previously studied seven LOSS parents and any outcomes produced by concurrently running blind experiments before this commit are not eligible.

The purpose is to test a narrower hypothesis suggested by the corrected seven-parent analysis: `independent_memo_used` may be harmful as a global ordering rule, yet still contain residual information **within equal `legal_move_count` groups**.

## Candidate ordering rules

For every eligible parent, enumerate the same legal candidate children once and attach pre-outcome features:

- `legal_move_count`: number of legal replies from the child under the exact 10×10 collinearity/cocircularity rule.
- `independent_memo_used`: memo usage from a fresh Solver probe of that child at the fixed probe budget used for the holdout. A fresh Solver is required for every child; no transposition memo may be shared between candidate probes.
- `state_key`: deterministic serialization of the child state used only as a final tie-break.

Compare exactly these two orders:

1. **baseline**: `(legal_move_count ASC, state_key ASC)`
2. **memo tie-break**: `(legal_move_count ASC, independent_memo_used ASC, state_key ASC)`

`independent_memo_used` must never reorder candidates with different `legal_move_count`.

## Eligible analysis parents

A parent enters the primary matched analysis only if all of the following hold:

1. It belongs to a newly selected holdout population fixed without consulting exact child outcomes.
2. No exact outcome for the parent or any candidate child was inspected before the holdout manifest was frozen.
3. Exact solving later establishes that at least one candidate child is LOSS.
4. The two pre-outcome orderings differ somewhere in the candidate list.

Criterion 4 depends only on pre-outcome ordering features and therefore may be fixed before exact outcomes are revealed.

## Per-parent endpoint

After the complete eligible holdout is exact-solved, define

- `R_base`: 1-based rank of the first LOSS child under the baseline order.
- `R_memo`: 1-based rank of the first LOSS child under the memo tie-break order.
- `D = R_memo - R_base`.

Interpretation:

- `D < 0`: memo tie-break improves first-LOSS discovery.
- `D = 0`: no change.
- `D > 0`: memo tie-break worsens first-LOSS discovery.

Parents with `D = 0` remain in descriptive summaries but are omitted from the sign-test denominator.

## Primary hypothesis test

Primary null hypothesis:

`P(D < 0 | D != 0) = 1/2`.

Primary alternative:

`P(D < 0 | D != 0) > 1/2`.

Use a **one-sided exact sign test** at `alpha = 0.05` over nonzero `D` parents. This direction is fixed before the future holdout outcomes are observed because the scientific claim being tested is improvement, not merely any difference.

Report additionally, without changing the primary decision rule:

- number of wins (`D < 0`), ties, and losses (`D > 0`),
- median `D`,
- `sum(D)`,
- median `R_base` and median `R_memo`,
- two-sided exact sign-test p-value.

## Success criterion

The narrow tie-break hypothesis is considered supported only if all three conditions hold:

1. the one-sided exact sign-test p-value is `< 0.05`;
2. wins exceed losses among nonzero-D parents;
3. `sum(D) < 0` over all analyzed LOSS parents.

Otherwise the confirmatory result is recorded as unsupported, even if a secondary summary looks favorable.

## Holdout freezing requirements

Before any exact child outcome from the new population is inspected, save and commit a manifest containing at least:

- parent-selection algorithm and seed,
- selected ordered parent list,
- candidate child list for each parent,
- probe budget and solver/source commit,
- deterministic hash of the full ordered task list,
- exclusion list of all previously observed parents/children,
- SHA-256 of all analysis-input files.

The exact solver may run only after this manifest is frozen. If exact outcomes already exist for a candidate set before this document or its corresponding manifest is committed, that set cannot be used as the confirmatory holdout defined here.

## Probe integrity

Each child probe must use a newly constructed Solver with empty memo state. No result from an earlier candidate probe may affect `independent_memo_used` for a later candidate. Probe execution order may therefore not influence the feature value.

The exact solver used to label WIN/LOSS may share memo if that is already verified not to change exact outcomes, but any order-dependent exploration statistics from such a run are not primary data for this experiment.

## Prohibited changes after outcome reveal

Do not, after any exact outcome in the frozen holdout has been inspected:

- change the ordering keys or their directions;
- replace `memo_used` by another probe statistic;
- change the probe budget;
- remove inconvenient parents except for a pre-specified integrity failure;
- redefine the sign-test denominator based on outcome magnitude;
- change one-sided to two-sided as the primary test;
- add legal-count weights or learned coefficients and call them part of this test.

Any such idea becomes a new exploratory hypothesis and requires another fresh holdout.

## Relation to earlier results

The seven previously known LOSS parents are exploratory evidence only. They suggested that unrestricted memo ordering is poor, while restricting memo to equal-legal-count ties may retain weak residual signal. They are excluded from this confirmatory population and may not contribute to its p-value.
