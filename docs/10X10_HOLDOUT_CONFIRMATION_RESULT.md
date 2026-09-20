# 10x10 fresh-memo probe: holdout confirmation result

Date: 2026-09-07
Branch: `blind-probe-holdout-validation`
Preregistration: `docs/10X10_PROBE_HOLDOUT_PREREGISTRATION.md` (base `9d2e4e6`)
Frozen parent set: `results/10x10/holdout-parent-selection-preregistered.csv` (11 parents)

## What was tested

Preregistered ranking on fresh-solver 1M probes per child (shrink 3, load 80):

1. probe-proved LOSS first;
2. unresolved children by ascending independent `memo_used`;
3. probe-proved WIN last;
4. tie-break ascending move/cell index.

Comparators: memo-desc, solver-default order, reverse file order, exact
random-permutation null. Primary budget 1M fixed before outcomes. No
direction/budget/parent/endpoint changes after outcomes.

## Execution

- 1020/1020 probe rows collected (11 parents × all batches), protocol manifest
  binds solver binary + sources + exact ordered task set
  (`independent_probe_1000000.protocol.json`).
- 1020/1020 exact outcomes (shrink 0, load 90, unbounded, 0 failures,
  0 timeouts), merged into 55 analyzer-compatible batch files.
- Input verification passes (1020 tasks / 1020 probe rows).
- **Interpretation correction (audit `3d87e8b`)**: The 11 parents were unused for the probe-ranking experiment, but each originated from pre-existing proof families (`two-stone-90-61-child-proof.csv` and `two-stone-90-66-child-proof.csv`) that already supplied at least one exact LOSS child (in eight cases a literal direct child; in three cases a D4-equivalent direct child). Therefore this experiment is a prospective ranking replication on previously certified WIN parents, not a fully child-outcome-blind holdout. See `docs/10X10_HOLDOUT_PREKNOWN_LOSS_CHILD_AUDIT.md` and `results/10x10/exhaustive_preknown_loss_audit.json`.

## Primary result: hypothesis CONFIRMED on the holdout

All 11 frozen holdout parents contain exact LOSS children (counts 1–82).
First-LOSS ranks under the preregistered rule:

| parent | m | l | corrected | memo-desc | solver | reverse | E[R] | exact median |
|---|---|---|---|---|---|---|---|---|
| 0,36,50 | 92 | 17 | 1 | 59 | 13 | 14 | 5.17 | 4 |
| 9,33,54 | 92 | 82 | 1 | 1 | 1 | 1 | 1.12 | 1 |
| 0,1,13 | 92 | 4 | 1 | 43 | 9 | 17 | 18.6 | 15 |
| 0,7,31 | 92 | 12 | 1 | 13 | 15 | 3 | 7.15 | 5 |
| 0,17,31 | 92 | 1 | 1 | 92 | 33 | 60 | 46.5 | 46 |
| 0,13,34 | 92 | 22 | 1 | 3 | 13 | 6 | 4.04 | 3 |
| 0,13,44 | 92 | 16 | 1 | 8 | 13 | 6 | 5.47 | 4 |
| 0,2,13 | 94 | 2 | 6 | 79 | 50 | 17 | 31.67 | 28 |
| 0,3,13 | 94 | 1 | 1 | 94 | 78 | 17 | 47.5 | 47 |
| 0,10,13 | 94 | 5 | 1 | 43 | 1 | 17 | 15.83 | 12 |
| 0,13,21 | 94 | 11 | 1 | 24 | 10 | 17 | 7.92 | 6 |

- better than exact random median: **10**, tie: **1** (`9,33,54`, l=82/92),
  worse: **0**.
- One-sided exact sign test (ties excluded, preregistered direction):
  **p = 0.00098** (10/10).
- Exact convolution null (primary calibrated comparator, sum of ranks):
  observed **16** vs random-expected **190.97**, one-sided **p = 1.2e-09**.
- Per the preregistered interpretation rule and the null-interpretation note,
  the p-value is a procedure-vs-random-order benchmark on this frozen set
  (randomization over candidate order within fixed parents), not a
  population-generalization probability. The replication effect size above
  (10/11 rank 1, 10 better / 1 tie / 0 worse) is what supports the claim.
- **Sensitivity analysis** (`scripts/audit_and_sensitivity_exhaustive.py`):
  after removing all 33 pre-known LOSS witnesses across the 11 parents,
  9 parents still had remaining LOSS children; the memo-ascending rule
  remained 8 better / 1 tie / 0 worse (sign $p = 0.0039$, mean AUC 0.813).
  This reduces, but does not eliminate, the concern that the primary result
  was driven by pre-existing witnesses.

## Secondary

- Parent AUC (score `-memo`, preregistered order): mean **0.820**, median
  **0.802**, all 11 parents > 0.58 (min 0.582 for `0,13,34`).
- Corrected rank 1 in **10/11**; memo-desc 1/11; solver-default 2/11;
  reverse 1/11. Corrected beats solver-default 9/11, ties 2/11.
- All 1020 probes hit the 1M budget unresolved (no probe proved LOSS/WIN),
  so the outcome-aware tiers were vacuous and the rule reduced to pure
  memo-ascending (= `visited - memo` descending).
- Old `b5172a4` verdict C stays withdrawn; this result does not rescue it —
  it confirms the *corrected opposite-direction* rule on new parents.

## Mechanism status (secondary diagnostic, P5)

`visited - memo` must not be read as a memo-hit count (memo hits skip
`visited`; memoized depths are 9–17 only). Depth-resolved counters
(`visited_by_depth`, memo hits/puts by depth) remain uninstrumented and are
the next diagnostic step. No new heuristic was mined from this holdout.

## 9x9 status (P6/P7)

- Raw/filtered response-set modes separated in `scripts/kyouen9_pairsum.py`
  (+ cached engine), with C++ cross-check regression (`tests/test_pairsum.py`,
  9/9 pass): raw `raw_pair = T + E + O`, pinned O>0/E>0 fixtures, filtered
  E'=O'=0 by construction.
- Main-branch assets (11,378 D4 strict reps, pilot-64, confirmatory/factorial
  designs) untouched; pilot-64 stays excluded from confirmatory samples.

## Artifacts

- Probes: `results/10x10/blind-probe-holdout/independent_probe_1000000.csv`
  + `.protocol.json`; task list `exact_task_list.csv`.
- Exact: 55 `results/10x10/blind_probe_children/exact_<parent>_batch<N>.csv`.
- Analysis: `preregistered_parent_results.csv`, `preregistered_summary.json`,
  `preregistered_exact_random_null.json`, `secondary_diagnostics.json`.
- Runners: `run_probe_holdout_independent.py`, `run_holdout_exact_one.py`,
  `run_holdout_exact_sweep.py`, `merge_holdout_exact.py`;
  analyzers: `analyze_probe_holdout_preregistered.py`,
  `analyze_probe_holdout_exact_null.py`, `verify_probe_holdout_analysis_inputs.py`.

## Next most valuable experiment

1. Second independent holdout (new parents, same frozen rule) to test
   repeatability, ideally with depth-resolved instrumentation from the start.
2. Multi-budget rank stability (10k/100k/1M) on the same frozen set.
3. Move-ordering-inside-exact-search test (node-count savings), separate
   from LOSS-rank prediction.
