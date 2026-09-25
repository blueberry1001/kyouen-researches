# F-E early-side R-external retrospective check

Baseline: `origin/main=224f0da`
Branch: `analysis/f-e-early-r-external-retrospective`

## Result

Without running any new solver jobs, the already-labeled historical 3-stone
states in `results/10x10/search-cost-outcomes.csv` were reanalyzed after:

- restricting to 3-stone states,
- excluding every state that is a subset of the 8-stone root
  `R={90,61,2,73,69,66,13,91}`,
- D4-canonical deduplication,
- recomputing `d(p)` directly from the 10x10 geometry.

This leaves **480 unique R-external 3-stone states: 6 LOSS / 474 WIN**.

| metric | value |
|---|---:|
| mean Sigma d, LOSS | **5537.333** |
| mean Sigma d, WIN | **6195.460** |
| LOSS-WIN mean difference | **-658.127** |
| AUC, lower Sigma d predicting LOSS | **0.900141** |
| rank-biserial | **+0.800281** |
| exact lower-tail random-label p | **3.87447e-5** |

All six R-external LOSS states lie toward the low-Sigma-d side. Thus the
**3-stone early direction (lower Sigma d -> LOSS) is also present outside R**
in historical data, and it is directionally opposite to the independently
confirmed 4-stone R-external holdout (higher Sigma d -> LOSS).

## Interpretation boundary

This is strong **retrospective external evidence**, but it is not a clean
confirmatory population holdout:

- the 480 states were collected by several targeted historical campaigns;
- they are not a uniform/random sample of all canonical 3-stone states;
- some campaigns deliberately focused on hard or structurally interesting
  parents;
- therefore the exact random-label p-value is descriptive conditional on this
  fixed selected set, not a population-level significance claim.

The important point is that no new solver selection was made using Sigma d:
the labels predate F-E, and the states are outside R.

## Consequence

The next expensive experiment should no longer ask merely whether the
3-stone sign exists outside R. The retrospective data already says it does.

The clean confirmatory target is now the **sign change itself** under a fresh
sampling frame:

- prospective R-external 3-stone cohort, stratified by Sigma d and selected
  before labels;
- primary direction: lower Sigma d -> more LOSS;
- compare its sign with the already preregistered R-external 4-stone result;
- 2-stone can be a separate secondary cohort because exact solves are likely
  to be more expensive.

Reproduction:

```bash
python scripts/analysis/f_e_early_r_external_retrospective.py
```
