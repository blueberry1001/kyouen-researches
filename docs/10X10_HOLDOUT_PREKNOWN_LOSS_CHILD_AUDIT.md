# 10x10 holdout audit: pre-known LOSS children in the selected parent pool

Date: 2026-09-07
Base result branch: `blind-probe-holdout-validation` @ `2bcd387102874ee20ee641ebd7311c0101d849b5`

## Summary

The 11-parent fresh-memo holdout result is **not a fully child-outcome-blind holdout**.

All 11 selected parents came from pre-existing proof CSVs that already store at least one exact LOSS child (or a D4-canonical representative of that child) for the parent. Therefore the statement in `docs/10X10_HOLDOUT_CONFIRMATION_RESULT.md` that no holdout child overlapped previously classified repo states (`0/1020`) is too strong and, under raw-state identity, already false for multiple parents.

This does **not automatically invalidate** the memo-ascending ranking comparison on the frozen 11-parent set. The ranking rule was frozen before the new 1M probe outcomes and the parent selection did not explicitly use the new probe `memo_used` values. But the experiment must be interpreted as a prospective ranking test on parents whose WIN status was already certified via at least one known LOSS witness, not as a completely unseen child-level holdout.

## Evidence

Frozen parent selection:

`results/10x10/holdout-parent-selection-preregistered.csv`

uses two pre-existing sources:

- `results/10x10/two-stone-90-66-child-proof.csv`
- `results/10x10/two-stone-90-61-child-proof.csv`

For the selected rows, both source files explicitly contain `outcome=WIN`, `source=HAS_EXACT_LOSS_CHILD` (or an equivalent child-proof provenance), and a `loss_child` field.

| selected parent | pre-existing LOSS child representative | relation to literal child task |
|---|---|---|
| `0,36,50` | `0,31,36,50` | literal direct child |
| `9,33,54` | `9,33,54,63` | literal direct child |
| `0,1,13` | `0,1,10,13` | literal direct child |
| `0,7,31` | `0,7,31,64` | literal direct child |
| `0,17,31` | `9,12,31,38` | D4-equivalent direct child |
| `0,13,34` | `0,13,24,34` | literal direct child |
| `0,13,44` | `0,13,22,44` | literal direct child |
| `0,2,13` | `7,9,16,54` | D4-equivalent direct child |
| `0,3,13` | `0,30,31,38` | D4-equivalent direct child |
| `0,10,13` | `0,1,10,13` | literal direct child |
| `0,13,21` | `0,13,21,26` | literal direct child |

Thus all 11 parents had at least one child outcome known before the holdout exact sweep. Eight of the stored witnesses are literal supersets of the selected parent; the remaining three become literal direct children after a D4 transform of the parent.

A concrete contradiction to the `0/1020` claim is already visible without D4 normalization:

- parent `0,36,50` has pre-existing LOSS child `0,31,36,50` in `two-stone-90-66-child-proof.csv`;
- `results/10x10/blind-probe-holdout/exact_task_list.csv` contains exactly `0,31,36,50` (batch 1, position 8).

Likewise several other selected rows have literal pre-known LOSS children in the frozen task list.

## What remains valid

The following facts are not changed by this audit:

- candidate probes in the new run were fresh-Solver / fresh-memo;
- all 1020 new 1M probes were unresolved, so the preregistered ordering reduced to pure `memo_used` ascending;
- the 11-parent analysis yielded corrected first-LOSS ranks `1,1,1,1,1,1,1,6,1,1,1` and strong within-parent association;
- the old cumulative-memo result at `b5172a4` remains invalid and is not rescued by this audit.

The exact random-order p-value is still a valid benchmark **conditional on the frozen 11 parents and their observed LOSS sets**, provided the ranking was not constructed from those exact labels. What must be withdrawn is the stronger description that the child outcomes themselves were all previously unseen.

## Main remaining selection concern

The holdout is strongly family-structured:

- 2 selected parents came from the `90-66` child-proof family;
- 9 selected parents came from the `90-61` child-proof family.

Therefore the striking 10/11 rank-1 result may reflect a real search-statistic signal that is especially stable inside these proof families. It should not yet be generalized to arbitrary 10x10 3-stone WIN parents.

## Immediate low-cost reanalysis

Before spending more exact-solve compute, reanalyze the existing 11 parents after excluding every child state whose exact LOSS outcome was already encoded by the pre-holdout proof CSVs (matching under D4, not only raw string equality).

For each parent report:

- number of pre-known LOSS child orbits removed;
- first LOSS rank under memo-ascending before/after removal;
- AUC before/after removal;
- whether the rank-1 child was already pre-known.

If the effect remains strong after all pre-known witnesses are removed, that substantially reduces the contamination concern while retaining the current dataset as an exploratory robustness check.

## Required next confirmatory test

A second genuinely child-outcome-blind holdout should select parents **without using any pre-existing child proof / exact child label**.

Recommended design:

1. deterministically select D4-canonical safe 3-stone parents from a geometry/state-only pool using a fixed seed/hash;
2. exclude every parent/orbit previously used in probe-direction discovery or the first holdout;
3. freeze the parent set and the same memo-ascending 1M rule before any child exact outcomes are inspected;
4. run fresh 1M probes for every safe child;
5. exact-classify every child only after probes are frozen;
6. prespecify that primary analysis uses selected parents that turn out to contain at least one exact LOSS child, without replacing parents after labels are known;
7. record parent-selection yield as part of the result.

This would test whether the very large first-holdout effect survives outside the `90-61` / `90-66` proof-family selection mechanism.

## Terminology correction

Until that second holdout is run, describe the current result as:

> A preregistered fresh-memo ranking replication on 11 previously certified WIN parents, with child-level exact labels recomputed exhaustively; memo-ascending strongly outperformed random/default ordering on this frozen set.

Do not describe it as:

> 1020 completely previously-unseen child outcomes / a fully child-level blind holdout.
