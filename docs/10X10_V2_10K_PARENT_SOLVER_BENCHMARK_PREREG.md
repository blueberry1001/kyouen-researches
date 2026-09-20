# 10×10 V2 10k parent-solver benchmark preregistration

Base commit: `b9e381f60986e02f93f4cade6c2be56854117b67`

This benchmark follows the completed clean-holdout V2 and fresh 10k probe study. It does **not** test the already-confirmed predictive direction again. Its purpose is operational: determine whether using the 10k memo signal actually reduces the work of solving a 3-stone parent with the real shared-memo solver.

## Why a new benchmark is required

The previous P5/P6 cost reconstruction summed exact costs measured by solving each 4-stone child in a fresh process / fresh `Solver`. That is internally valid for that child-independent experiment, but it is not the same execution model as solving a 3-stone parent directly.

In the native solver, a fresh parent solve constructs all root children once, initially orders them by cached outcome class, then `legal_move_count`, then canonical key, and evaluates them with one shared `Solver` / memo table. Work performed while solving an earlier root child can therefore affect later root children through the shared memo. The previous `file order` baseline is also not the native parent-solver ordering.

Consequently, the previous 10k result (median reconstructed ratio 0.847; aggregate 2002 s vs 2893 s file-order baseline) is evidence that the signal is economically promising, but it is **not** yet evidence of an end-to-end speedup over the current native parent solver.

## Frozen cohort

Use exactly the same 12 V2 parents from `results/10x10/clean-holdout-v2/parents.csv` / the existing V2 manifest at the base commit. No parent may be added, removed, or replaced.

Exact outcomes are already known. This is therefore a performance benchmark, not a blind outcome-validation experiment.

## Solver invariants

Use the same exact solver semantics, board rules, shrink/load settings, memo implementation, and recursive ordering as the V2 exact solver unless a change is explicitly required to inject the root ordering. Pin and report source SHA, binary SHA, compiler, flags, and all runtime parameters.

For every parent/strategy run, start a fresh process and fresh exact `Solver`. No memo may carry across parents or strategies.

The treatment's 10k probes must each use a fresh probe `Solver`; probe memo tables are **not** imported into the exact parent solve. Only the resulting root-child order is passed to the exact solve.

## Strategies

### A — native baseline (primary control)

Solve the 3-stone parent directly with the unmodified native exact solver.

At a fresh root the existing implementation orders root children by its normal recursive rule (cached outcome class, then lower legal-move count, then canonical key) and uses one shared memo while evaluating them.

This, not historical file order, is the primary operational baseline.

### B — 10k memo root ordering (primary treatment)

1. Enumerate the same root children as strategy A.
2. Run a fresh 10,000-visited probe for **every** root child.
3. Order root children by `(memo_used ascending, move id ascending)` exactly as in the completed 10k experiment.
4. Solve the parent exactly using one fresh exact `Solver`, forcing **only the root order** to this frozen probe-derived order.
5. Below the root, retain the native recursive ordering unchanged.

The treatment total includes all probe work.

No 100k, 1M, staged K, legal-count shortlist, or post-hoc hybrid is part of the primary benchmark.

## Implementation guard

Add the smallest possible root-order override to the solver. The override must affect only the first recursive expansion of the requested 3-stone parent. Recursive descendants must continue to use the existing native ordering.

Before benchmarking, regression-test that:

1. with no override, the modified binary exactly reproduces the original binary's parent outcome and visited count on a small deterministic set;
2. the supplied root order contains each unique canonical root child exactly once;
3. treatment and control produce the same exact parent outcome;
4. no exact outcome labels are read to construct the treatment order.

## Primary cost endpoint

Primary endpoint is **total visited-node work** per parent, because it is independent of machine scheduling and parallel wall-clock effects.

- `A_work = exact_parent_visited_native`
- `B_work = 10,000 * number_of_probed_children + exact_parent_visited_10k_order`
- `work_ratio = B_work / A_work`

If a probe terminates exactly before 10,000 visits, use its actual visited count; report this explicitly. Based on the completed V2 10k run, all probes are expected to exhaust at 10,000.

Report parentwise ratios plus median, geometric mean, aggregate `sum(B_work)/sum(A_work)`, and improved/tie/worse count.

Operational success criterion, fixed before execution:

- median work ratio < 1.0, and
- at least 7 of 12 parents have work ratio < 1.0.

This criterion is descriptive for this fixed cohort; no new population-level p-value is claimed.

## Secondary timing endpoint

Also record:

- exact solver-reported seconds;
- total probe solver-reported seconds;
- process wall time for each exact parent solve;
- orchestration wall time for the probe stage;
- end-to-end treatment wall time under the stated worker count.

Timing comparisons must distinguish serial-equivalent solver time from parallel wall time. Do not claim a CPU-work speedup solely from parallelizing probes.

For timing-noise control, execute A/B in deterministic counterbalanced order across parents (e.g. SHA256(parent) parity determines AB vs BA). Do not choose ordering after seeing timings.

## Secondary diagnostic endpoints

For A and B record:

- exact parent visited;
- exact parent memo_used;
- maxdepth;
- exact seconds;
- first root child actually evaluated / winning witness if available;
- number of root children entered before the parent is proved WIN, if instrumentation can record it without altering semantics.

These diagnostics are secondary and do not change the primary success criterion.

## Interpretation

Possible outcomes:

- **B wins primary endpoint:** 10k memo ordering has crossed from a ranking result to a genuine reduction in native parent-solver search work on V2.
- **B loses despite reconstructed P5 winning:** shared-memo interactions and/or the native legal-count baseline explain the discrepancy; the earlier file-order cost result must not be presented as solver speedup.
- **Mixed:** inspect parent-level shared-memo interactions, but do not tune the rule on these 12 parents.

## Post-primary work

The exploratory `C-K10-asc` staged strategy from P8 is explicitly post-hoc and excluded from this benchmark's primary treatment. If pursued, freeze it on a new cohort before outcomes / timings are inspected there.

Likewise, do not add 100k after observing this benchmark merely to rescue a negative result.
