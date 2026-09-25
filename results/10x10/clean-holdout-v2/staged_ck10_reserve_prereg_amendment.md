# Pre-data amendment: C-K10-asc reserve endpoint

Status: protocol correction before inspecting or generating reserve exact/probe outcomes.

## Problem found

The original reserve preregistration (`staged_ck10_reserve_prereg.md`) defines its comparator and treatment exact cost as sums of fresh-process child solves. That recreates the desk-style endpoint already shown to disagree with native parent-solver behavior under shared memo. The parent-solver benchmark report explicitly concluded that a future C-K10-asc validation requires a native parent-solve endpoint, not a desk reconstruction.

Therefore the original primary endpoint is not suitable for confirmatory claims about solver speedup. This amendment is made before reserve outcomes are inspected; the cohort, K=10 selection rule, 10k probe budget, ordering direction, tie-breaking, fallback rule, and frozen reserve parents are unchanged.

## Corrected primary comparison

For each reserve parent, run two fresh parent-solver processes from identical empty memo state:

- **A (native baseline):** production/native root ordering, unchanged solver semantics.
- **B (C-K10-asc):** enumerate the same canonical legal root children; rank by `legal_move_count` ascending with frozen child/file order as tie-break; probe only the first K=10 in independent fresh probe processes; order those ten by `(memo_used ascending, move ascending)`; present that ordered head to the *same parent solver with one shared memo table for the entire parent solve*; if no LOSS occurs in the head, continue the remaining root children in frozen original order, excluding the head.

Probe work is charged to B. Exact work is measured inside the single native-style parent solve, preserving shared-memo interactions among root children.

Primary work metric:

`work_A = parent_A_visited`

`work_B = 10000 * number_of_completed_probes + parent_B_exact_visited`

and per-parent

`ratio_work = work_B / work_A`.

Wall-clock seconds are secondary because probe parallelism and machine noise make them less stable. Record `parent_B_exact_visited / parent_A_visited` separately to distinguish probe overhead from ordering effects.

## Frozen decision rule

Retain the original four thresholds, but apply them to `ratio_work` rather than desk-style summed child seconds:

1. median `ratio_work` across the 12 reserve parents < 0.75;
2. at least 9/12 parents have `ratio_work < 1.0`;
3. aggregate `sum(work_B) / sum(work_A) < 0.75`;
4. no reserve parent has `ratio_work > 2.0`.

All four are required for confirmatory success.

## Required guards

Before reserve execution, verify on already-used non-reserve parents that:

1. A reproduces production outcome and visited count exactly;
2. A and B enumerate identical canonical root-child sets;
3. B differs from A only in root ordering plus the separately charged independent probes;
4. parent A and parent B each use one fresh memo table shared across that parent's entire exact solve;
5. probe processes never share memo state with each other or with the exact parent process;
6. repeated 10k probes are deterministic in outcome, visited and `memo_used`.

Do not inspect reserve outcomes while implementing or debugging these guards.

## Interpretation

The original desk endpoint may still be reported as a descriptive secondary analysis, but it cannot establish solver speedup. A reserve success claim must use the corrected native parent-solver work endpoint above. If implementation of B cannot preserve production parent semantics apart from root order, stop rather than substitute fresh child sums.
