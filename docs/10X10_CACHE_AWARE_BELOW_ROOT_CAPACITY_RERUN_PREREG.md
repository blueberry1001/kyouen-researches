# Preregistration: 10x10 cache-aware below-root ordering — capacity-rescued confirmation rerun

Date: 2026-09-08
Branch: `preregister-10x10-cache-aware-below-root-capacity-rerun`
Base: `5b501588d0e71807977ef69850ad78758295b031` (C2 INCOMPLETE final receipt)
Status: **FROZEN BEFORE ANY CAPACITY-RERUN A/B RESULT EXISTS**

## 1. Objective

C1 (`d9b9a0f`) found that using cached WIN/LOSS status in below-root child ordering reduced exact visited work on 12/12 parents. C2 attempted confirmation on the independently frozen V2 extended ranks 13--24, but parent `1,12,80` hit `TableFull` under both A and B. Under the frozen C2 completeness rule, C2 is correctly reported as **INCOMPLETE** and no reduced-denominator primary statistics are used.

This experiment does not reinterpret C2. It performs a **new, all-fresh 24-run rerun on the identical 12-parent cohort** with only memo capacity enlarged enough to remove the observed capacity wall. The A/B intervention, primary endpoint, success criterion, run order, and no-reduced-denominator rule remain unchanged.

The prior 22 completed C2 raw runs are provenance/audit evidence only and MUST NOT be mixed into this endpoint.

## 2. Frozen cohort

Use exactly the same V2 extended ranks 13--24, originally frozen before V2 probe/exact outcomes at commit `98564ac1713c7cc387d69a8fe301a0417c01f765`:

1. `12,21,58`
2. `0,19,95`
3. `2,11,61`
4. `1,27,61`
5. `1,68,74`
6. `0,7,67`
7. `1,12,80`
8. `2,43,60`
9. `23,37,45`
10. `1,6,51`
11. `12,13,67`
12. `12,25,71`

No parent may be added, removed, replaced, or screened by outcome/difficulty.

## 3. A/B conditions — unchanged from C1/C2

One binary, runtime switch only.

### A: cache-aware

At below-root nodes, child order is:

1. cached LOSS
2. unknown
3. cached WIN
4. `legal_move_count` ascending
5. canonical key ascending

Root behavior remains the native/frozen root behavior.

### B: cache-blind below-root

Root behavior is identical to A. Below root only, cached outcome priority is removed from sorting and children are ordered by:

`(legal_move_count ascending, canonical key ascending)`

B still retains all memo lookup/prefetch, cached outcome availability, recursive omission, cached-LOSS WIN shortcut, memo put/get, duplicate elimination, canonicalization, game rules, witness logic, and instrumentation. The only causal intervention remains whether cached WIN/LOSS is used as a below-root ordering key.

## 4. Capacity intervention — fixed before rerun

Keep `shrink=0`, `load=90`, and all memo semantics unchanged. Increase only the physical table powers for depths 12--16 by one bit. Depths 9--11 and 17 remain unchanged.

| depth/table | old power | new power |
|---|---:|---:|
| d12a | 27 | 28 |
| d12b | 24 | 25 |
| d13a | 27 | 28 |
| d13b | 25 | 26 |
| d14a | 27 | 28 |
| d14b | 24 | 25 |
| d15 | 26 | 27 |
| d16 | 23 | 24 |

At load 90%, total allowed entries by depth therefore change as follows:

- d12: 135,895,449 -> 271,790,898
- d13: 150,994,943 -> 301,989,887
- d14: 135,895,449 -> 271,790,898
- d15: 60,397,977 -> 120,795,955
- d16: 7,549,747 -> 15,099,494

### Capacity-sizing evidence permitted

Only the C2 failure occupancy is used for sizing:

- A failure: d16 = 7,549,747, exactly the old d16 90%-load ceiling.
- B failure: d13 = 150,994,943, exactly the old combined d13 90%-load ceiling; d16 was also 7,539,456 (~99.86% of its ceiling).
- B d14 was ~96.3% full, d15 ~86.2%, d12 ~79.8% when d13 failed.

Therefore d12--16 are doubled together to avoid a predictable cascade into the next nearly-full table after removing the first wall. No completed-parent A/B ratio or effect size is used to choose these powers.

The capacity profile is an engineering feasibility change, not a new heuristic.

## 5. Implementation restrictions

The capacity rerun may modify only what is necessary to select the larger d12--16 table powers and to adapt runner/provenance tooling to a new output directory/manifest.

Forbidden changes before the endpoint is complete:

- ordering comparator changes
- root-order changes
- memo lookup/prefetch changes
- load-factor change
- memo outcome encoding change
- duplicate-elimination changes
- canonicalization/game-rule changes
- witness changes
- instrumentation-schema changes unless strictly required for provenance (any such amendment must be committed before runs)
- cheap heuristic/probe additions

A/B must use one byte-identical binary and differ only by the existing runtime ordering switch.

## 6. Pre-run regression and provenance

Before freezing the execution manifest:

1. Compile the enlarged-capacity binary with the same compiler family/flags used in C2 unless an unavoidable environment difference is documented.
2. Run a small regression on successful old C2 parents under both A and B. Require exact agreement with the corresponding old C2 run for outcome, visited, memo, maxdepth, root unique/entered/first/witness. At minimum include one light, one medium, and one heavier successful parent.
3. Require B ordering-change counters to remain zero below root and memo-reuse counters to remain nonzero.
4. Seal SHA256 for cohort, all solver sources/includes, runner, verifier, analyzer, compiled binary, regression log, compiler version/flags, params, and run order in an execution manifest committed before the first endpoint run.

If the regression changes exact visited on a previously successful state, DO NOT start the endpoint; investigate before amending/re-freezing.

## 7. Execution

Exactly 12 parents x 2 conditions = 24 fresh processes.

- Serial execution.
- Rank order 1..12.
- Counterbalance exactly as C2: odd rank A then B; even rank B then A.
- No reuse of old C2 memo, raw output, or partial result.
- Save each run's raw stdout/stderr/depth outputs immediately.
- Attempt all 24 even after a failure.
- Do not run the primary analyzer until all 24 attempts are committed and the verifier passes.

## 8. Primary endpoint and success criterion — unchanged

For every parent:

`R = visited_B / visited_A`

A is better iff `R > 1`.

Confirmatory PASS requires BOTH:

1. median R > 1
2. A has smaller visited on >= 7 of 12 parents

Ties are ties.

No effect-size threshold is added. The C1 estimate (~1.16) is not a criterion.

## 9. Completeness rule

The denominator is frozen at 12.

If either condition for any parent lacks a valid exact result because of `TableFull`, timeout, crash, parse failure, or other solver failure, the endpoint is **INCOMPLETE**. Do not compute/interpret the primary endpoint on 11/12 or any reduced denominator. Do not replace the parent. Do not rerun only the failed pair under a new capacity setting inside this preregistration.

All 24 attempts must still be completed/recorded where possible.

## 10. Verification before analysis

The verifier must establish at least:

- exact frozen cohort and 24/24 completed A/B rows
- one A and one B per parent
- frozen counterbalanced execution order
- A/B outcome equality per parent
- root diagnostics equality A/B
- B below-root ordering-change counters zero
- memo reuse alive in both conditions
- counter arithmetic identities
- depth-row completeness and `sum(depth_visited) == exact_visited`
- binary/source/runner/tool hashes match execution manifest
- no old C2 raw row is used as an endpoint row

Only after verifier PASS may the analyzer compute R or any secondary endpoint.

## 11. Secondary endpoints

Pre-specified secondary outputs only:

- parent R values
- geometric/arithmetic mean R
- aggregate visited B/A
- improved/tie/worse
- exact paired sign test
- solver-seconds and wall ratios
- final memo ratio
- maxdepth
- prefetch hit rates
- cached recursive-omission fractions
- cached-LOSS shortcut rates
- depth-wise visited/recursive/cached/shortcut deltas
- C1 vs capacity-rerun effect-size comparison
- pooled C1 + completed confirmation descriptive summary

Secondary metrics cannot override the primary criterion.

## 12. Interpretation

### PASS

If the frozen primary criterion passes with 12/12 valid pairs, the evidence supports replicated causal work reduction from cache-aware below-root ordering on the independently pre-frozen extended cohort, now under a capacity regime that can represent the heavy-tail parent.

C2 itself remains historically INCOMPLETE; this new rerun is the completed confirmation.

### FAIL

C1 remains a fixed-cohort causal result, but generalization to the extended cohort is not supported.

### INCOMPLETE

No generalization judgment. Any further capacity change requires another new preregistration and all-fresh endpoint.

## 13. No peeking / no adaptive changes

Before endpoint completion, do not compute parent R, median/gmean/aggregate R, sign tests, or C1 comparison from the new runs. Operational stdout/visited may exist in raw logs but must not be summarized as A/B effects until verification passes.

Do not change capacity, table powers, load, ordering, cohort, success criteria, or failure handling after the first endpoint run starts.
