# Preregistration: AB staged-V3 root-order solver benchmark

Date: 2026-09-13
Branch: `ab-staged-v3-root-ordering`
Base: `ce30c31` (V3 staged holdout result) on top of V2 parent-bench lineage
Status: **FROZEN BEFORE ANY AB PROBE OR EXACT ROW IS COLLECTED**

## 0. Why this experiment exists

V3 (`docs/10X10_STAGED_V3_HOLDOUT_RESULT.md`) established that staged
10k → top-11 → 1M ranking is a **classification / shortlist-recall**
success on an independent 12-parent holdout (12/12 top-11 LOSS coverage;
87.5% probe reduction vs full-1M). That result explicitly does **not**
claim native parent-solver wall-clock or visited-node speedup.

V2 parent benchmark (`docs/10X10_V2_10K_PARENT_SOLVER_BENCHMARK_REPORT.md`)
showed that naive 10k-memo root ordering **loses** (median work ratio 1.84;
improved 2/12) even ignoring shared-memo pollution (S1 median 1.79).
Mechanism: 10k memo order often selects an expensive LOSS sibling; native
`legal_move_count` is a strong proof-cost heuristic.

Staged V3 is a different treatment: only the top-11 shortlist is reordered
by a 1M rerank; residuals fall back to native order. Whether that reduces
**probe-inclusive end-to-end solver cost** is untested.

This preregistration freezes a **new independent parent cohort** and tests:

> `B_total = 10k_probe_visited + 1M_probe_visited + staged_exact_visited`
> versus
> `A_total = native_exact_visited`

under identical solver binary, memo, shrink/load, and fresh-process rules.

## 1. Parent universe and exclusion

1. Universe: all D4-canonical 3-stone states on 10×10 (20,355).
2. Exclusion: every 3-stone state appearing in git history at freeze HEAD
   (`ce30c31` lineage working tree / `HEAD` at sample time), plus explicit
   V1/V2/V3 parent lists. This includes V1 (11), V2 (12), V3 (12), parent
   benchmark, tuning, counterexample, proofs/tests, and any prior root-ordering A/B.
3. Selection: SHA-256 ranking
   `SHA256("kyouen-10x10-ab-staged-v3-root-seed-20260913:" + parent)`
   ascending on the clean universe. Top **16** parents.
4. No child outcomes, parent game values, or proof witnesses are inputs
   to selection.

Cohort freeze artifacts (already committed with this phase):
- `results/10x10/ab-staged-v3-root/ab_parents_primary.csv`
- `results/10x10/ab-staged-v3-root/ab_exclusion_list.csv`
- `results/10x10/ab-staged-v3-root/sampling_manifest.json`
- `results/10x10/ab-staged-v3-root/exact_task_list.csv`
- `results/10x10/ab-staged-v3-root/tasks_manifest.json`

## 2. Frozen protocol choices

| choice | value |
|---|---|
| cohort size | 16 parents |
| 10k budget | 10,000 visited / child |
| 1M shortlist | K = 11 children / parent (V3 frozen K; not retuned) |
| shrink / load (probes) | 3 / 80 |
| shrink / load (exact) | 0 / 90 |
| exact budget | 0 (unbounded) |
| fresh process | yes; one solver process per probe child; one per (parent, strategy) exact |
| probe binary | `tmp-kb/probe_holdout_native` (sha256 `15d805ea…`) |
| exact binary | `tmp-kb/parent_bench_native` (sha256 `e0de57b3…`, root-order patch) |
| ranking key | probe LOSS first; unresolved `memo_used` asc; probe WIN last; move asc |
| K / direction / adaptive rules | frozen from V3; no change |
| exact repeats | 1 serial run per (parent, strategy); visited is primary |
| counterbalance | SHA256(parent) parity decides AB vs BA |
| exact timeout | 10800 s per (parent, strategy) |

### Strategy A — baseline

Unmodified native root ordering. No probes. Command shape:
`parent_bench_native STATE 0 90 0 0 --root-depth 3`

### Strategy B — staged V3 root ordering

1. Enumerate all legal root children (same task list as probes).
2. Fresh 10k probe every child (`probe_holdout_native`, shrink=3, load=80).
3. Rank by frozen V3 corrected key; freeze top-11.
4. Fresh 1M probe the top-11 only.
5. Re-rank the 11 by the same key on 1M rows.
6. Build root order file:
   - unique canonical children first-seen from task list;
   - head: 1M-reordered top-11 (first-occurrence unique);
   - tail: remaining unique children in **native residual order**
     (`legal_move_count` ascending, then canonical Bits key ascending),
     matching the solver's uncached root comparator.
7. Exact solve with `--root-order-file` + `--root-depth 3`.
8. Probe memo is **not** imported into the exact solver; only order is injected.

Forbidden after freeze:
- changing K, budgets, ranking key, tie-break
- `0,16,59`-style exceptions, geometry exceptions, adaptive K
- reading exact labels to build order or to fallback
- dropping shortlist-miss children from native fallback
- retuning after seeing parent-level ratios

## 3. Primary cost endpoint (frozen decision)

### Correctness gate
- A vs B parent outcome agreement must be **16/16**.
- Any mismatch → implementation failure; performance claims invalid.

### Performance gates (confirmatory success candidate)

Let `ratio_i = B_total_i / A_total_i` in **visited nodes**:
`B_total = sum(10k visited) + sum(1M visited) + exact_visited_B`
`A_total = exact_visited_A`

All of the following must hold:
1. aggregate ratio `sum(B_total)/sum(A_total) < 1.0`
2. median parent ratio < 1.0
3. improved parents ≥ **13 / 16**  
   (scaled from V2 10/12 → 10/12 × 16 = 13.33, floored to 13; fixed before data)
4. worst parent ratio ≤ 2.0

Secondary (not success-determining):
- aggregate / median total-visited ratio (same as primary here)
- one-sided exact sign test on parent ratios
- aggregate / median end-to-end solver-seconds ratio
  (`B: probe_seconds + exact_seconds` vs `A: exact_seconds`)
- first LOSS rank (classification secondary only)

No bootstrap unless sign test is ambiguous and a method is frozen here
(this prereg does **not** freeze a bootstrap).

## 4. Mechanism decomposition (secondary)

Per parent, if A/B visited data allow:

- probe overhead = `10k_visited + 1M_visited`
- WIN-prefix exact delta: difference in root children entered before first
  LOSS (from `bench_root entered`) and, when instrumented binary is used,
  visited attributed to WIN-prefix children
- selected LOSS proof-cost delta: selected LOSS child rank + (if available)
  visited of the proving child
- residual / memo interaction: leftover of
  `exact_delta - (win_prefix_delta + selected_loss_delta)`

Hypotheses (report support/refute; do not retune):
- **H1** staged V3 reduces expensive WIN siblings before first LOSS.
- **H2** staged V3 can win even without picking the cheapest LOSS if
  WIN-prefix savings exceed probe overhead.
- **H3** failures have probe fixed cost and/or expensive selected LOSS
  exceeding WIN-prefix savings (V2-like).

`0,16,59` and other weak parents may be discussed **post hoc** only.

## 5. Execution order (hard)

1. Commit cohort freeze (parents, exclusion, tasks, this doc skeleton).
2. Collect all 10k probes. Commit raw CSV + protocol.
3. Freeze top-11 shortlist. Commit + SHA256.
4. Collect 1M probes on shortlist. Commit raw CSV + protocol.
5. Freeze 1M ranking. Commit + SHA256.
6. Build root order files (no exact labels). Commit orders + digests.
7. Run exact A/B serial, counterbalanced. Commit raw CSV.
8. Only then evaluate endpoints. Commit summary + analysis.

Stopping rule: all 16 parents complete every stage. No parent add/drop.

## 6. Artifacts

- `results/10x10/ab-staged-v3-root/sampling_manifest.json`
- `results/10x10/ab-staged-v3-root/ab_parents_primary.csv`
- `results/10x10/ab-staged-v3-root/exact_task_list.csv`
- `results/10x10/ab-staged-v3-root/probe_10000.csv`
- `results/10x10/ab-staged-v3-root/top11_shortlist.csv` + manifest
- `results/10x10/ab-staged-v3-root/probe_1000000_top11.csv`
- `results/10x10/ab-staged-v3-root/top11_rank_1m.csv` + manifest
- `results/10x10/ab-staged-v3-root/root_orders/order_*.txt`
- `results/10x10/ab-staged-v3-root/ab_exact_raw.csv`
- `results/10x10/ab-staged-v3-root/protocol.json`
- `results/10x10/ab-staged-v3-root/parent_summary.csv`
- `results/10x10/ab-staged-v3-root/aggregate_summary.json`
- `docs/10X10_AB_STAGED_V3_ROOT_ORDER_RESULT.md`

## 7. Failure analysis (if gates fail)

Parent-by-parent diagnosis using already-collected probe rows plus exact
labels: probe cost share, WIN-prefix entered, selected LOSS rank, residual
order position of true first LOSS, memo occupancy if available. Any new
rule invented here is exploratory and requires a further independent cohort.
