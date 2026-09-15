# 8×8 O-stratum independent replication — preregistration draft

Status: DRAFT FOR PRE-OUTCOME FREEZE  
Purpose: independent replication of the structural O-stratum pattern discovered in the completed 9×9 factorial experiment.

## 1. Background

The completed 9×9 factorial experiment showed:

- E×O interaction on shared parents was essentially zero.
- The apparent O-effect reversal was driven mainly by structural membership composition.
- In the pre-outcome-defined 9×9 unobserved holdout:
  - O0-only: ΔLOSS ≈ +0.0912
  - O-overlap: ΔLOSS ≈ -0.0143
- The 9×9 O populations are now fully observed, so they cannot be reused for a new confirmatory test.

This 8×8 experiment is a new-board-size replication. No 8×8 outcomes may be inspected before the population, strata, endpoints, and success criteria below are frozen.

## 2. Score definitions

For every legal candidate move from a safe 4-stone parent:

- T = number of genuinely newly lost safe responses
- E = re-counting of already-dangerous responses
- O = duplicate counting of the same newly-dangerous response

Scores:

- S00 = T
- S10 = T + E
- S01 = T + O
- S11 = T + E + O = raw pair score

For each score, require a unique argmax.

Let:

- top_T   = argmax S00
- top_TE  = argmax S10
- top_TO  = argmax S01
- top_raw = argmax S11

## 3. Population

Enumerate all safe 4-stone parents on the 8×8 board.

Canonicalize parents under D4 symmetry.

Eligibility requires:

1. all four scores have unique argmax;
2. at least one of the four top moves differs.

No outcome information is used in population construction.

## 4. Structural strata

Define purely from top-move membership:

### O0-only

- top_T != top_TO
- top_TE == top_raw

Equivalently:
- O changes the selected move when E=0
- O does not change the selected move when E=1

### O-overlap

- top_T != top_TO
- top_TE != top_raw

O changes the selected move in both E conditions.

### O1-only

- top_T == top_TO
- top_TE != top_raw

This stratum is secondary.

These definitions must be frozen before any exact child outcome is read.

## 5. Primary quantities

Encode selected child outcome as:

- LOSS = 1
- WIN = 0

For each O0-only or O-overlap parent, solve:

- y00 = outcome(top_T)
- y01 = outcome(top_TO)

Define parent-level O effect at E=0:

O_effect_E0 = y01 - y00

Thus:

- +1 = O selects a LOSS where T selected WIN
-  0 = same outcome
- -1 = O selects WIN where T selected LOSS

For each stratum:

Δ_O = mean(O_effect_E0)
    = added LOSS rate - baseline LOSS rate

This is an exact finite-population descriptive quantity because the plan is a full D4-orbit census, not a sample.

## 6. Primary hypothesis and success criterion

The confirmatory structural hypothesis is:

> O helps materially more in O0-only parents than in O-overlap parents.

Primary contrast:

G = Δ_O(O0-only) - Δ_O(O-overlap)

Success requires BOTH:

1. Δ_O(O0-only) > 0
2. G >= +0.05

The +0.05 threshold is frozen prospectively as a practically meaningful cross-stratum gap. It is deliberately smaller than the exploratory 9×9 gap (~0.105) and is not to be tuned after 8×8 outcomes are seen.

No primary p-value is required because both strata are censused finite populations.

Report exact counts:

- both LOSS
- both WIN
- baseline-only LOSS
- O-added-only LOSS
- discordant
- baseline LOSS rate
- O-added LOSS rate
- Δ_O
- change rate

## 7. Secondary analyses

### 7.1 O1-only

For all O1-only parents, solve:

- y10 = outcome(top_TE)
- y11 = outcome(top_raw)

Report:

Δ_O_E1 = mean(y11 - y10)

Descriptive only.

### 7.2 Shared-parent interaction in O-overlap

For all O-overlap parents, additionally solve:

- y10 = outcome(top_TE)
- y11 = outcome(top_raw)

Define:

I = (y11 - y10) - (y01 - y00)

Report:

- I histogram for -2,-1,0,+1,+2
- mean I
- median I
- I<0 / I=0 / I>0
- |I|=2 count

No new p-value.

### 7.3 Structural metadata

Before outcomes, record for each stratum:

- number of D4 orbits
- number of distinct top moves
- pair_E / pair_O if exporter supports them
- top-move equality pattern
- orbit size

Do not define or tune new thresholds from 8×8 outcomes.

## 8. Solver work deduplication

Create the union of required unique child roots:

(canonical_parent, move)

and exact-solve each unique root once.

Required moves:

- O0-only: top_T, top_TO
- O-overlap: top_T, top_TO, top_TE, top_raw
- O1-only: top_TE, top_raw

Join the resulting root outcomes back to parent-level comparisons.

Solver semantics must be identical across all roots.

## 9. Dependence audit

Before outcomes, audit shared child roots across different parents.

Two distinct 4-stone parents can generate the same 5-stone child.

Record:

- total child-root instances
- unique child roots
- number of child roots shared by >1 parent
- connected-component sizes induced by shared children

Because the main endpoint is a full finite-population census, this does not invalidate the descriptive contrast, but it must be reported and must not be hidden.

## 10. Freeze requirements

Before reading any 8×8 child outcome, commit:

1. population exporter / selector
2. canonical population CSV
3. stratum counts
4. required-root CSV
5. SHA256 hashes
6. this preregistration document
7. solver binary/source identity
8. success criterion exactly as written above

The freeze commit hash is part of the final report.

## 11. Prohibited changes after outcome observation

Do not:

- alter T/E/O definitions
- change unique-argmax eligibility
- alter O0-only/O-overlap/O1-only definitions
- change the +0.05 primary threshold
- drop inconvenient parents
- add a minimum pair_E threshold
- choose a subset based on outcomes
- convert a secondary result into the primary criterion

Any new hypothesis generated from the 8×8 result requires another independent dataset.

## 12. Interpretation

If the primary criterion succeeds, the result supports cross-board-size replication of the claim:

> O's usefulness is strongly conditioned by the outcome-free top-move membership structure, rather than by a large E×O interaction on the same parent.

If Δ_O(O0-only) is positive but G < 0.05, treat the 9×9 effect heterogeneity as not materially replicated.

If Δ_O(O0-only) <= 0, the main 9×9 structural hypothesis fails to replicate on 8×8.
