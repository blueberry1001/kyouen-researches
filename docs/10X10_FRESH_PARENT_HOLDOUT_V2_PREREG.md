# Preregistration: 10x10 Second Clean Holdout Validation (V2)

Date: 2026-09-07
Branch: `10x10-second-clean-holdout`
Status: **FROZEN BEFORE PROBES OR EXACT OUTCOMES**

## 1. Background and Objective

The initial 11-parent holdout evaluation demonstrated strong performance for the fresh-solver `memo_used` ascending ranking heuristic (ranks `1,1,1,1,1,1,1,6,1,1,1` vs random median, sign $p = 0.00098$, mean AUC 0.820). However, audit `3d87e8b` and sensitivity analysis `c7fc23c` revealed that all 11 parents came from previously classified proof families (`90-66` and `90-61`), and contained 33 pre-known exact LOSS child witnesses. While sensitivity analysis excluding all 33 pre-known witnesses retained $p = 0.0039$ and mean AUC 0.813, establishing external validity requires a strictly clean, child-outcome-blind holdout.

This V2 confirmatory holdout tests the identical ranking heuristic on a completely fresh, geometry-sampled parent cohort where **no child outcomes, parent game values, or proof witnesses were inspected prior to freezing**.

## 2. Parent Universe and Exclusion Rule

1. **Universe**: All D4-canonical safe 3-stone states on a $10 \times 10$ board. Total size: **20,355** canonical states. (All 3-stone states are non-terminal in Kyouen since co-circularity requires 4 stones).
2. **Canonicalization**: For any 3 points $(p_1, p_2, p_3)$, standard D4 orbit reduction under 8 transformations:
   $$\text{canonical}(p_1, p_2, p_3) = \min_{k \in [0, 7]} \text{sort}(T_k(p_1), T_k(p_2), T_k(p_3))$$
3. **Exclusion List**: Exhaustive scan of the entire Git history at `HEAD` for any 3-stone state ever referenced in tests, proofs, tuning, or prior holdouts. Total excluded: **2,899** states (stored in `results/10x10/clean-holdout-v2/holdout_v2_exclusion_list.csv`).
4. **Clean Universe**: $20,355 - 2,899 = \mathbf{17,456}$ completely untouched candidate parents.

## 3. Sampling Method and Frozen Cohort

- **PRNG / Hash Chaining**: Fully deterministic via SHA-256:
  $$\text{hash}(P) = \text{SHA256}(\text{"kyouen-10x10-fresh-parent-holdout-v2-seed-20260907:"} + P)$$
- **Primary Sample Size**: **12 parents** (approx. 1,100 children), ensuring exhaustive exact solving feasibility while matching/exceeding the first holdout sample size ($N=11$).
- **Frozen Primary Cohort**:
  1. `3,53,84` (97 children)
  2. `0,11,35` (96 children)
  3. `12,24,68` (96 children)
  4. `12,32,55` (97 children)
  5. `3,47,63` (92 children)
  6. `4,24,26` (96 children)
  7. `4,42,54` (94 children)
  8. `23,44,45` (92 children)
  9. `11,78,87` (97 children)
  10. `14,64,74` (90 children)
  11. `11,38,44` (97 children)
  12. `13,52,57` (92 children)
- **Total Child Tasks**: **1,136 tasks** (ordered task list digest: `7ca356a7453437448d301c53642df1ed49ad4f37f952dce7a0f96735f35c900c`).

## 4. Ranking Rule (Frozen, Identical to V1)

Each safe child is evaluated via a fresh Solver process with budget $1,000,000$ (shrink=3, load=80).
Ranking key tuple:
1. Probe resolved LOSS first.
2. Unresolved probes: `memo_used` **ascending** (smallest memo table first).
3. Probe resolved WIN last.
4. Tie-breaker: 4th move board index **ascending** (deterministic).

**Direction change is strictly forbidden** (remains `memo_used` ascending).

## 5. Hypotheses and Success Criteria

### Primary Endpoint
For each eligible parent having $\ge 1$ exact LOSS child ($l \ge 1$), compare the first LOSS rank $r_1$ against the exact median rank under the uniform random ordering null:
$$\text{Med}_{\text{random}}(m, l) = \min \{ r \mid F_{\text{null}}(r; m, l) \ge 0.5 \}$$
A parent is scored as:
- **better**: $r_1 < \text{Med}_{\text{random}}$
- **worse**: $r_1 > \text{Med}_{\text{random}}$
- **tie**: $r_1 = \text{Med}_{\text{random}}$

### Primary Hypothesis Test
One-sided exact sign test on eligible parents with ties excluded:
$$H_0: P(\text{better}) \le P(\text{worse}) \quad \text{vs.} \quad H_1: P(\text{better}) > P(\text{worse})$$
Significance threshold: $\alpha = 0.05$.

### Secondary Endpoints
1. Rank sum statistic: $\sum r_1$ vs. null expectation.
2. Normalized first LOSS rank: mean and median of $r_1 / m$.
3. Child-level AUC: computed for parents with both $\ge 1$ LOSS and $\ge 1$ WIN.
4. Individual parent outcomes and exact LOSS yield.

## 6. Execution Order and Stopping Rule

1. Commit sampling code, seed, candidate list, task list, and this preregistration document before running probes.
2. Execute fresh 1M probes on all 1,136 child tasks.
3. Commit raw probe outputs and probe protocol manifest before running exact solver.
4. Execute exact solver on all 1,136 child tasks.
5. Compute preregistered evaluation metrics and compile reports.
6. Stopping rule: All 12 parents are evaluated. No parents may be added or removed post-hoc based on exact outcomes.
