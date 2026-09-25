# D9 one-shot read-mask: same-key rewrite semantics correction

Status: implementation constraint frozen before D9LM1R/D9WM1R cohort execution.

## Newly identified problem

The previous read-mask notes describe retirement after a "successful same-key generation transition" / normal rewrite. The production memo implementation does not currently have such a transition.

At depth 9, `MultiDepthMemo100` uses `RankCompactTable`. Its `try_put(rank, value)` probes the existing occupant and, when the same rank is already present with the same outcome, simply returns `true`; it does not rewrite the slot, create a new generation, or otherwise distinguish a recomputed fact from the old stored fact. `RankFlat17` has the same idempotent same-key behavior at depth 17.

Therefore a mask keyed only by the existing physical occupant cannot safely retire merely because `try_put` returned success. Doing so would make an idempotent no-op write look like a new memo generation. Conversely, never retiring it would cause the selected fact to remain hidden indefinitely, which is not the intended one-shot intervention.

## Corrected implementation rule

For D9LM1R/D9WM1R, generation must be an experiment-side logical epoch, not inferred from physical slot replacement.

For each selected depth-9 rank:

1. record `epoch = 0` and mask `(rank, epoch=0)` at the intervention boundary;
2. while that mask is live, every ordinary read of that rank at both entry and child-prefetch sites returns miss;
3. after the solver actually recomputes that state and reaches the memo write with the same outcome, treat that completed recomputation as the explicit logical transition to `epoch = 1`, even though production `try_put` is physically idempotent;
4. retire only the `(rank,0)` mask after the recomputation has completed and the outcome-consistency check/write has succeeded;
5. subsequent reads of the unchanged physical slot are interpreted as the recomputed `epoch=1` fact and are readable normally;
6. a `try_put` success not causally preceded by recomputation of the masked state must not retire the mask.

The epoch sidecar is experimental metadata only. It must not change probing, occupancy, ordering, replacement, or production memo bytes.

## Mandatory microtest amendment

The existing same-key rewrite and access-path tests must additionally prove:

- physical depth-9 slot bytes before and after recomputation are identical under the current idempotent `try_put` path;
- nevertheless the experiment-side epoch changes exactly once, from 0 to 1;
- the old generation is masked at both read sites before that transition;
- the same physical slot becomes readable at both sites only after the explicit logical transition;
- calling `try_put` directly for the selected key without a completed masked-state recomputation cannot retire the mask;
- with masking disabled, no epoch bookkeeping changes solver outcome, visited count, memo occupancy, or event trace.

## Interpretation

This preserves the intended read-mask intervention: withhold an already-known memo fact once, force one genuine recomputation, then allow the recomputed fact to be reused. It also avoids adding tombstones or physical rewrites to a depth-9 table whose production implementation currently has neither mechanism.
