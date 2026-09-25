# C-K10-asc reserve: retired before unblinding

Status: **do not execute the frozen reserve cohort for a confirmatory solver-speedup claim.**

This decision is made without inspecting or generating reserve outcomes.

## Why the reserve is no longer informative

The endpoint correction in `staged_ck10_reserve_prereg_amendment.md` fixed a real problem: a solver-speedup claim must be evaluated with the native parent solver and its shared memo, not by summing fresh child solves. That correction remains valid.

However, the already-completed non-reserve mechanism analysis in `docs/10X10_LOSS_PROOF_COST_ANALYSIS.md` changes the expected value of running C-K10-asc itself:

- native root ordering already selects a LOSS at median **1.12x** the cheapest-LOSS oracle;
- native selected-LOSS median cost-rank is **2.0**;
- 10k `memo_used` selects median cost-rank **11.5** and median **1.79x** oracle;
- LOSS-conditional proof cost correlates much more strongly with `legal_move_count` than 10k `memo_used` (pooled-rank Spearman about **+0.65 vs +0.34**);
- the apparent parent-benchmark failure is reproduced to about 2% by entered-prefix independent exact costs, so no missing shared-memo mechanism is needed;
- the analysis explicitly recommends not spending a confirmatory parent benchmark on root-order tweaks and instead moving below root.

C-K10-asc still uses 10k `memo_used` as the ordering key inside its selected head. Restricting that key to the ten lowest-count children may reduce the damage, but the existing data provide no positive confirmatory rationale strong enough to justify consuming the untouched reserve. In particular, the natural count-primary/memo-tie-break candidate changes only 1/12 in-sample selections; C-K10-asc is a more invasive reordering than that candidate.

## Consequence

The reserve parents remain untouched and may be reused for a future hypothesis that is motivated independently of their outcomes. The C-K10-asc protocol and its corrected endpoint are retained as historical preregistration artifacts, but are superseded operationally by this retirement note.

Do not report C-K10-asc as failed or successful: it was **retired pre-data**, not tested.

## Priority after retirement

Use compute and engineering effort below the root, where the existing analysis says the remaining leverage lives: memo lookup/hit/put instrumentation, proof/certificate reuse, and deeper-layer ordering. Root ordering should only be reopened if a new cheap feature demonstrates residual LOSS-proof-cost information beyond `legal_move_count` on non-reserve data.
