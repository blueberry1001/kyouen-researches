# Depth-5 memo warming pathway decomposition

Status: preregistered before collecting memo-provenance or blocking results. Amended before any pathway-split results after re-reading the exact `Child.cached` execution semantics.

This is a supplemental diagnostic to `depth5-memo-warming-causal-probe.md`. It does not change that probe's primary full-block intervention or its success criterion.

## Why the original two-site split was insufficient

There are two memo access sites in `Solver::win`:

1. the **entry lookup** for the current state;
2. the **child-prefetch lookup** used to populate `Child.cached` before sorting children.

The child-prefetch value has two effects, not one:

- it changes the child's sort class (`cached LOSS`, `unknown`, `cached WIN`);
- when that child is reached, the solver consumes `Child.cached` directly and **does not call `win` for that child at all**.

Therefore the earlier proposed `B-entry` mode (block only current-state entry hits while leaving `Child.cached` untouched) does **not** isolate direct transposition reuse. Any prior-sibling value already found by child-prefetch still bypasses recursion before an entry lookup can occur.

Conversely, the earlier `B-prefetch` mode (hide a prior-sibling prefetch hit, then allow the ordinary entry lookup) does remove the sorting signal while still allowing the memo value to short-circuit when the child is actually entered. For visited-node accounting this remains a valid ordering-only intervention, but the mechanism should be described in terms of the cached value's two uses rather than two independent lookup sites.

This amendment is made before observing any memo-provenance or blocking results.

## Frozen supplemental interventions

Run the same fixed roots, fresh-process protocol, `shrink/load` matching, physical-slot provenance, and blocked-hit rederivation semantics as the primary causal probe. Do not tune these modes after seeing results.

### B-all: full cross-sibling block

This is the already-preregistered primary intervention. Remove all use of prior-depth5-sibling memo knowledge: hide it from child-prefetch classification/direct consumption and block it at entry lookup if reached. This estimates the total causal effect of sibling warming.

### B-order: ordering-information block only

When child-prefetch finds a prior-sibling memo entry, retain the cached outcome in a separate execution-only field, but force its sorting class to `unknown`.

When that child is later reached, consume the retained cached outcome exactly as baseline would, without recursively calling `win`.

Thus B-order removes only the information used to order children while preserving direct memo reuse. It is stronger and cleaner than relying on a later entry lookup because execution cost remains baseline-like even if changed ordering alters intervening memo state.

### B-direct: direct-reuse block only

When child-prefetch finds a prior-sibling memo entry, preserve that value for sorting exactly as baseline does, but mark it `sort-only`: if the child is later reached, do **not** consume the cached outcome. Instead recurse into that child while blocking the corresponding prior-sibling entry hit so the subtree is genuinely rederived.

For prior-sibling memo hits first encountered at current-state entry lookup, block them as in B-all.

This preserves the ordering/classification signal while removing the direct recursive shortcut.

### Deprecated diagnostic: old B-entry

The old `B-entry` definition (block entry hits only while leaving ordinary `Child.cached` execution intact) is not a valid direct-reuse isolation because prefetched cached children bypass entry lookup entirely. It may be retained only as an implementation sanity check, not as a mechanistic result.

## Structural prediction from the current solver

Because memoization covers depths 9--17 and every recursive node below the depth-5 parent performs child-prefetch before entering its children, much prior-sibling knowledge should normally be visible first through child-prefetch. Consequently the old B-entry-only mode may be nearly null even if direct reuse is very important; that would be an architectural consequence, not evidence against direct reuse.

The informative comparison is therefore B-order versus B-direct versus B-all.

## Quantities to report

For each fixed root and each mode, report outcome, visited nodes, memo entries, runtime, and the same final `shrink/load` setting.

For the pathway split report:

- `visited(B-order) / visited(baseline)`;
- `visited(B-direct) / visited(baseline)`;
- `visited(B-all) / visited(baseline)`;
- counts of prior-sibling prefetch hits by memo depth and cached outcome;
- counts of direct cached consumptions suppressed in B-direct;
- counts of prior-sibling entry hits blocked in B-direct/B-all.

Do not assume additivity. Changed ordering changes which later states are reached and which memo entries are created, so `B-all - baseline` need not equal the sum of the two single-mechanism effects.

## Frozen interpretation

- If B-order is large and B-direct is near baseline, sibling warming acts mainly through memo-informed move ordering.
- If B-direct is large and B-order is near baseline, sibling warming acts mainly through direct transposition reuse.
- If both are costly, both mechanisms matter.
- If neither is large but B-all is, the mechanisms interact strongly.

The original support criterion remains unchanged: attribution-only must exactly reproduce baseline, prior-sibling hits must be observed in multiple roots, and B-all must increase visited nodes with unchanged game outcome in at least 3 of 4 fixed roots. The split modes remain mechanistic diagnostics, not extra degrees of freedom for deciding whether the primary hypothesis passed.
