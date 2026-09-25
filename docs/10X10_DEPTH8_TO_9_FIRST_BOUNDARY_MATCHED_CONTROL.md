# Depth-8 -> depth-9 first-boundary matched causal control

## Status

Preregistered before any D9LF/D9WF/D9LM/D9WM cohort execution. This supplements, and does not replace, the frozen full and count-matched interventions.

## Motivation

The count-matched D9LM/D9WM diagnostic equalizes deletion count only while the two variants share the same pre-boundary trace. After the first effective deletion, their search trajectories may diverge; later eligible sets and realized deletion counts are then endogenous consequences of earlier treatment. Aggregate D9LM versus D9WM therefore cannot be interpreted as a fully paired value-label contrast even when the first boundary is perfectly matched.

Use a one-shot intervention to isolate the first causal divergence.

## Frozen intervention

For each frozen parent, run baseline B until the first depth-8 producer-parent exit at which both live producer-owned depth-9 LOSS and WIN sets are non-empty. Call this boundary `t*`.

At `t*` only:

- let `L` and `W` be the eligible live producer-owned LOSS and WIN entries;
- let `k = min(|L|, |W|)`;
- `D9LM1`: invalidate exactly `k` LOSS entries using the already-frozen deterministic `(hash, canonical_key)` selection rule;
- `D9WM1`: invalidate exactly `k` WIN entries using the same rule.

After `t*`, perform no further experimental invalidation. Ordinary memo replacement and solver behavior continue unchanged.

If no boundary with `k > 0` exists, mark the parent `NO_ELIGIBLE_BOUNDARY`; do not substitute a later depth or relax the eligibility rule.

The two variants must be forked from the identical pre-`t*` physical memo-table state, not merely from an equivalent logical key/value map. The fork state includes every slot's key/value, live/tombstone state, owner metadata, and all occupancy/replacement bookkeeping that can affect later lookup or insertion behavior. Preferred implementation is an exact in-memory clone at `t*`. Independent replay is valid only when both logical and physical-state digests, plus the trace through `t*`, are verified identical. Rebuilding a fresh table from the logical map is not a valid fork because slot placement and replacement state may differ.

Thus the treatment dose is exactly matched at the moment of intervention and cannot be altered by treatment-induced trajectory divergence.

## Read-mask topology control

Count matching does not by itself isolate memo value from hash-table topology. `D9LM1` and `D9WM1` necessarily invalidate different keys, so even with equal `k` they may create tombstones in different probe-chain locations. If tombstone placement changes later lookup/insertion/replacement behavior, part of `visited(D9LM1) - visited(D9WM1)` could be caused by physical deletion topology rather than by the unavailable LOSS versus WIN information.

Before cohort execution, add a one-shot read-mask diagnostic using the same `t*`, the same frozen selected key sets, and the same exact pre-`t*` fork state:

- `D9LM1R`: do not physically delete the selected LOSS entries. Mark their current occupant generation unreadable so a lookup of that exact key/generation is forced to behave as a memo miss;
- `D9WM1R`: identically mask the selected WIN entries;
- the underlying slot key/value/live state, probe-chain topology, occupancy counters, replacement bookkeeping, and owner metadata remain physically unchanged at `t*`;
- once a masked key is recomputed and ordinarily written as a new occupant generation, that new generation is readable. The mask must not suppress future independently produced values for the same canonical key;
- no additional mask is introduced after `t*`.

The read-mask variants are diagnostics, not replacements for the frozen deletion intervention: they estimate the effect of withholding the selected memo information while holding immediate table topology fixed, whereas D9LM1/D9WM1 estimate the effect under actual forgetting semantics.

Report `visited(D9LM1R)-visited(B)`, `visited(D9WM1R)-visited(B)`, and `visited(D9LM1R)-visited(D9WM1R)` beside the deletion results. Also report deletion-minus-mask deltas separately for LOSS and WIN.

Interpretation:

- if both deletion and read-mask contrasts favor LOSS by similar amounts, the LOSS-specific conclusion is robust to tombstone topology;
- if deletion shows a large LOSS/WIN contrast but read-mask does not, do not attribute the deletion contrast to memo value alone; slot/probe/replacement effects or deletion semantics are implicated;
- if read-mask shows a LOSS contrast but deletion attenuates or reverses it, physical deletion effects are opposing the informational effect.

Do not require numerical equality between deletion and read-mask variants: they intentionally implement different forgetting semantics after recomputation.

## Baseline-demand exposure diagnostic

Equalizing the number of selected entries still does not equalize the opportunity for those entries to matter. A selected LOSS key may simply be queried again more often, or sooner, than a selected WIN key. In that case a larger LOSS intervention effect would establish that the selected LOSS memo is more useful in the realized search, but would not by itself show that LOSS has greater value conditional on reuse opportunity.

Freeze an additional diagnostic from the unmodified baseline B trace. For every entry eligible at `t*`, without changing the intervention selection rule, record its post-`t*` baseline demand before that occupant generation is replaced or otherwise ceases to be the same memo fact:

- whether the canonical key is queried at least once;
- distance in solver lookup events from `t*` to its first query, or `NONE`;
- number of baseline lookups that would consume that exact memo fact while it remains live;
- whether its first such lookup would be a cached-LOSS shortcut / cached-WIN consumption under B.

Report these quantities separately for the frozen selected LOSS and WIN sets. In particular report `selected_with_future_demand / k`, median first-query distance among demanded entries, and total exact-generation baseline consumptions.

This is an exposure diagnostic, not a new treatment and not a success criterion. Do not use post-intervention traces to redefine, rematch, or filter the selected sets. Do not discard undemanded selected entries. The baseline trace is fixed before either arm diverges and is used only to distinguish two mechanisms:

- similar baseline demand exposure but a larger LOSS effect supports greater consequence per comparable reuse opportunity;
- much greater baseline demand exposure for LOSS means the observed LOSS/WIN effect may be driven partly or wholly by where future search demand falls, which is itself a substantive mechanism but is weaker evidence for a value-label-specific effect.

If desired after the frozen experiment is reported, a separately preregistered follow-up may match LOSS/WIN entries on baseline demand strata. It must not replace the frozen hash-selected result.

## Primary measurements

Per parent report:

- `t*` identity / deterministic boundary index;
- `k`;
- `visited(D9LM1) - visited(B)`;
- `visited(D9WM1) - visited(B)`;
- `visited(D9LM1) - visited(D9WM1)`;
- final outcome equality across B, D9LM1, D9WM1.

Across eligible frozen parents report total and median visited deltas plus the sign count of `visited(D9LM1) - visited(D9WM1)`. Do not divide visited delta by `k` and call it a per-entry effect: memo interactions are nonlinear.

## Interpretation

- `D9LM1 > D9WM1` consistently supports greater future causal value of the first matched batch of depth-9 LOSS memo than the corresponding WIN batch.
- Similar effects weaken the simple LOSS-label-specific explanation and suggest that deletion volume or generic memo investment explains the full-intervention contrast.
- A strong full D9LF/D9WF contrast with little first-boundary contrast implies that repeated interventions, later boundaries, or treatment-induced trajectory changes are important; the full contrast must not be attributed to a single matched LOSS batch.

This experiment estimates a one-shot boundary-level treatment contrast, not a global per-entry effect.

## Safety requirements

Before cohort execution require:

1. B, D9LM1, and D9WM1 have identical trace, logical memo-state digest, and physical memo-table digest immediately before `t*`. The physical digest must cover each slot's key/value, live/tombstone state, owner metadata, and all occupancy/replacement bookkeeping that can affect future behavior;
2. no variant may reconstruct its pre-`t*` table by reinserting the logical map into a fresh table; use an exact clone, or an independently replayed state satisfying requirement 1;
3. D9LM1 and D9WM1 delete exactly the same `k > 0` entries by count at `t*`;
4. no experimental invalidation occurs before or after `t*`;
5. selected key sets obey the frozen slot/order-independent hash rule;
6. non-target value entries at `t*` are untouched;
7. all three variants return the same game-theoretic outcome;
8. disabling the one-shot deletion reproduces B exactly, including visited count and the post-`t*` event trace;
9. D9LM1R and D9WM1R use exactly the same selected canonical key sets as their deletion counterparts and have a physical-table digest identical to B immediately after mask installation when mask metadata itself is excluded from the digest;
10. masked lookup must be observationally identical to an ordinary memo miss from the solver's point of view, except that the physical occupant is retained; a recomputed ordinary write must retire the old-generation mask;
11. disabling mask enforcement reproduces B exactly, including visited count and post-`t*` event trace;
12. B, D9LM1R, and D9WM1R must return the same game-theoretic outcome;
13. baseline-demand exposure is computed only from unmodified B and never changes `t*`, `k`, selected keys, treatment eligibility, or cohort inclusion; exact-generation accounting must stop when that occupant is replaced or ceases to represent the same memo fact.
