# Preregistration: F-E R-outside 4-stone holdout

Date: 2026-09-21
Base: `224f0dae89f95bfafa20290e872d96b9567dc6d7`
Status: **FROZEN BEFORE HOLDOUT OUTCOMES ARE COLLECTED OR INSPECTED**

## Question

Finding F-E was discovered inside the 70 four-stone subsets of the selected 8-stone LOSS route R = `{90,61,2,73,69,66,13,91}`. In that development set, LOSS states have larger `Sigma d` than WIN states. This experiment asks only whether the **direction** generalizes outside R:

`P(LOSS | high Sigma d) > P(LOSS | low Sigma d)`.

No claim about the R-development effect size is required for success.

## Clean universe

1. Enumerate all 10x10 four-stone states and reduce by the solver's D4 canonicalization.
2. Require the state itself to be legal/safe (it contains no dangerous four-point set).
3. Exclude the **entire D4 orbit** of every four-stone subset of R. Operationally, canonicalize all `C(8,4)=70` development states first, collect their canonical keys, and exclude those keys from the canonical universe. Merely testing whether the chosen canonical representative is literally a subset of the raw R is insufficient, because a D4-equivalent representative need not use point IDs from R.
4. Exclude every D4 orbit whose four-stone state/outcome occurs anywhere in git history at freeze base `224f0da`, including result CSV/JSON, certificates, probe/holdout/benchmark artifacts, docs containing explicit labelled states, and outcome caches. Exclusion is by canonical key, not raw spelling.
5. Selection code may use geometry and `Sigma d`, but MUST NOT read game outcome, solver memo, proof witness, visited count, or any descendant-derived feature.

For rule 4, **git history** is frozen operationally as every commit reachable by parent traversal from the full base SHA `224f0dae89f95bfafa20290e872d96b9567dc6d7`, including blobs that were later modified or deleted. An implementation that scans only the base checkout/tree is non-conforming. The audit must traverse the reachable commit/blob history (for example via `git rev-list --objects 224f0dae89f95bfafa20290e872d96b9567dc6d7`) and record enough provenance to identify the source commit and path for each excluded labelled four-stone canonical key. Commits or blobs that exist only on refs not reachable from the frozen base are outside this holdout's frozen knowledge set and MUST NOT be added later merely because they are visible at solve time.

If a historical artifact cannot be parsed automatically (for example a binary/large certificate), it must be either (a) parsed by a deterministic documented extractor before the manifest is frozen, or (b) conservatively represented by a documented exclusion source derived without inspecting any selected holdout outcome. Silent omission because the blob is absent from the current checkout is not allowed.

The exclusion list and its source-path audit are frozen before solving any selected state.

## Geometry score

For each board point p, `d(p)` is the exact number of 10x10 dangerous quadruples (concyclic or collinear) containing p, computed by integer determinant as in `scripts/analysis/quadruple_stats.py`.

For state S, `Sigma d(S) = sum(d(p) for p in S)`.

No alternate geometry score may replace or be combined with this score on this holdout.

## Frozen sampling

After exclusions, sort the clean canonical universe by the tuple `(Sigma d, canonical_state)`. Let `N` be its size and `q = floor(N/5)`. Define the strata by exact Python-style half-open slices of that sorted list:

- LOW: `sorted_states[0:q]`
- MID: `sorted_states[floor(2*N/5):floor(3*N/5)]`
- HIGH: `sorted_states[N-q:N]`

Thus LOW and HIGH each contain exactly `floor(N/5)` states; MID uses the fixed 40%-to-60% rank interval. No alternate percentile convention or rounding rule is permitted.

`canonical_state` has one frozen textual serialization everywhere selection or hashing depends on it: sort the four canonical point IDs numerically ascending, encode each as unsigned ASCII decimal with no leading zeros, and join them with a single ASCII comma. There are no brackets, spaces, quotes, or trailing newline. Example: the state with point IDs 4, 9, 33, 57 serializes exactly as `4,9,33,57`.

Within each stratum rank candidates by ascending SHA-256 digest interpreted lexicographically as its 64-character lowercase hexadecimal representation. The hashed byte string is exactly UTF-8/ASCII

`kyouen-10x10-f-e-r-outside-v1-20260921:` + `canonical_state`

with no BOM, NUL, whitespace, or newline before or after it. Select the first 12 states per stratum: 36 states total. Because `(Sigma d, canonical_state)` totally orders the pre-slice universe and SHA-256 of the frozen serialization orders candidates within a stratum, no implementation-dependent tie handling remains. No replacement or state dropping is allowed after the 36-state manifest is frozen, except a solver/infrastructure failure that prevents an exact result; every such failure remains in the report and is not replaced.

Before exact solving, commit:

- this preregistration;
- complete canonical exclusion list plus source audit;
- clean-universe counts and stratum boundaries;
- the 36-state sampling manifest containing raw/canonical state, stratum, `Sigma d`, and selection hash;
- solver source commit/digest and exact-run protocol.

## Exact solving

Use the repository's validated 10x10 exact solver with a fresh process and fresh memo for each state. Use the same fixed solver configuration for all 36 states. Exact classification has no visited-node budget; resource/time failures are censored failures, not outcomes and not reasons to substitute another state.

Raw solver output must be committed before aggregate endpoint analysis.

## Primary endpoint

Primary statistic:

`Delta = LOSS_rate(HIGH) - LOSS_rate(LOW)`.

Success criterion: `Delta > 0`.

Report the raw 2x2 HIGH/LOW counts and an exact two-sided Fisher test as descriptive uncertainty. The sign criterion, not p<0.05, is the preregistered success rule because n=24 for the primary contrast is intentionally a small confirmatory screen.

If either HIGH or LOW has an unsolved/censored state, primary status is `INCOMPLETE`; do not silently analyze only completed states as the confirmatory endpoint.

## Secondary endpoints

On all 36 completed states, report without changing the primary decision:

1. AUC for `Sigma d` discriminating LOSS from WIN (LOSS is positive).
2. Rank-biserial effect size.
3. Mean and median `Sigma d` by outcome.
4. Spearman association between `Sigma d` and binary LOSS label.
5. LOW/MID/HIGH LOSS counts and rates.
6. Exact conditional label-randomization statistic for the observed number of LOSS labels, clearly marked descriptive because sampled states are not an iid population sample.
7. Exact visited and wall-time distributions by stratum/outcome as exploratory solver-cost diagnostics only.

## Interpretation gates

- `Delta > 0`: F-E's **direction** survives a clean R-outside holdout; R-specific combinatorics alone no longer explain the observation.
- `Delta = 0`: no directional replication.
- `Delta < 0`: directional contradiction on this holdout.
- The cohort MUST NOT be enlarged, strata changed, or seed changed after labels are inspected. Any revised hypothesis requires a new holdout.
- Because selection deliberately samples score extremes, the observed LOSS rates are not estimates of the unconditional prevalence of LOSS among all four-stone states.

## Non-claims

This experiment does not establish causality of `Sigma d`, does not estimate the population LOSS rate, does not validate a move-order heuristic, and does not turn the within-R label-randomization p-value into a population significance claim.

## Planned artifacts

- `results/10x10/f-e-r-outside-holdout/exclusion.csv`
- `results/10x10/f-e-r-outside-holdout/exclusion_audit.json`
- `results/10x10/f-e-r-outside-holdout/sampling_manifest.csv`
- `results/10x10/f-e-r-outside-holdout/sampling_manifest.json`
- `results/10x10/f-e-r-outside-holdout/exact_raw.csv`
- `results/10x10/f-e-r-outside-holdout/summary.json`
- `results/10x10/f-e-r-outside-holdout/REPORT.md`
