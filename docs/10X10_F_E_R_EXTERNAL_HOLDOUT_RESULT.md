# F-E R-external 4-stone holdout result

> **2026-09-29 memo-width revalidation:** the historical FlatMemo81 implementation
> truncated 6 high key bits on 10x10. All **36/36 frozen states were re-solved**
> with the corrected full-width key and all WIN/LOSS labels were unchanged.
> The preregistered decision below therefore remains valid. See
> [10X10_F_E_R_EXTERNAL_HOLDOUT_MEMO_REVALIDATION.md](10X10_F_E_R_EXTERNAL_HOLDOUT_MEMO_REVALIDATION.md).

Baseline: `224f0da`
Preregister commit: `4249e73` (sample frozen before any holdout label)
Branch: `analysis/f-e-r-external-holdout`

## Decision (preregistered)

**`reversal_supported_outside_R`**

All three frozen conditions hold:

- `L = 10 ≥ 3`
- AUC `0.811538 > 0.5`
- `P(LOSS | high Σd) = 0.5 ≥ P(LOSS | low Σd) = 0.0`
- mean(Σd|LOSS) `9118.100 > mean(Σd|WIN) 8497.769`

## Frozen cohort

| Item | Value |
|---|---|
| Clean R-external safe canonical 4-stone universe | 460,321 |
| Σd tertiles | q33=8538, q67=8974 |
| Sample | 12 low + 12 middle + 12 high = 36 |
| Exact outcomes | 36/36 (no TABLE_FULL / TIMEOUT / ERROR) |
| Solver | FlatMemo81, memo_power=28, fresh process, timeout=600s |

## Endpoints

| Metric | Holdout (R-external) | R-internal F-E reference |
|---|---:|---:|
| LOSS n | 10 | 12 |
| WIN n | 26 | 58 |
| mean Σd LOSS | 9118.100 | 8732.833 |
| mean Σd WIN | 8497.769 | 8285.276 |
| mean diff (LOSS−WIN) | **+620.331** | +447.557 |
| median Σd LOSS | 9161.5 | — |
| median Σd WIN | 8569.0 | — |
| AUC | **0.811538** | 0.759339 |
| rank-biserial | **+0.623077** | +0.518678 |
| P(LOSS\|low) | 0.00 (0/12) | (not preregistered) |
| P(LOSS\|middle) | 0.333 (4/12) | (not preregistered) |
| P(LOSS\|high) | 0.500 (6/12) | (not preregistered) |
| P(LOSS\|high)−P(LOSS\|low) | **+0.50** | — |
| exact random-label p (LOSS Σd-sum upper) | 0.0008535 (descriptive) | 0.001573 within-R |

Direction is **the same** as R-internal F-E: higher Σd → more LOSS at four stones.
Holdout separation is numerically stronger (AUC 0.81 vs 0.76), so the reversal is
not an artifact of the selected 8-stone root R.

## Stratum × outcome

| Stratum | LOSS | WIN | n |
|---|---:|---:|---:|
| low | 0 | 12 | 12 |
| middle | 4 | 8 | 12 |
| high | 6 | 6 | 12 |

All 12 low-Σd states are WIN. LOSS mass is concentrated in middle/high.

## Protocol notes

1. Sampling used geometry only (Σd strata + SHA-256 hash rank with frozen seed).
   Outcome labels were used only to **exclude** previously observed canonical keys
   (24,072 keys).
2. First solve attempt wrote a CSV whose state field contained commas and was
   mis-parsed. That partial file was discarded and all 36 states were re-solved
   after quoting the state field. No frozen choice changed (same 36 states).
3. Random-label p is descriptive only: the cohort is stratified by Σd, so it is
   not an unstratified population significance claim.
4. R-internal statistics were not refit after seeing holdout outcomes.

## Implication

F-E’s four-stone reversal (“higher dangerous-quadruple load → more LOSS”) holds
on R-external safe four-stone states. The early-game (2–3 stone) opposite trend
is therefore not solely a property of the medium LOSS root’s subset lattice.

## Artifacts

- `results/10x10/f-e-r-external-holdout/sampling_manifest.csv`
- `results/10x10/f-e-r-external-holdout/exact_outcomes.csv`
- `results/10x10/f-e-r-external-holdout/holdout_summary.json`
- `results/10x10/f-e-r-external-holdout/solver_run_manifest.json`
- `docs/10X10_F_E_R_EXTERNAL_HOLDOUT_PREREG.md`
