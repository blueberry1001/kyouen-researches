# Depth-8 -> depth-9 value-label matched control

## Status

Preregistered supplement to `10X10_DEPTH8_TO_9_LOSS_MEMO_CAUSAL_ABLATION.md` before any D9LF/D9WF cohort execution.

## Why this control is needed

The frozen D9LF and D9WF interventions delete all surviving producer-owned depth-9 entries of different value classes. Therefore `visited(D9LF)-visited(B)` versus `visited(D9WF)-visited(B)` is a valid comparison of the two *full interventions*, but it is not by itself a clean value-label control: the number of surviving LOSS and WIN entries eligible for deletion can differ at each depth-8 parent boundary. A larger D9LF effect could reflect more deleted entries rather than greater future value per LOSS entry.

Do not change or replace the original endpoints. Add a count-matched diagnostic.

## Frozen matched intervention

At each depth-8 producer-parent exit, let:

- `L` be the still-live producer-owned depth-9 LOSS entries eligible for D9LF;
- `W` be the still-live producer-owned depth-9 WIN entries eligible for D9WF;
- `k = min(|L|, |W|)`.

Define two additional variants:

- `D9LM`: invalidate exactly `k` entries from `L`;
- `D9WM`: invalidate exactly `k` entries from `W`.

Selection must be deterministic and independent of table slot, insertion time, search order, and future reuse. For each canonical memo key compute the same fixed 64-bit hash with a repository-fixed seed, sort eligible entries by `(hash, canonical_key)`, and take the first `k`. Freeze the concrete hash function and seed in code/tests before cohort execution.

If `k = 0`, both matched interventions are inert at that boundary.

The same tombstone/lazy-invalidation semantics and ownership definition as D9LF/D9WF apply. Do not alter move ordering or any non-target memo behavior.

## Measurements

For every frozen parent report:

- `visited(D9LM) - visited(B)`;
- `visited(D9WM) - visited(B)`;
- total matched deletions in each variant (these must be equal);
- sign of `visited(D9LM) - visited(D9WM)`.

Across the 12-parent cohort report totals, medians, sign counts, and the aggregate matched-deletion count. Because search trajectories may diverge after the first intervention, equality of deletion counts is required boundary-by-boundary only while the two matched variants still share the same pre-boundary trace; after divergence, report realized counts separately and do not claim a perfectly paired per-entry treatment.

## Interpretation

- Full D9LF >> D9WF and matched D9LM >> D9WM supports LOSS-specific future value more strongly than the original full-intervention contrast alone.
- Full D9LF >> D9WF but matched D9LM ~= D9WM suggests that deletion volume/composition, rather than the value label itself, may explain much of the full contrast.
- Matched D9WM > D9LM argues against the simple LOSS-specific mechanism even if the full interventions differ.

This diagnostic does not estimate an additive per-entry causal effect; memo reuse is trajectory-dependent and nonlinear.

## Safety additions

Before cohort execution require:

1. on an identical synthetic eligible set, D9LM and D9WM delete exactly `k` entries;
2. permutation of physical table slots leaves the selected canonical-key set unchanged;
3. reinsertion/replacement history that leaves the same live canonical-key set leaves selection unchanged;
4. hash ties are resolved only by canonical key;
5. `k=0` is metamorphically inert;
6. disabling matched deletion reproduces B exactly.
