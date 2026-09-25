# D9 one-shot read-mask: access-path invariant

Status: implementation constraint frozen before D9LM1R/D9WM1R cohort execution.

## Problem

`Solver::win` does not consume memo facts only through the current-state entry lookup. A child-prefetch lookup populates `Child.cached` before sorting, and a populated `Child.cached` is later consumed directly without calling `win` for that child. This is already documented in `notes/depth5-memo-warming-pathway-split.md`.

Therefore a D9 read-mask implemented only at node-entry lookup is not an intervention that withholds the selected memo fact. A selected generation may be copied into `Child.cached` during prefetch and then bypass the masked entry lookup entirely. Such an implementation can understate the treatment, or produce different LOSS/WIN effects merely because the two labels are encountered through different access paths.

## Required invariant

For every selected `(canonical_key, occupant_generation)` in D9LM1R/D9WM1R:

1. every ordinary solver read of that exact generation must observe a miss while the mask is live, including child-prefetch reads and current-state entry reads;
2. no `Child.cached`, execution-only cached field, ordering class, or other transient copy created after mask activation may retain the masked value;
3. if a transient copy of that generation was created before mask activation, the experiment must prove that it cannot be consumed after the intervention boundary; otherwise the boundary is invalid for that key/run;
4. after a successful same-key generation transition retires the mask under `10X10_D9_READ_MASK_IMPLEMENTATION_INVARIANT.md`, subsequent prefetch and entry reads may observe the new generation normally;
5. mask-disabled execution must remain event-for-event identical to baseline.

The implementation should preferably enforce masking in the common memo-read primitive used by both access sites. If the two sites do not share a primitive, both must be instrumented and the test below is mandatory.

## Mandatory access-path microtest

For both LOSS and WIN values, construct a deterministic state where the selected memo key is reachable through child-prefetch. With the mask active:

- child-prefetch reports unknown/miss and does not populate an executable cached value;
- reaching the child cannot bypass recursion via the old generation;
- an entry lookup for the same old generation also reports miss;
- after recomputation and successful same-key write, a new generation is readable by both prefetch and entry paths.

Record `(key, generation, access_site, mask_hit, returned_value, Child.cached state)` for each read. Require at least one exercised read at each access site; a test that never reaches one site is not a pass.

## Interpretation boundary

This does not change the frozen treatment or selected keys. It closes an implementation hole: D9LM1R/D9WM1R are intended to compare withholding selected old LOSS versus WIN memo facts, not merely withholding them at one of the solver's two memo-consumption paths.
