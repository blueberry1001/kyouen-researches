# Cached-LOSS prefix provenance: bounded implementation refinement

Branch: `preregister-cached-loss-prefix-provenance`
Base amendment: `0e0de3badefa55d50e7d33c7e2df4378a84347cf`

This refinement is frozen before cohort results are inspected.

## Observation

The nesting amendment requires ownership by the outermost active prefix, but it does not require storing an event token in every memo slot.

The production rank memo tables do not evict or relocate occupied keys. An outermost prefix event also cannot overlap another outermost event in the single-threaded DFS: while it is active, every nested prefix belongs to that same outermost event; the next outermost event begins only after the previous one exits.

Therefore later-reuse eligibility can be materialized at outer-prefix exit rather than recovered from a per-slot owner id.

## Frozen bounded representation

Use one instrumentation sidecar byte per physical memo slot. Two bits are sufficient:

- `PREFIX_ORIGIN`: the currently stored key was first inserted while an outermost prefix was active;
- `LATER_ELIGIBLE`: that owning outermost prefix has exited.

For each currently active outermost prefix, maintain a `touched` list of physical slot identities first inserted anywhere inside that prefix, including nested prefixes.

Rules:

1. When prefix nesting depth changes from 0 to 1, start a fresh outermost `touched` list.
2. A successful first insertion while depth > 0 sets `PREFIX_ORIGIN`, leaves `LATER_ELIGIBLE` clear, and appends that physical slot exactly once to the current outermost list.
3. Nested prefix entry/exit does not create or flush another ownership list.
4. When nesting depth changes from 1 to 0, iterate the outermost `touched` list and set `LATER_ELIGIBLE` on those still-corresponding prefix-origin slots; then discard the list.
5. A memo hit contributes to later reuse iff both bits are set. Thus hits before outer exit, including hits after an inner exit, cannot count.
6. A non-prefix insertion has both bits clear.
7. Any slot clear/reuse must clear both bits before a different key can occupy the slot.

The WIN/LOSS split is read from the ordinary memo payload at hit time; no provenance outcome field is needed.

## Why this is equivalent to outermost event tokens

All insertions made while one outermost event is active have the same causal owner. No later outermost event can begin before that owner exits. Consequently the only owner property needed by the preregistered metric is whether that owner has exited. Flipping `LATER_ELIGIBLE` for exactly the slots in the owner's touched list at the 1 -> 0 transition implements that predicate directly.

This also avoids a potentially large per-slot event-id sidecar. A 32-bit owner id would require four bytes per physical slot; the two-bit state fits in the already acceptable one-byte-per-slot provenance representation used by earlier memo-warming instrumentation.

## Mandatory regressions added before cohort use

In addition to the amendment regressions:

- nested insertion -> inner exit -> hit: `PREFIX_ORIGIN=1`, `LATER_ELIGIBLE=0`, no later hit;
- outer exit flips eligibility for every nested/outer insertion exactly once;
- a subsequent independent outermost prefix cannot change ownership or eligibility of an earlier stored entry;
- a slot reused for a different key has both provenance bits cleared before the new key becomes visible;
- instrumentation on/off preserves outcome, `visited`, memo insertion/failure behavior, and B/L ordering exactly.

## Scope

This changes bookkeeping representation only. The frozen cohort, counters, 0.05 decision threshold, and interpretation in the original preregistration and nesting amendment remain unchanged.
