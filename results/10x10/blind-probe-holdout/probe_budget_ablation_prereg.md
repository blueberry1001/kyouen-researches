# Probe-budget ablation preregistration

This document freezes the next retrospective budget-ablation experiment on the existing 11-parent / 1020-child independent holdout. It does **not** constitute another independent generalization test because the endpoint `K=6` was selected after inspecting the 1M-probe holdout.

## Frozen primary endpoint

For each parent, sort children exactly as in `scripts/analyze_holdout_head_recall.py`, using ascending `memo_used` and the same deterministic tie breaking. The primary endpoint is:

> Does the first `K=6` children contain at least one exact LOSS child?

Report both the number of parents hit out of 11 and the per-parent first-LOSS rank. Do not tune K after seeing lower-budget results.

## Stage 1: 10k probe on all existing holdout children

Use the same task list and runner as the recorded 1M protocol, changing only the probe budgets and output path:

```bash
python3 scripts/run_10x10_probe_classify.py \
  --tasks results/10x10/blind-probe-holdout/independent_holdout_tasks.txt \
  --out results/10x10/blind-probe-holdout/independent_probe_10000.csv \
  --probe-budget 10000 \
  --timeout-fallback-budget 10000 \
  --progress-every 100
```

This is 1020 * 10,000 = 10.2M maximum probe nodes, 1% of the 1M-per-child experiment's nominal 1.02B-node budget.

### Stopping rule

- If 10k achieves top-6 LOSS hit on all 11/11 parents, stop budget ablation on this cohort. Do **not** run a full 100k sweep merely to improve retrospective curves. Freeze `(budget=10k, K=6)` for the next genuinely new parent cohort.
- If one or more parents fail top-6 LOSS hit at 10k, proceed to Stage 2 only for diagnostic purposes.

## Stage 2: targeted 100k diagnosis of 10k failures

Run 100k only on children of parents that failed the frozen top-6 endpoint at 10k. This stage asks whether the failure is simply insufficient probe depth or a ranking instability that remains at larger budgets.

This selection uses exact labels and therefore is **retrospective diagnostic only**; it is not a deployable adaptive probing rule. Do not claim that a solver can know which parents require 100k at runtime from this experiment.

If a deployable adaptive budget rule is pursued later, preregister an unlabeled trigger (for example a stability or score-margin criterion) and validate it on fresh parents.

## Secondary diagnostics (non-gating)

- top-6 set overlap with the 1M ranking;
- first-LOSS rank at 10k / 100k / 1M;
- rank-6 boundary ties in `memo_used`;
- total `probe_nodes` actually consumed.

These are explanatory only. They must not alter `K=6` or the Stage-1 success criterion.

## Interpretation

Success at 10k on these 11 parents establishes only that the previously observed head-recall phenomenon survives a 100x lower probe budget on the same labeled cohort. The next confirmation must use a new independent cohort with both `K=6` and the chosen probe budget fixed in advance.
