# D9 one-shot read-mask: recomputation-causality token

Status: implementation constraint frozen before D9LM1R/D9WM1R cohort execution.

## Newly identified ambiguity

The logical-epoch correction requires a mask to retire only after the solver has genuinely recomputed the selected masked depth-9 state and completed the matching memo write. The current production `MultiDepthMemo100::put` interface, however, carries only `(state, depth, outcome)`. A successful `put` by itself cannot prove that the corresponding invocation entered because the selected fact was masked; `RankCompactTable::try_put` is idempotent for an already-present same-key/same-outcome entry.

A global `recomputing_masked_key` flag is also unsafe. `win()` is recursive, so a masked depth-9 invocation can contain arbitrary deeper memo writes before its own return. Those writes must not retire the depth-9 mask, and nested/re-entrant experimental calls must not overwrite one another's provenance.

## Required implementation rule

Mask retirement must be tied to the exact `win()` invocation that crossed the masked depth-9 entry read.

1. At node entry, perform the mask-aware memo read and distinguish `ordinary miss` from `masked hit suppressed to miss`.
2. If and only if depth is 9 and the selected `(rank, epoch=0)` was suppressed, create an invocation-local recomputation token containing at least the canonical rank, old outcome, and epoch 0.
3. Carry that token only in the current `win()` stack frame. Child recursion and unrelated memo writes do not inherit it.
4. When that exact frame reaches its terminal/WIN/LOSS return write, first require the recomputed outcome to equal the stored old outcome. A mismatch is a hard experimental failure, not a new epoch.
5. Execute the ordinary production memo write. Only after it succeeds may that frame atomically retire `(rank,0)` and advance the experiment-side epoch to 1.
6. Early return from an ordinary cache hit never owns a token. Exceptions / `TableFull` / aborted writes leave the mask live.
7. Child-prefetch suppression alone never creates a retirement token; the token is created only if the child is actually entered while its depth-9 entry read is still masked.

The token is experimental control flow only and must not alter child ordering except through the intended masked read result, production memo bytes, probing, occupancy, or replacement.

## Mandatory microtests

- suppressing a selected key only at child-prefetch, then retiring its mask elsewhere before child entry, must make the later entry an ordinary cache hit and must not create a recomputation token;
- a selected masked depth-9 entry creates exactly one frame-local token; deeper depth-10+ writes cannot retire it;
- the token retires the mask only at its own depth-9 return write after outcome equality and write success;
- forced outcome mismatch aborts the experiment with the mask still live;
- forced write failure / `TableFull` leaves the mask live;
- two selected ranks recomputed in separate calls cannot retire each other's masks;
- with masking disabled, token bookkeeping is absent and outcome, visited count, memo occupancy, and event trace remain byte-for-byte / value-for-value baseline-equivalent where applicable.

## Why this matters

Without invocation-local provenance, the experiment can accidentally treat an idempotent write as evidence of recomputation or retire a mask because of unrelated recursive activity. The one-shot read-mask contrast would then no longer mean “withhold this known fact until this state is genuinely recomputed once.” This token makes that causal statement executable without changing the production table representation.
