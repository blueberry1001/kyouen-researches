# Preregistration: F-E R-external 4-stone holdout

Date: 2026-09-22
Branch: `analysis/f-e-r-external-holdout`
Baseline: `origin/main=224f0da`
Status: **FROZEN BEFORE ANY HOLDOUT EXACT LABEL**

Related prior work (direction source only; not reused as holdout data):

- `origin/analysis/f-e-exact-label-test` (`4ea7025`, `8aa6569`)
- Within-R exact label test on the 70 four-stone subsets of the 8-stone LOSS root
  `R = {90,61,2,73,69,66,13,91}` on the 10×10 board
- Observed within-R association (LOSS side has **higher** Σd):
  - LOSS n=12 mean Σd=8732.833 range=[8033,9472]
  - WIN n=58 mean Σd=8285.276 range=[7252,9263]
  - AUC=0.759339, rank-biserial=0.518678, Hedges g=0.957284
  - exact conditional random-label p=0.001573310019 (descriptive within-R only)

## 1. Objective

Determine whether the four-stone reversal

> higher Σd → more likely LOSS

observed **inside** the selected 8-stone LOSS root R also appears on **R-external**
four-stone states, or whether it is R-specific.

This is an external-validity holdout, not a re-fit of the within-R statistic.

## 2. Frozen definitions

### 2.1 Geometry

- Board: 10×10, point id `p = y*10 + x`.
- Dangerous quadruple: four distinct points whose integer matrix
  `[x²+y², x, y, 1]` has determinant 0 (concyclic or collinear).
- `d(p)`: number of dangerous quadruples containing point `p`.
- State Σd: `sum(d(p) for p in state)`.

Regression anchors from `f_e_exact_label_test.py` must hold when `d` is recomputed:

```text
d(90)=1515 d(61)=2289 d(2)=1927 d(73)=2395
d(69)=2080 d(66)=2499 d(13)=2289 d(91)=1730
```

### 2.2 D4 canonical key

Same dictionary-min bit-orbit reduction as `scripts/analysis/cache_core_classify.py`:

```text
k=0:(x,y) k=1:(N-1-x,y) k=2:(x,N-1-y) k=3:(N-1-x,N-1-y)
k=4:(y,x) k=5:(N-1-y,x) k=6:(y,N-1-x) k=7:(N-1-y,N-1-x)
canonical = sorted points of the orbit member with minimal bitmask
```

Both raw coordinate tuple and canonical key are stored in the manifest.

### 2.3 Legal four-stone holdout states

A holdout candidate is a set of four distinct board points such that:

1. **Safe / non-terminal**: the four points themselves are **not** a dangerous
   quadruple (the game has not already ended).
2. **R-external**: the point set is **not** a subset of
   `R = {90,61,2,73,69,66,13,91}`.
3. **Unseen**: its D4 canonical key does not appear in any prior labeled
   outcome source listed in §3.

## 3. Exclusion sources (labels consulted only to exclude, never to sample)

Any canonical key appearing in these sources is ineligible:

1. All four-stone subsets of R (70 raw subsets, reduced by D4).
2. `results/10x10/*-stone-subsets-of-medium-loss.csv` and sibling result CSVs
   on `origin/main` at the baseline commit.
3. `scratch/kyouen-local-handoff/outcome-cache.json` keys (research-properties
   worktree / main-handoff extract), any stone count.
4. Four-stone states embedded in git history under `results/`, `artifacts/`,
   `docs/` (comma-separated 4-tuples with ids in 0..99).
5. Known proof states referenced in `docs/10X10_*`.

Sampling code must not read any `outcome` column to build the cohort.

## 4. Universe, strata, sampling rule

### 4.1 Clean universe

All D4-canonical safe R-external four-stone states after §3 exclusions.

### 4.2 Σd strata (geometry only)

Let `{s_i}` be the multiset of Σd over the clean universe.

- Sort `s` ascending.
- **low**: Σd ≤ 33rd percentile of clean-universe Σd
- **middle**: (33rd, 67th] percentile
- **high**: Σd > 67th percentile

Percentile cutpoints are computed once from the clean universe and frozen in
the sampling manifest.

### 4.3 Deterministic sample

- Seed string: `kyouen-10x10-f-e-r-external-holdout-seed-20260922`
- Hash key: `SHA256(seed + ":" + canonical_key)` as hex
- Within each stratum, sort by hash ascending.
- Sample size: **12 states per stratum**, 36 total (confirmatory cohort).
- No post-outcome replacement, dropping, or re-stratification.

### 4.4 Manifest columns

Committed **before** any exact solve:

- `index`, `stratum`, `canonical_key`, `raw_state`, `sigma_d`,
  `hash`, `seed`, `baseline_commit`

## 5. Solver protocol (frozen)

| Item | Frozen value |
|---|---|
| Solver family | 10×10 exact FlatMemo81 searcher (same D4 canonical + forbidden-completion logic as `kyouen_solver_10_root.cpp`) |
| Source | `cpp/solvers/kyouen_solver_10_f_e_plain.cpp` (plain-state CLI wrapper over Solver10) |
| Binary | `cpp/solvers/kyouen_solver_10_f_e_plain.exe` built from the source above |
| memo_power | 28 (table size 2^28; solver raises over-load at 80% occupancy) |
| budget | unbounded exact search (no visit cap) |
| timeout | 600 seconds per state |
| memo | **fresh process per state**; no outcome-cache load; no cross-state memo reuse |
| inputs | one plain state per line: `a,b,c,d` raw coordinates |
| stdout row | `state,outcome,visited,memo_used,seconds` where outcome ∈ {WIN,LOSS,TABLE_FULL} |
| accepted outcomes | `WIN`, `LOSS` only for analysis |
| non-exact outcomes | `TABLE_FULL`, `TIMEOUT`, `ERROR` recorded but excluded from primary association stats; counted in the inconclusive rule |

Note: the historical four-stone subset classification used the kyoenc4 binary with
`shrink=3, load=80`. This holdout freezes the FlatMemo81 exact searcher instead,
because that binary is the one available at baseline for independent R-external
states. Direction comparison to R-internal F-E is about Σd–outcome association,
not about solver visited counts.

Solver commit / binary SHA-256 is recorded in the run manifest after the
preregistration commit and before execution is treated as complete.

## 6. Primary endpoints

Computed **only after** the frozen 36-state manifest exists and all solves that
can finish under §5 have been attempted. No mid-run rule changes.

Among states with exact `WIN`/`LOSS` labels:

1. mean and median Σd by outcome
2. AUC = P(Σd_LOSS > Σd_WIN) + 0.5 P(tie)
3. rank-biserial = 2·AUC − 1
4. `P(LOSS | high Σd stratum)` vs `P(LOSS | low Σd stratum)`
5. exact/permutation random-label statistic on the observed LOSS count
   (descriptive; sample is stratified by Σd so this is **not** a population
   p-value for unstratified four-stone states)

### Direction comparison to R-internal F-E

| Quantity | R-internal reference | Holdout decision use |
|---|---|---|
| AUC | 0.759 (LOSS higher Σd) | compare sign / magnitude only |
| rank-biserial | +0.519 | same |
| mean(LOSS)−mean(WIN) | +447.6 | same |
| P(LOSS\|high)−P(LOSS\|low) | not preregistered in R-internal script; report holdout value | primary stratified contrast |

No re-tuning of the R-internal statistic after seeing holdout outcomes.

## 7. Decision rules (frozen)

Let `L` = number of exact LOSS labels in the 36-state cohort.

1. **Reversal supported outside R** if **all** hold:
   - `L ≥ 3`
   - AUC > 0.5
   - `P(LOSS | high) ≥ P(LOSS | low)`
   - mean(Σd|LOSS) > mean(Σd|WIN)

2. **Reversal not supported outside R** if `L ≥ 3` and at least one of:
   - AUC < 0.5
   - `P(LOSS | high) < P(LOSS | low)`
   - mean(Σd|LOSS) ≤ mean(Σd|WIN)
   and the observed direction is not exclusively explained by zero LOSS in
   both low and high strata (i.e. not a pure sparse-label artifact where all
   LOSS sit in middle).

3. **Inconclusive** otherwise, including:
   - `L < 3`
   - more than 20% of frozen states non-exact
   - all exact LOSS confined to a single stratum **and** both extreme strata
     have 0 LOSS

Report both the decision label and the raw endpoints. Do not promote a
directionally ambiguous inconclusive result as a discovery.

## 8. Stopping rule

- Attempt all 36 frozen states once under §5.
- Do not add replacement states based on observed labels.
- A later larger cohort requires a **new** PREREG + new seed; it must not
  reuse this manifest’s outcomes to alter sampling.

## 9. Deliverables

1. This PREREG + sampling script + frozen manifest (pre-label commit).
2. Exact outcomes CSV + solver run manifest (post-solve commit).
3. Analysis script + summary JSON comparing holdout endpoints to R-internal F-E.
4. Optional findings update only if §7 yields supported / not-supported /
   clearly inconclusive with a concrete next design.

## 10. Worktree / branch safety

- Operate only on `analysis/f-e-r-external-holdout`.
- Do not modify `main` or other agents’ branches.
- Integration to main is left to the orchestrator.
