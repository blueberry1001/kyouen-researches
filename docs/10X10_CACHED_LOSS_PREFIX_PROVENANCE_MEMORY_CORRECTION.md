# Cached-LOSS prefix provenance: memory-bound correction

Branch: `preregister-cached-loss-prefix-provenance`
Previous refinement: `aa2dd1bfeed4ac5bd6663d44871dde26333eda9a`

This correction is frozen before cohort results are inspected.

## Problem found in the previous refinement

`aa2dd1b` described the exit-flip representation as bounded because the per-slot sidecar is one byte. That statement omitted the peak memory of the active outermost prefix's `touched` list.

If an outermost prefix first-inserts `k` distinct physical memo slots, the list must retain `k` slot identities until the outermost 1 -> 0 exit. With 32-bit slot indices this is `4k` bytes in addition to the one-byte-per-slot sidecar. In the worst case `k` approaches the number of physical slots `N`, so peak provenance memory approaches `5N` bytes. With 64-bit indices it approaches `9N`. Thus the exit-flip scheme is not actually smaller in worst-case memory than a 32-bit owner id per slot.

This is bookkeeping-only, but it matters because the measurement is supposed to be lightweight and non-perturbing.

## Corrected preferred representation

Prefer a 32-bit `origin_outer_event` sidecar per physical memo slot and two global counters:

- `next_outer_event`: monotonically increasing nonzero id assigned on prefix depth 0 -> 1;
- `last_exited_outer_event`: id of the most recently completed outermost prefix.

Rules:

1. On depth 0 -> 1, assign `active_outer_event = next_outer_event++`.
2. Nested prefixes inherit the same `active_outer_event`.
3. A successful first insertion while depth > 0 stores `origin_outer_event[slot] = active_outer_event`.
4. A non-prefix insertion or slot clear/reuse stores zero.
5. On depth 1 -> 0, set `last_exited_outer_event = active_outer_event`.
6. A hit is later reuse iff `origin_outer_event[slot] != 0 && origin_outer_event[slot] <= last_exited_outer_event`.

Because outermost events cannot overlap in the single-threaded DFS and ids are monotone, this predicate exactly excludes hits inside the creating outermost prefix, including inner-exit/outer-active hits, while retaining eligibility forever after the owner exits. No touched list or O(N) exit scan is required.

Use `uint32_t`; abort/fail closed before id wrap rather than silently recycling ids. Cohort runs must report the maximum assigned event id so the wrap guard is auditable.

## Memory comparison

For `N` physical memo slots:

- previous exit-flip implementation: `N` sidecar bytes + up to `4N` bytes of 32-bit touched indices = up to about `5N` bytes;
- owner-event implementation: exactly `4N` sidecar bytes, no touched list;
- full DAG logging: substantially larger and still unnecessary for this phase.

The owner-event representation therefore has the lower simple worst-case bound and simpler eligibility semantics, despite the larger fixed per-slot sidecar.

## Mandatory regressions

Retain all previous regressions and add:

- outer event A insertion -> A exit -> event B active -> hit A: counts as later reuse;
- event B insertion -> nested exit -> hit B while B outermost remains active: does not count;
- B exit -> hit B: counts;
- slot clear/reuse resets owner id to zero before a different key is visible;
- forced near-wrap test fails closed rather than reusing an event id;
- instrumentation on/off preserves outcome, `visited`, memo insertion/failure behavior, and B/L ordering exactly.

## Scope

This supersedes only the bounded representation in `aa2dd1b`. The frozen cohort, event definition, counters, 0.05 research-priority threshold, nesting semantics, and interpretation remain unchanged. No cohort result has been inspected for this correction.