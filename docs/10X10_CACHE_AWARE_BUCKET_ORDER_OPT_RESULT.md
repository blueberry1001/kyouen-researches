# 10x10 cache-aware bucket-order optimization — final result

Branch: `preregister-10x10-cache-aware-bucket-order-optimization`
Base: `e9d0460b55b7f058379da2a843ecea33525b86ea`
Prereg text: `83e1b6d5f546b8d85a703fc536619f1a46bf32c8` (docs/10X10_CACHE_AWARE_BUCKET_ORDER_OPT_PREREG.md)
Machine-readable freeze: `e595a404c346b80c0252761113b381c3bda84321` (results/10x10/cache-aware-bucket-order-optimization/prereg.json)
Status: **COMPLETED — semantic parity PASS, timing primary endpoint FAIL (negative result)**

## Objective (unchanged from prereg)

Implement the already-confirmed cache-aware below-root ordering rule

`cached LOSS < unknown < cached WIN < legal_move_count asc < canonical key asc`

as a three-bucket procedure (partition by cached class, then sort each
bucket by `(count, key)`) and test whether the identical total order can be
executed with lower runtime, without changing the exact search tree.

## Implementations (one binary, runtime switch)

- **S** `--cache-aware-order-impl sort` — the historical single
  `std::sort` comparator (unchanged from base).
- **B** `--cache-aware-order-impl bucket` — two partition passes (cached
  LOSS first, unknown next, cached WIN last) + one
  `(legal_move_count, canonical key)` `std::sort` per non-empty bucket.

Switch affects ONLY cache-aware nodes strictly below frozen root depth 3.
Root ordering and the cache-blind path are untouched (proven below).

## Implementation commits

- `cfbb6e4` bucket method + impl switch + order-equivalence test
- `967e81f` fail-closed source-diff auditor (PASS)
- `f977ef9` provenance-safe build gate + binary receipt
- `a9887dd` semantic parity runner
- `e0e1c54` parity gate collection: 12/12 PASS
- `09f11c1` dedicated parity verifier: PASS
- `075fa72` frozen 72-run timing manifest
- `37f6d69` timing endpoint collection: 72/72, PRIMARY FAIL

## 1. Order-equivalence synthetic test

`scripts/order_equivalence_test.cpp` (deterministic, committed; includes
fixed seeds). 32,157 cases:

- n=0, n=1 per class, n up to 100;
- all-LOSS / all-unknown / all-WIN; 2-class subsets; 3-class mixes;
- same-count key-only ties; same-class count variation;
- adversarial reversed inputs and LOSS/WIN interleave;
- 24 exhaustive permutation families (4!+5!);
- 24,000 deterministic random fixtures (splitmix64, fixed seed
  `0xC0FFEE123456789`, every third also reversed);
- duplicate keys excluded by stated premise (canonical child keys are
  unique after the solver's duplicate-elimination stage, so
  `(class, count, key)` is a total order).

Each fixture is checked twice: via mirror comparators AND via the live
`Solver::order_cache_aware_{single_sort,bucket}_for_test` methods (the
preregistered minimal test exposure).

Result: **PASS — 32,157/32,157, zero order divergence.**

## 2. Source-diff audit

`scripts/audit_bucket_order_source_diff.py` (fail-closed, exact
expected-content reconstruction vs base `e9d0460`):

- `resume_0`, `resume_1` (memo capacity constructor), `witness_log`,
  `probe_cert_solver.cpp`: byte-identical;
- `resume_2`: ONLY the bucket method, the else-if selection line, the
  new member + setter, and the two `..._for_test` exposures;
- `resume_3`: ONLY the `--cache-aware-order-impl` token added to the
  `--certificate` rejection guard;
- `resume_4`: ONLY the runtime switch (parse loop + validation + solver
  wiring + stderr echo).

Result: **SOURCE AUDIT PASS** (auditor run before the endpoint binary
build; re-run inside the build gate).

## 3. Build / provenance

- stale binary deleted before build; built from frozen sources;
- compiler: g++ (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0;
- flags: `-O2 -std=c++20`;
- binary SHA256: `3b52e510569861b79c3281a2274d57e38d0bd96b8128f78313ed41c52bde9758`
  (one binary for both S and B);
- git HEAD at build: `967e81f...` (receipt `build_receipt.json`;
  source SHA256s sealed per file);
- runner/verifier/analyzer digests sealed in the frozen execution
  manifest BEFORE the first timing run.

## 4. Semantic parity gate (hard gate)

C1 original 12 parents (d9b9a0f cohort, restored from the frozen C1
manifest/raw outputs — no new sampling):

- 24 fresh cache-aware processes (12 parents x {S, B}, counterbalanced);
- each run compared exactly vs the frozen historical C1 cache-aware
  raw output AND vs the other implementation.

Exact-equal on ALL of (12/12 parents, both impls):

- outcome, exact visited, exact memo, maxdepth;
- all 20 `depth_visited` columns;
- all 13 `memo_used_d*` columns;
- root unique / entered / first_lo / first_hi / witness;
- all 21 instrumentation counters at every depth;
- `sum(depth_visited) == visited`, counter arithmetic identities;
- S == B memo_capacity columns (enlarged d12–d16 profile identical
  within the binary).

`memo_capacity` vs historical C1 intentionally differs: base `e9d0460`
already contains the capacity-rescued enlarged d12–d16 powers (documented
in the runner; not a semantic change of this experiment).

Flag-independence probes: cache-blind runs with `sort` and with `bucket`
are exactly equal to each other AND to the frozen C1 cache-blind run
(light parent `14,64,74`) — the switch provably cannot reach the
cache-blind path.

Result: **SEMANTIC PARITY PASS 12/12** (`parity_receipt.json`,
`parity_verifier.log`; dedicated verifier
`scripts/verify_bucket_order_parity.py` PASS).

## 5. Timing benchmark

72 fresh serial runs (12 parents x 2 impls x 3 reps), one byte-identical
binary, fresh process each run, frozen counterbalanced order (committed
manifest `execution_manifest.json` before the first run; odd rank
S→B/B→S/S→B, even rank B→S/S→B/B→S). No historical timing reused; no
capacity-rerun seconds used. Failures/reruns: **0** (rerun policy was
frozen in the manifest and never triggered).

Per-parent (median solver-reported seconds; T = med_S / med_B; B faster
iff T > 1):

| rank | parent | med_S | med_B | T | faster |
|---:|---|---:|---:|---:|---|
| 1 | 0,11,35 | 330.921 | 329.612 | 1.0040 | B |
| 2 | 11,38,44 | 72.292 | 70.720 | 1.0222 | B |
| 3 | 11,78,87 | 43.131 | 44.043 | 0.9793 | S |
| 4 | 12,24,68 | 50.733 | 53.400 | 0.9501 | S |
| 5 | 12,32,55 | 34.462 | 35.556 | 0.9692 | S |
| 6 | 13,52,57 | 55.612 | 54.597 | 1.0186 | B |
| 7 | 14,64,74 | 23.067 | 23.727 | 0.9722 | S |
| 8 | 23,44,45 | 41.099 | 39.710 | 1.0350 | B |
| 9 | 3,47,63 | 31.007 | 33.221 | 0.9333 | S |
| 10 | 3,53,84 | 39.914 | 37.812 | 1.0556 | B |
| 11 | 4,24,26 | 213.018 | 216.040 | 0.9860 | S |
| 12 | 4,42,54 | 37.796 | 42.532 | 0.8887 | S |

Secondary (all preregistered):

- median T = **0.982651**, gmean = 0.983485, mean = 0.984515;
- B faster 5/12, ties 0, S faster 7/12;
- aggregate median solver seconds: S 973.1 vs B 981.0
  (B costs +7.9 s per full-cohort pass; aggregate ratio 0.9919);
- aggregate median wall seconds: S 1001.5 vs B 1010.6 (+9.1 s);
- paired sign test (two-sided exact binomial, n=12): p = 0.7744;
- visited reduction = 0 exactly (every run S==B visited, by design).

### Primary endpoint

PASS requires BOTH median T > 1 AND B faster on >= 7/12.

**PRIMARY: FAIL** (median T = 0.9827 <= 1; B faster on 5/12).
No FAIL-SAFETY condition occurred; semantic parity held everywhere.

## 6. Mechanism finding (why bucketization did not help)

From the committed parity-run instrumentation (identical for S and B —
no instrumented timing runs; primary timing binary untouched):

- 193,606,274 nonterminal nodes sorted; 858,168,427 unique children
  (mean 4.43 children/node);
- child cached-class distribution: LOSS 12.4%, WIN 11.4%, unknown 76.2%;
- 36.0% of nodes have NO cached child at all (single `(count,key)`
  comparators only — bucket partition work is pure overhead there);
- cache changes the full order at 33.7% of nodes and the first child at
  21.5%.

So the single-sort comparator's per-comparison cost is dominated by the
`(count,key)` integer compares it must do anyway; the cached-class
recomputation it saves via bucketization is a small fraction of total
comparison work, and the two partition passes (up to 2n swaps plus
scanning all children twice) add cost on every cache-aware node,
including the 36% no-hit nodes and the 76% unknown-heavy children where
class-partitioning carries no ordering information. Net effect is a
small slowdown (~1.6–1.8% median), largest on parents with many
no-cache-hit nodes (e.g. 4,42,54: −0.111 T; −679 ns/node).

Per-parent ns/node deltas in `time_vs_visited.json`.

## 7. Interpretation (per prereg)

> Bucketization preserves exact semantics but does not improve runtime
> under this implementation/compiler/workload.

- The confirmed cache-aware ordering RESULT (visited reduction vs
  cache-blind) is unchanged; the search tree is identical between S and
> B (visited parity exact on all 72 runs).
- No claim is made that any heuristic reduced search work.
- Retain the current single-sort implementation.

Ideas recorded for separate future preregistrations only (not executed
here): none beyond what is already on file; this experiment's freeze
explicitly excluded new heuristics/capacity/ordering changes.

## 8. Provenance summary

- order-equivalence test receipt: PASS, 32,157 cases (this doc + committed test);
- source-diff audit: PASS;
- build receipt: `build_receipt.json` (binary/compiler/flags/HEAD/source hashes);
- parity receipt: `parity_receipt.json` + `parity_verifier.log` (verifier PASS);
- execution manifest (72-run order, sealed pre-run): `execution_manifest.json`;
- timing: `timing_summary.csv` (72 rows), `timing_analysis.json`;
- mechanism: `mechanism_stats.json`, `time_vs_visited.json`;
- raw per-run artifacts: `raw_parity/`, `timing/`.
