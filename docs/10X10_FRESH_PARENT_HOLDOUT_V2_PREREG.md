# 10x10 fresh-parent holdout v2 preregistration

Base SHA: `eaf40af27224ad5beb977dc401a787a59cefd2f0`

Purpose: test the already-fixed fresh-solver `memo_used` ascending rule on 3-stone parents selected without using parent game value, child outcome, LOSS witness, proof-family membership, or probe results.

## Parent universe and selection

Universe: every 3-cell subset of the 10x10 board, reduced to one lexicographically-minimal representative per D4 orbit.

Before hashing, conservatively exclude every D4 orbit whose 3-cell canonical key can be extracted from **any tracked text file** at the fixed base SHA. The implementation uses `git grep -I` over the entire tree rather than only selected directories, so a state appearing only in `tests/`, `cpp/`, `experiments/`, or another tracked path is still excluded. The exclusion parser is intentionally label-blind: it records state identities only and never reads WIN/LOSS fields, witness labels, probe scores, memo counts, or game values. Over-exclusion is acceptable; outcome-dependent inclusion is not.

This whole-tree exclusion rule was fixed before the v2 parent CSV was generated or any v2 probe/exact outcome was inspected.

Seed: `kyouen-10x10-fresh-parent-holdout-v2-2026-09-07`

For each remaining canonical triple `a,b,c`, compute SHA-256 of

`seed + "|" + "a,b,c"`

sort by `(digest, canonical triple)`, and take the first **24** parents. No parent may be replaced after any probe or exact outcome is inspected. If the exclusion parser leaves fewer than 24 parents, use all remaining parents and record that fact before probing.

The selected parent list and a manifest containing the base SHA, seed, universe count, exclusion count, selected count, and SHA-256 of the CSV must be committed before probes are run.

## Probe protocol

Primary budget: **1,000,000 visited states per child**.

Each legal child is probed in a fresh solver process / fresh Solver instance. No memo table, timer, counter, or solver state may be shared between children.

Primary ranking is frozen from the previous holdout:

1. probe-proved LOSS first;
2. unresolved children by ascending independent `memo_used`;
3. probe-proved WIN last;
4. ties by ascending move/cell index.

If all candidates remain unresolved at 1M, this reduces to pure `memo_used` ascending. Direction must not be reversed on this holdout.

## Exact outcomes and endpoint

Exact solving starts only after the complete 1M probe table and its protocol manifest are committed.

Every sampled parent remains in the report regardless of exact game value.

For a sampled parent having at least one exact LOSS child, primary endpoint is the rank of its first LOSS child under the frozen ranking. Parents having no LOSS child are reported as non-contributing to first-LOSS analysis rather than removed from the frozen sample.

For a parent with `m` legal children and `l` LOSS children, use the exact random-permutation distribution and its exact median. Across contributing parents classify frozen rank as better / tie / worse than that median. Primary directional test is the one-sided exact sign test over non-ties, with hypothesis `memo ascending better than random`, alpha = 0.05.

Always report individual ranks, LOSS counts, normalized rank, rank sum, and exact random expectation. Candidate-level AUC within each parent containing both LOSS and WIN children is secondary; report each AUC plus mean and median, not only pooled AUC.

## No rescue rule

The following are forbidden on this holdout after outcomes are observed:

- reversing memo direction;
- changing 1M primary budget;
- dropping or replacing sampled parents;
- choosing a subset based on LOSS density, proof family, solver difficulty, or effect size;
- modifying the primary statistic or alpha;
- promoting 10k/100k results to primary.

Any heuristic discovered from this holdout is exploratory and requires another independent holdout.

## Diagnostics

Depth-resolved instrumentation and 10k/100k probes may be collected as secondary diagnostics, provided they do not alter the 1M primary solver behavior or ranking definition.

`visited - memo_used` is not a memo-hit count and must not be interpreted as one.

## Interpretation

A favorable result supports repeatability beyond the proof-family-selected first holdout because parent identity is fixed without consulting outcomes. A null/adverse result weakens the generality of the memo-ascending signal and must be reported without post-hoc rescue.
