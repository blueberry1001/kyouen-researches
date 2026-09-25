# D9 one-shot read-mask: same-key rewrite invariant

Status: implementation constraint frozen before D9LM1R/D9WM1R cohort execution.

## Problem

The preregistered read-mask control keeps the selected occupant physically live while making its current generation unreadable. A lookup therefore reports a miss even though the hash table still contains the same canonical key.

This creates a write-path hazard that is not covered merely by checking that lookup behaves like a miss. After recomputation, the solver may attempt an ordinary memo write for that same canonical key. If the insertion/update path sees the retained masked occupant and treats it as an ordinary existing hit, it can:

- suppress the write as "already present";
- update the value without advancing occupant generation;
- leave the old mask attached to the refreshed fact;
- change occupancy/replacement bookkeeping differently from the intended read-mask semantics.

Any of these can make D9LM1R/D9WM1R measure an implementation artifact rather than temporary withholding of the old memo fact.

## Required invariant

For a selected `(canonical_key, occupant_generation)` mask:

1. lookup of that exact masked generation behaves as a memo miss;
2. the first successful ordinary write of a recomputed fact for that canonical key must retire the mask **atomically with** establishing a new readable occupant generation;
3. after that write, a lookup of the key must return the newly written value exactly as it would in an unmasked run from the resulting table state;
4. mask identity is `(canonical_key, generation)`, never canonical key alone, so later independent occupants cannot inherit a stale mask;
5. a failed/aborted write must not retire the mask;
6. replacement of the physical slot by another key retires the old generation and therefore its mask.

Do not implement mask retirement as "remove mask on first attempted write". Retirement is tied to a successful generation transition.

## Mandatory microtests before cohort execution

Construct deterministic table-level tests for both LOSS and WIN occupants:

- masked lookup -> miss -> recompute -> successful same-key write -> immediate lookup returns the new readable fact;
- masked lookup -> miss -> failed write -> second lookup is still masked;
- masked occupant replaced by another key -> old mask cannot affect a later reinserted copy of the original key;
- two successive generations of the same key: masking generation `g` never masks `g+1`;
- mask enforcement disabled: byte-for-byte/event-for-event behavior equals the ordinary table path.

Record generation, mask state, slot identity, value, occupancy/replacement counters, and lookup result at every step. These are safety tests only; they do not alter the frozen treatment, selected keys, success criteria, or interpretation in `10X10_DEPTH8_TO_9_FIRST_BOUNDARY_MATCHED_CONTROL.md`.

## Interpretation boundary

The read-mask control holds physical table topology fixed at the intervention instant, not forever. Once a masked miss causes recomputation and a successful write, later table evolution may legitimately differ from baseline. The invariant above only ensures that this divergence begins from withholding the selected old memo fact rather than from stale-mask or same-key-write bookkeeping bugs.
