# 10x10 holdout preflight audit

Date: 2026-09-06
Branch: `blind-probe-holdout-validation`
Audited head before this note: `154eedc813758b395027b66ecbef1a69a62b0402`

This audit is intentionally performed before any holdout probe-output file exists.
At the audited head, `results/10x10/blind-probe-holdout/` does not exist, so no
holdout probe measurements were available while making the checks below.

## 1. Preregistered protocol remains intact

The primary protocol in `docs/10X10_PROBE_HOLDOUT_PREREGISTRATION.md` is:

- fresh solver process for every child;
- 1,000,000 visited states as the primary budget;
- ranking = proved LOSS first, unresolved by ascending independent `memo_used`,
  proved WIN last;
- ascending move index as tie-break;
- first exact-LOSS rank vs the exact random-permutation distribution as the
  primary endpoint;
- one-sided parent-level sign test, with no post-outcome direction/budget/
  parent-subset changes.

`scripts/run_probe_holdout_independent.py` enforces a one-line temporary input
and a distinct solver process per child.  It does not read exact child outcomes
or rank children.  This removes the shared-memo failure mode that invalidated
the original blind-probe validation.

## 2. Parent-selection ordering discrepancy

The preregistration says to D4-canonicalize eligible parents, deduplicate, sort
lexicographically by canonical triple, and take the first 20; if fewer than 20
eligible parents exist, use every eligible parent.

The committed file
`results/10x10/holdout-parent-selection-preregistered.csv` contains 11 parents,
and its rows are **not displayed in lexicographic canonical-parent order**.  For
example, canonical `0,5,63` and `0,36,55` precede `0,1,13`.

This is a procedural discrepancy worth recording before execution.  However,
for the currently frozen 11-parent set, row order does not affect membership or
any preregistered statistic: all 11 rows are used, the runner enumerates every
selected parent, and primary analysis is parent-wise rather than based on
selection index.  Therefore the safe correction is **not** to choose a new
subset after this point.  The 11 committed identities remain frozen; the CSV
row order must not be treated as a statistical ordering.

If a future holdout has more eligible parents than its cap, selection must be
performed by a deterministic script that canonicalizes, deduplicates, sorts,
and writes the selected membership before any probe outcomes are generated.

## 3. Isolation and resumability checks

From `scripts/run_probe_holdout_independent.py`:

- parent identities come only from the committed holdout-selection CSV;
- child states come only from pre-existing immutable batch files;
- duplicate `(parent,state)` tasks are rejected;
- each child is passed alone to a fresh solver process;
- output is flushed after each row and resumable;
- `--check` rejects extra rows outside the frozen task set and reports missing
  rows.

The output path is
`results/10x10/blind-probe-holdout/independent_probe_1000000.csv`.
At this audit point the directory does not yet exist in the branch.

## 4. Interpretation guard

The earlier result `fixed first LOSS median 3 vs random median 6` from
`b5172a4` remains invalid because `probe_memo` was cumulative across candidates
inside a shared solver process.  This holdout tests the corrected *fresh-memo*
direction and must be interpreted independently of that old verdict.

No 9x9 `O=0` conclusion is imported here; the 9x9 filtered-response definition
artifact is documented separately in
`docs/9X9_PAIRSUM_METRIC_DEFINITION_CORRECTION.md`.

## Decision

Proceed with the frozen 11-parent membership and the preregistered 1M fresh-
solver protocol.  Treat the non-sorted CSV row order as a documented
presentation/selection-procedure deviation with no effect on this membership.
Do not alter the 11-parent set after probe outcomes become available.
