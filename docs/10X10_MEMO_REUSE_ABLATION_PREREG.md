# 10x10 memo-reuse ablation preregistration

Base commit: `80b734b265a698370c33631bc8c9771c8fc645e2`

This document is frozen **after** the below-root instrumentation cohort and
**before** any memo-ablation solver result is generated. It does not alter the
completed root-order or instrumentation endpoints.

## Motivation from the completed instrumentation cohort

Across the 12 native V2 parents:

- exact visited: 225,422,484
- node-entry memo lookups: 225,422,484
- node-entry hits: **0**
- child-prefetch lookups: 858,168,427
- child-prefetch hits: 204,133,384 (23.79%)
- cached child evaluations consumed: 121,051,417 / 346,473,889 (34.94%)
- cached LOSS evaluations consumed: 80,710,588
- cached WIN evaluations consumed: 40,340,829
- WIN returns directly from cached LOSS child: 80,710,588 / 153,066,536 solved-WIN nodes (52.73%)
- cache changes first child vs `(legal_move_count,key)` fallback at 41,677,154 / 193,606,274 nonterminal nodes (21.53%)

Two observations now need causal tests:

1. The node-entry lookup consumed about 20.8% of all memo `get` calls but had
   zero hits in this cohort. It may be redundant in ordinary exact solve.
2. Child-prefetch reuse is substantial, especially cached LOSS: every consumed
   cached LOSS in this cohort corresponds to an immediate WIN return.

The instrumentation itself cannot tell how much runtime the zero-hit entry
lookup costs, nor whether cached-priority ordering is beneficial after
separating it from cached recursive-call omission.

## Scope and invariants

Use the same 12 V2 parents and the same native solver semantics/settings as the
completed parent benchmark and instrumentation cohort.

Do not change:

- game semantics
- canonicalization
- duplicate removal
- legal-move computation
- memo table implementation/capacity/load settings
- root ordering
- child fallback ordering `(legal_move_count asc, canonical key asc)`
- certificate/witness code except where a variant is explicitly confined to
  the ordinary exact-solve path

`main` must not be modified.

## Experiment E: node-entry lookup removal

### Hypothesis E1

For ordinary exact parent solve, removing the `memo_.get(key, depth)` lookup at
`win()` entry while retaining all existing child-prefetch lookups will preserve
outcome, visited, memo-used, maxdepth, root diagnostics, and witness on all 12
parents.

### Critical implementation constraint

This variant must be confined to the ordinary exact-solve recursion used by the
parent benchmark. Do **not** silently remove lookup behavior needed by
certificate generation or other callers unless separately demonstrated safe.

No compensating/new memo lookup may be added.

### Primary validity endpoint

Exact semantic/work parity with frozen native baseline, 12/12:

- outcome
- visited
- memo used
- maxdepth
- root unique
- root entered
- root first key
- root witness

Any mismatch rejects the optimization regardless of timing.

### Timing endpoint

Only if semantic/work parity is 12/12:

- per-parent solver-seconds ratio `E0/native`
- median ratio
- geometric-mean ratio
- aggregate solver-seconds ratio

Wall time is secondary because scheduler noise is larger.

No success threshold is fixed for timing; report the complete effect including
regressions. The main scientific question is whether the 225M observed zero-hit
lookups are removable without changing search.

## Experiment O: isolate cached-priority ordering

Run only after Experiment E is interpreted or independently from the same
frozen base.

### Variant O0

Retain the existing child-prefetch lookup and retain cached outcomes for
recursive-call omission, but do **not** use `cached` as a sort priority.

Sort children only by the native fallback:

`(legal_move_count ascending, canonical key ascending)`

When a child is reached in the loop, its already-prefetched cached outcome is
still consumed exactly as in baseline; do not force recursion for a cached
child.

Thus O0 changes ordering only. It does not disable memo reuse.

### Hypothesis O1

The existing cached-priority order reduces exact visited relative to O0.

### Primary endpoint

Per-parent exact visited ratio `O0/native` on the same 12 parents.

Report:

- median ratio
- geometric-mean ratio
- aggregate ratio
- improved/tie/worse count from the perspective of native cached ordering

### Secondary endpoints

- solver seconds
- root entered
- root first/witness
- memo used
- maxdepth

Outcome must remain identical 12/12; otherwise treat as implementation failure.

## Why there is no full "memo off" experiment yet

A complete memo-disable ablation simultaneously removes:

- transposition reuse
- cached child recursion omission
- cached LOSS immediate WIN proof
- cached-priority ordering

and may multiply work enough to be expensive. It is also mechanistically
confounded. E and O are smaller causal interventions and should be completed
first.

If O shows little or negative ordering benefit, the remaining memo benefit is
mainly transposition/cached-outcome reuse. If O strongly favors native, cached
LOSS ordering is an important independent mechanism.

## Predeclared interpretation

- **E semantic parity + faster:** remove/bypass node-entry lookup in ordinary
  exact solve is a justified implementation optimization candidate.
- **E mismatch:** entry lookup catches a state transition not observed by the
  instrumentation counters as interpreted; inspect the first divergent parent
  before any optimization claim.
- **O0 worse:** cached-priority ordering has causal value below root.
- **O0 approximately equal:** memo's main value is cached outcome reuse, not
  reordering.
- **O0 better:** cached-priority ordering is actively harmful despite its high
  use rate; redesign ordering before any deeper memo-capacity work.

## Not authorized by this preregistration

- 100k/1M probe cohorts
- new root heuristics
- memo capacity tuning
- memo table replacement
- proof/certificate reuse changes
- combining E and O into one treatment before their individual effects are
  measured

Commit this preregistration before implementing either ablation. Results must
be kept even if negative.
