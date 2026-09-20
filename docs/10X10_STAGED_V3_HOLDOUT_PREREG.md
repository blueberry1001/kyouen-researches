# Preregistration: Staged Probe V3 Holdout (10k → top-11 → 1M)

Date: 2026-09-12
Branch: `staged-probe-v3-holdout`
Base: `80b734b265a698370c33631bc8c9771c8fc645e2`
Status: **FROZEN BEFORE ANY V3 PROBE OR EXACT ROW IS COLLECTED**

## 0. Why this experiment exists

V1 (11 parents) and V2 (12 clean parents) established that fresh-solver
`memo_used` ascending is a strong LOSS **classifier** at 1M budget.
V2 also showed 10k retains ranking signal but weakens top-6 recall
(8/11 on the older budget-stability set; V2 10k first-LOSS ranks stayed
small). Exploratory staged simulations on frozen V2 10k rows (P8) were
post-hoc and therefore cannot support a success claim.

Separately, the V2 native parent-solver benchmark showed that using 10k
memo order as a **root proof-cost** heuristic fails (median work ratio
1.84). That result does **not** invalidate the classification endpoint
below; it only forbids claiming solver speedup from this holdout alone.

This preregistration freezes a **new independent parent cohort** and tests
the staged classification hypothesis:

> All children get a fresh 10k probe. The top-K=11 by the frozen ranking
> key receive a fresh 1M probe. The 10k top-11 set contains at least one
> exact LOSS child for every eligible parent.

K=11 is **not** tuned on this holdout. It was fixed from prior
exploratory work (V2 budget-stability top-11 coverage on the older 11
parents, and staged-sim neighborhood around K=10). If this holdout fails,
K will not be re-tuned on the same parents.

## 1. Parent universe and exclusion

1. Universe: all D4-canonical 3-stone states on 10×10 (20,355).
2. Exclusion: every 3-stone state appearing in git history at base HEAD
   `80b734b` in `10x10`/`probe`/`holdout`/`benchmark` paths, plus the
   frozen V1 selection CSV and V2 primary/sampling/protocol lists.
3. Selection: SHA-256 ranking `SHA256("kyouen-10x10-staged-v3-holdout-seed-20260912:" + parent)`
   ascending on the clean universe. Top 12 parents.
4. No child outcomes, parent game values, or proof witnesses are inputs
   to selection.

## 2. Frozen protocol choices

| choice | value |
|---|---|
| cohort size | 12 parents |
| 10k budget | 10,000 visited / child |
| 1M shortlist | K = 11 children / parent |
| shrink / load (probes) | 3 / 80 |
| shrink / load (exact) | 0 / 90 |
| exact budget | 0 (unbounded) |
| fresh process | yes, one solver process per child, no memo sharing |
| solver | `tmp-kb/probe_holdout_native` |
| ranking key | probe LOSS first; unresolved `memo_used` asc; probe WIN last; move asc |
| tie-break | 4th-move board index ascending (never changed mid-run) |

Solver binary SHA256 is recorded in each run protocol JSON at freeze
time. Source digest is enforced via `probe_holdout_native.sources.sha256`.

## 3. Execution order (hard)

1. Commit sampling code, exclusion list, parent list, children/task list,
   and this document.
2. Collect **all** V3 fresh 10k probes. Commit raw CSV + protocol.
3. Select top-11 per parent from 10k rows only. Commit shortlist + SHA256
   manifest. **Do not read exact labels.**
4. Collect fresh 1M probes for the shortlist only (fresh process; 10k
   state is not continued). Commit raw CSV + protocol.
5. Re-rank the 11 shortlist children by the same key on 1M rows.
   Commit ranking artifact.
6. Only then run exact solves on **all** children of the cohort.
7. Unlock labels and evaluate endpoints. Commit parent-by-parent results,
   including failures.

Stopping rule: all 12 parents complete every stage above. No parent
add/drop after step 1. No K/direction/budget change after this freeze.

## 4. Endpoints

### Primary
For each parent with ≥1 exact LOSS child, indicator that the frozen 10k
top-11 set contains ≥1 LOSS. Parent-level recall = successes / eligible
parents. Report exact count and binomial CI.

Success criterion (classification claim): recall = 12/12 if all 12 are
eligible; if any parent has zero LOSS children it is ineligible and must
be reported separately (not silently dropped).

### Secondary
1. First LOSS rank inside the 1M-reordered shortlist of 11 (1-based).
2. Median first-LOSS rank in the 1M shortlist order.
3. Top-1 / top-3 / top-6 recall within the 1M shortlist.
4. First LOSS rank under 10k-only full-child ordering (for comparison).
5. Probe node budget: `10k * n_children + 1M * 11` vs `1M * n_children`
   and the reduction ratio.
6. Wall-clock of 10k stage and 1M stage.
7. Catastrophic false-switch inventory: parents where 10k top-11 misses
   all LOSS children, or 1M shortlist first-LOSS rank is worse than the
   random median on 11 items. Report parent-by-parent; never hide behind
   aggregates. Note `12,32,55`-type failures are about **solver root
   ordering**, which is out of scope here but must not be confused with
   this classification endpoint.

### Explicit non-claims
- This holdout does **not** authorize changing the native solver root
  order.
- This holdout does **not** claim exact-solver wall-clock speedup.
- Solver A/B integration is a later phase and requires its own
  preregistration.

## 5. Blindness

- 10k collection must finish before top-11 selection.
- Top-11 must be committed before 1M collection.
- 1M ranking must be committed before exact outcomes are analyzed.
- Exact runner may execute in parallel with analysis scaffolding, but
  no endpoint script may read `exact_outcomes.csv` until 1M ranking
  artifacts exist on disk.

## 6. Failure analysis (if primary fails)

If any eligible parent misses LOSS in the 10k top-11, produce a
parent-by-parent diagnosis using only already-collected probe rows
(10k and, if available, 1M) plus later exact labels: memo growth, rank
stability, legal-move count, maxdepth, geometry. Any new feature
discovered here is exploratory; this cohort is then training/development
and a **further** independent holdout is required.

## 7. Artifacts

- `results/10x10/staged-v3-holdout/sampling_manifest.json`
- `results/10x10/staged-v3-holdout/holdout_v3_parents_primary.csv`
- `results/10x10/staged-v3-holdout/exact_task_list.csv`
- `results/10x10/staged-v3-holdout/independent_probe_10000.csv`
- `results/10x10/staged-v3-holdout/top11_shortlist.csv`
- `results/10x10/staged-v3-holdout/top11_shortlist.manifest.json`
- `results/10x10/staged-v3-holdout/independent_probe_1000000_top11.csv`
- `results/10x10/staged-v3-holdout/top11_rank_1m.csv`
- `results/10x10/staged-v3-holdout/exact_outcomes.csv`
- `results/10x10/staged-v3-holdout/primary_results.csv`
- `results/10x10/staged-v3-holdout/primary_summary.json`
