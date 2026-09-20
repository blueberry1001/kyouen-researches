# Preregistration: 10x10 cache-aware below-root ordering — independent cohort confirmation V2

Date: 2026-09-08
Branch: `preregister-10x10-cache-aware-below-root-confirmation-v2`
Base: `d9b9a0fafa0158f185f17a5acf323d617eb33d58`
Status: **FROZEN BEFORE ANY A/B RUN ON THE CONFIRMATION COHORT**

## 1. Confirmatory question

The completed fixed-cohort A/B experiment on the original V2 primary 12 parents found that, with memo lookup/reuse fully preserved, removing cached outcome from below-root child ordering increased exact visited on 12/12 parents (median blind/aware ratio 1.162). The causal question for this preregistration is:

> Does cache-aware below-root ordering reduce exact parent-solver work on a genuinely unused, independently frozen 3-stone parent cohort?

This is a generalization confirmation only. No new heuristic is introduced.

## 2. Cohort provenance and blindness

The cohort is **not sampled now**. It is the unused second half of the V2 `extended24` sample that was already deterministically frozen in commit `98564ac1713c7cc387d69a8fe301a0417c01f765` on 2026-09-07, before V2 probes or exact outcomes were collected.

That original V2 freeze used:

- all 20,355 D4-canonical safe 3-stone states;
- exclusion of 2,899 3-stone states previously referenced in Git history;
- clean universe size 17,456;
- seed `kyouen-10x10-fresh-parent-holdout-v2-seed-20260907`;
- SHA-256 deterministic ordering;
- an extended sample of 24 parents.

Ranks 1–12 became the V2 primary cohort. This confirmation uses **exactly ranks 13–24**, in their pre-existing order:

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

Frozen copy: `results/10x10/cache-aware-below-root-confirmation-v2/cohort.csv`.

Source trust anchors:

- original extended sample file: `results/10x10/clean-holdout-v2/holdout_v2_parents_extended24.csv`
- source blob SHA: `ebbfde8c7d6de2cf7c9803ab508454e43886d442`
- original sampling manifest blob SHA: `89d01b0015920ad24fa0f1fc25f36c768250f4a8`
- original freeze commit: `98564ac1713c7cc387d69a8fe301a0417c01f765`

No parent may be added, dropped, replaced, reordered, or selected based on outcome, runtime, probe information, or any new solver result.

## 3. Solver conditions

Use the same implementation and semantics as the completed experiment `preregister-10x10-cache-aware-vs-blind-below-root`.

One binary must support both conditions via the existing runtime switch:

### A — cache-aware native below-root ordering

At every non-root node, native ordering:

1. cached LOSS
2. uncached
3. cached WIN
4. `legal_move_count` ascending
5. canonical key ascending

Root depth 3 remains native in both A and B.

### B — cache-blind below-root ordering

For `depth > 3`, preserve exactly the same:

- memo lookups;
- child prefetch;
- cached-outcome recursive omission;
- cached-LOSS immediate WIN shortcut;
- memo puts;
- child generation and deduplication;
- legal-move semantics;
- canonicalization.

Only the ordering comparator ignores cached outcome and becomes:

1. `legal_move_count` ascending
2. canonical key ascending

No other difference is allowed.

## 4. Execution protocol

- Fresh process / fresh Solver per parent-condition.
- Same binary for A and B.
- Same shrink/load and all solver settings as the completed C1 experiment.
- Run all 12 parents under both conditions: 24 parent runs total.
- Counterbalance condition order by frozen cohort rank:
  - odd rank: A then B
  - even rank: B then A
- Exact visited is the primary work measure.
- Solver seconds and wall seconds are secondary only.
- Existing frozen instrumentation may remain enabled, but the schema must not be changed after runs begin.

Before the first cohort run, commit a machine-readable execution manifest containing at minimum:

- cohort file SHA256;
- solver binary SHA256;
- relevant solver source/blob SHAs;
- runner/analyzer/verifier SHAs;
- compiler/version and compile command;
- solver parameters;
- the A/B runtime arguments;
- parent execution order.

Raw outputs must be committed before verification/analysis.

## 5. Semantic checks

For each parent:

- A and B must return the same game outcome.
- Root behavior must be identical between A and B by construction: root unique count, first root child and root-depth policy are unchanged.
- B must retain memo reuse; this is not a memo-off experiment.
- B below-root ordering-change counters attributable to cache priority must be zero, if the existing instrumentation exposes them.

There is intentionally no requirement that these new parents have the same outcome as the original 12. Outcome is not an eligibility criterion.

## 6. Primary endpoint

For each parent `i` with completed A and B runs:

`R_i = visited_B_i / visited_A_i`

where `R > 1` means cache-aware ordering reduces exact work.

### Frozen replication criterion

Carry forward the **same criterion as C1**, without tightening or loosening it after observing the original effect:

1. median `R > 1`, and
2. A has lower visited than B in at least **7 of 12** parents.

Both conditions are required for PASS.

The primary report must include all 12 individual `R_i`, median, geometric mean, arithmetic mean, aggregate visited ratio, and improved/tie/worse counts.

A paired exact sign test is reported as a secondary inferential statistic; it does not replace the frozen PASS criterion.

## 7. Failures, interruptions and stopping

- All 12 frozen parents must be attempted under both conditions.
- Do not stop early for apparent success or failure.
- Do not replace a parent after timeout, TableFull, crash, or unexpected outcome.
- A machine interruption may be rerun from scratch for the **same** parent-condition.
- Any unresolved solver failure is reported explicitly; if a primary ratio cannot be obtained for all 12 parents, the confirmatory endpoint is reported as incomplete rather than silently reducing the denominator.

## 8. Secondary mechanism endpoints

Using the already frozen instrumentation only, report A vs B aggregate and depth-resolved differences for:

- prefetch memo hit rate;
- cached child recursive-omission fraction;
- cached-LOSS immediate WIN shortcut fraction;
- exact memo puts / final memo usage;
- depth at which visited divergence begins and peaks.

These are explanatory only and may not redefine the primary conclusion.

## 9. Interpretation rules

### PASS

If the frozen replication criterion passes, the supported statement becomes:

> Cache-aware use of memo outcome in below-root child ordering has a reproducible, independent causal work-saving effect across two separately frozen 12-parent cohorts.

Effect-size generalization should be described using both cohorts, not only the larger estimate.

### FAIL

If the criterion fails, retain the original C1 result as a fixed-cohort causal finding but do not claim generalization. Analyze heterogeneity by parent outcome/depth only as exploratory follow-up.

## 10. Forbidden changes before completion

Do not:

- tune the cached priority rule;
- add depth cutoffs to the aware ordering;
- change root ordering;
- switch to memo-off;
- select parents using parent/child outcomes;
- use 10k/100k/1M probe values for cohort selection;
- drop slow or inconvenient parents;
- change the PASS threshold;
- merge to `main`.

The next optimization question (e.g. a cheaper approximation to cached-LOSS-first ordering) starts only after this confirmation is complete.
