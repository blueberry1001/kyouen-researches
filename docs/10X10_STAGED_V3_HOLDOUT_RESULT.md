# Staged Probe V3 Holdout — result

Branch: `staged-probe-v3-holdout`
Prereg: `docs/10X10_STAGED_V3_HOLDOUT_PREREG.md` (frozen before probes)
Cohort freeze: `91f9e48`
10k + top-11 freeze: `32257ed`
1M ranking freeze: `d956fe6`
Base solver sources: restored to V2 freeze (`451ece8` lineage)
Solver binary: `tmp-kb/probe_holdout_native` / rebuilt `tmp-kb/probe_v3_native`
  sha256 `15d805ea9b354cc11c5c5ee5329512b723241897e32d135bf5a82094cdccd585`
  sources sha256 `9b6f227ffb9fd802851ae69bad3a5621ce78857af1c65084ae92d09aa67e47b3`

## Cohort

12 geometry-sampled parents, seed
`kyouen-10x10-staged-v3-holdout-seed-20260912`, excluding 5,157 previously
referenced canonical 3-stone states (clean universe 15,198).

| parent | children | exact LOSS |
|---|---:|---:|
| 0,16,59 | 97 | 5 |
| 1,34,89 | 91 | 35 |
| 1,37,64 | 90 | 56 |
| 1,47,64 | 97 | 20 |
| 14,27,35 | 92 | 23 |
| 2,55,65 | 95 | 95 |
| 22,24,73 | 97 | 16 |
| 3,12,81 | 97 | 22 |
| 3,23,61 | 97 | 5 |
| 3,57,78 | 97 | 10 |
| 4,21,47 | 97 | 9 |
| 4,72,85 | 97 | 13 |

Total children: 1,144. Exact: 835 WIN / 309 LOSS.

## Pipeline (blind stages)

1. Fresh 10k probe on all 1,144 children (all unresolved `PROBE`).
2. Freeze top-11 per parent by corrected key (memo asc, move asc).
   Shortlist SHA256 `18071205…f72f`.
3. Fresh 1M probe on the 132 shortlist children only.
4. Freeze 1M shortlist ranking. Ranking SHA256 `767fd26d…063f`.
5. Exact solve on all children; then unlock labels and evaluate.

## Primary endpoint

**10k top-11 contains ≥1 exact LOSS: 12 / 12 eligible parents.**

Parent-level recall = **1.00** (Wilson 95% CI [0.76, 1.00]).
No catastrophic miss parents.

Verdict: **supports** the staged 10k→top-11 classification hypothesis on
this independent holdout. K=11 was frozen before these parents were
probed; it was not retuned here.

## Secondary

1M-shortlist first-LOSS ranks:
`5,1,1,1,1,1,2,1,1,1,1,1` (median **1**).

| metric | value |
|---|---:|
| top-1 recall | 10/12 (0.833) |
| top-3 recall | 11/12 (0.917) |
| top-6 recall | 12/12 (1.000) |
| 10k full-order first-LOSS ranks | `6,1,1,1,1,1,1,3,2,2,1,1` |
| staged probe nodes | 143.44M |
| full-1M probe nodes (if all children at 1M) | 1,144M |
| probe-node reduction | **87.5%** |
| 10k probe seconds (sum) | 606.9 s |
| 1M shortlist seconds (sum) | 690.3 s |
| exact seconds (sum, labels only) | 87,804 s |

Weakest parent: `0,16,59` (10k first-LOSS rank 6; 1M shortlist rank 5;
only 5 LOSS among 97 children). Still inside the frozen top-11.

## Explicit non-claims

- This result is a **classification / shortlist-recall** success.
- It does **not** show native parent-solver wall-clock speedup.
- Prior V2 parent benchmark already showed 10k memo root ordering can
  lose on exact work; solver A/B remains a separate later phase.
- `2,55,65` has LOSS on all 95 children (trivial coverage); the other 11
  parents still pass with non-degenerate LOSS sets.

## Reproduction

```bash
# from this branch
python3 scripts/run_v3_solver_tasks.py --budget 10000 --shrink 3 --load 80 \
  --tag independent_probe_10000 --workers 12
python3 scripts/select_v3_top11.py
python3 scripts/run_v3_solver_tasks.py --budget 1000000 --shrink 3 --load 80 \
  --tag independent_probe_1000000_top11 --workers 12 \
  --only-states results/10x10/staged-v3-holdout/top11_shortlist.csv
python3 scripts/rank_v3_top11_1m.py
python3 scripts/run_v3_solver_tasks.py --budget 0 --shrink 0 --load 90 \
  --tag exact_outcomes --workers 6
python3 scripts/analyze_v3_staged_primary.py
```

Artifacts: `results/10x10/staged-v3-holdout/`.
