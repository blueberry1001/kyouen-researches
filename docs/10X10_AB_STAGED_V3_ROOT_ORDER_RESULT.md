# AB staged-V3 root-order solver benchmark — result

## Verdict

**Correctness PASS (16/16). Confirmatory performance FAIL.**

Staged V3 shortlist root ordering is **not** a confirmatory solver speedup
under the frozen probe-inclusive gates, even though aggregate visited
improves and exact-only work is much lower.

| gate | required | observed | pass |
|---|---|---|---|
| outcome agreement | 16/16 | 16/16 (all WIN) | yes |
| aggregate visited ratio | < 1.0 | **0.908** | yes |
| median parent ratio | < 1.0 | **1.367** | no |
| improved parents | ≥ 13/16 | **7/16** | no |
| worst parent ratio | ≤ 2.0 | **3.289** (`3,36,62`) | no |

Secondary:
- one-sided exact sign test (improved vs worse): p = **0.773** (not evidence of general speedup)
- median solver-seconds ratio: **1.71**
- aggregate exact-only ratio: **0.698** (ignoring probes, B looks strong)
- probe overhead share of A total: **0.210**
- median probe / A: **0.513** (probe fixed cost is half of a typical native parent solve)

## Provenance

- branch: `ab-staged-v3-root-ordering`
- cohort freeze: `2a257ca`
- prereg + runner: `96c192b`
- 10k + top-11 freeze: `27cf12c` (shortlist sha256 `45806cb5…bc71a`)
- 1M ranking freeze: `de8c8be` (ranking sha256 `c788bce7…d5f77`)
- root orders: `6ccbac5` (orders sha256 `af3ff00f…b6df5`)
- seed: `kyouen-10x10-ab-staged-v3-root-seed-20260913`
- 16 fresh parents, 1,529 children (clean universe 14,635; excluded 5,720)
- probe binary `tmp-kb/probe_holdout_native` sha256 `15d805ea…`
- exact binary `tmp-kb/parent_bench_native` sha256 `e0de57b3…`
- probes: shrink=3 load=80; exact: shrink=0 load=90; K=11 frozen from V3
- fresh process per probe child and per (parent, strategy) exact
- AB/BA by SHA256(parent) parity; serial exacts; 1 repeat (visited primary)

## Primary table (visited)

| parent | A_exact | B_exact | probe | B_total | ratio | exact-only | entA | entB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 4,55,78 | 82,933,033 | 12,981,953 | 11,950,000 | 24,931,953 | 0.301 | 0.157 | 5 | 1 |
| 4,45,68 | 79,047,740 | 12,474,929 | 11,970,000 | 24,444,929 | 0.309 | 0.158 | 4 | 1 |
| 3,58,81 | 68,428,419 | 11,363,418 | 11,960,000 | 23,323,418 | 0.341 | 0.166 | 3 | 1 |
| 2,30,53 | 86,429,522 | 22,187,375 | 11,920,000 | 34,107,375 | 0.395 | 0.257 | 5 | 1 |
| 2,50,69 | 111,884,858 | 40,379,879 | 11,970,000 | 52,349,879 | 0.468 | 0.361 | 7 | 2 |
| 11,25,64 | 101,290,530 | 55,761,029 | 11,920,000 | 67,681,029 | 0.668 | 0.551 | 4 | 3 |
| 1,27,54 | 28,886,008 | 15,660,673 | 11,970,000 | 27,630,673 | 0.957 | 0.542 | 2 | 1 |
| 4,13,67 | 21,645,184 | 16,742,770 | 11,960,000 | 28,702,770 | 1.326 | 0.774 | 1 | 1 |
| 4,15,23 | 14,494,611 | 8,435,409 | 11,970,000 | 20,405,409 | 1.408 | 0.582 | 1 | 1 |
| 4,16,41 | 14,364,974 | 9,823,171 | 11,970,000 | 21,793,171 | 1.517 | 0.684 | 2 | 1 |
| 2,59,87 | 241,174,390 | 362,238,186 | 11,970,000 | 374,208,186 | 1.552 | 1.502 | 21 | 30 |
| 4,32,64 | 14,189,168 | 10,662,167 | 11,970,000 | 22,632,167 | 1.595 | 0.751 | 1 | 1 |
| 12,57,58 | 23,332,546 | 26,873,962 | 11,970,000 | 38,843,962 | 1.665 | 1.152 | 2 | 1 |
| 12,44,46 | 6,657,408 | 6,657,408 | 11,960,000 | 18,617,408 | 2.796 | 1.000 | 1 | 1 |
| 22,44,55 | 7,049,546 | 10,239,311 | 11,900,000 | 22,139,311 | 3.141 | 1.452 | 1 | 1 |
| 3,36,62 | 7,198,361 | 11,715,422 | 11,960,000 | 23,675,422 | 3.289 | 1.628 | 1 | 1 |

Aggregates: A 1,011,326,660 → B_exact 705,555,275 + probe 191,380,000 = 896,935,275
(ratio 0.908).

## Mechanism decomposition (secondary)

Classes (post hoc, frozen rules not changed):

| class | n | parents |
|---|---:|---|
| expensive_A_wins (B faster E2E) | 7 | 4,55,78 4,45,68 3,58,81 2,30,53 2,50,69 11,25,64 1,27,54 |
| cheap_A_probe_dominated | 6 | 12,44,46 22,44,55 3,36,62 4,15,23 4,16,41 4,32,64 |
| loss_proof_cost_or_order | 3 | 2,59,87 12,57,58 (+ exact-worse extras) |

Hypotheses:
- **H1 supported on mechanism, not on gates.** Root children entered fell
  in 9/16 parents; 7 of those 9 are E2E wins. Typical win is A_entered
  4–7 → B_entered 1–2, cutting expensive WIN siblings before a LOSS proof.
- **H2 partially supported.** Several parents win E2E (entered drop and
  exact-only ≤ 0.4) despite paying ~12M probe nodes. WIN-prefix savings
  can exceed probe overhead when A is expensive.
- **H3 supported as the failure mode.** Failures split into:
  1. **cheap native A** (A ≲ 15M, often entered=1): probe fixed ~12M is
     already ≥ A, so any exact improvement is drowned. Worst ratios are
     here (`3,36,62` 3.29, `22,44,55` 3.14, `12,44,46` 2.80).
  2. **selected LOSS cost increase**: `2,59,87` entered 21→30 and
     exact-only 1.50 — staged head did not pick a cheaper proving LOSS
     than native legal-count order (V2-like residual).

`total_delta = probe_overhead + exact_delta` holds arithmetically.
`exact_delta` is the dominant win term on expensive parents and the
dominant loss term on cheap parents after probe is subtracted.

## Why this is not a solver-speedup claim

V3 classification success (top-11 recall 12/12, 87.5% probe reduction)
does **not** transfer to confirmatory parent-solver speedup:

1. Native root order already solves 5/16 parents with **entered=1**
   and total work ≲ 15M — there is no WIN-prefix to cut.
2. Probe fixed cost is **~12M visited / parent** (10k×n_children + 1M×11),
   comparable to a cheap native parent solve.
3. Even when exact-only improves a lot (median exact-only among wins
   ≈ 0.16–0.36), the frozen E2E gates require median ratio < 1 and
   ≥13/16 improved, which this cohort fails.

This matches the V2 warning: classification ranking ≠ native solver
ordering under shared-memo exact search.

## Explicit non-claims / claims

- Claim: **outcome-correct** staged root-order injection (16/16).
- Claim: **aggregate** probe-inclusive visited improved (0.908) on this
  cohort; large wins on expensive parents.
- Non-claim: confirmatory median/improved-count/worst gates — **failed**.
- Non-claim: general solver speedup for arbitrary 3-stone parents.
- Non-claim: that K=11 / 1M budget is optimal for solver cost (not tested).

## Artifacts

- raw exacts: `results/10x10/ab-staged-v3-root/ab_exact_raw.csv`
- parent summary: `results/10x10/ab-staged-v3-root/parent_summary.csv`
- aggregate: `results/10x10/ab-staged-v3-root/aggregate_summary.json`
- mechanism: `results/10x10/ab-staged-v3-root/mechanism_decomposition.csv`,
  `mechanism_summary.json`
- analysis scripts: `scripts/analyze_ab_staged_v3.py`,
  `scripts/decompose_ab_staged_v3.py`

## Next actions (post-fail, new hypotheses only)

Do **not** retune on this cohort for a confirmatory claim.

1. **Budget reduction (highest leverage):** 12M probe fixed cost is the
   main E2E tax. Test 10k-only order (no 1M) or 10k→100k staged on a
   *new* independent cohort, with the same probe-inclusive gates.
2. **Selective probing:** skip probes when a cheap geometry prior predicts
   A_entered=1 (but this needs a frozen surrogate and a new cohort).
3. **Cooperate with legal-count:** hybrid residual already uses native
   tail; consider legal-count-aware head only inside the shortlist.
4. **Expensive-parent-only policy:** if a cheap pre-exact estimate can
   identify high-A parents, staged V3 looks attractive — again needs a
   new blind cohort.

Given gates, V3 remains a **classification** result. Solver use requires
either budget cut or a parent-cost prefilter, validated independently.

## Reproduction

```bash
git checkout ab-staged-v3-root-ordering
wsl python3 scripts/run_ab_staged_v3.py --phase all --workers 12
wsl python3 scripts/analyze_ab_staged_v3.py
wsl python3 scripts/decompose_ab_staged_v3.py
```

Resume-safe; frozen `protocol.json` must match on every run.
