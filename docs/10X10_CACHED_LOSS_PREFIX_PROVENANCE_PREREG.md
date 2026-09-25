# 10x10 cached-LOSS prefix provenance measurement

Branch: `preregister-cached-loss-prefix-provenance`
Base: `224f0dae89f95bfafa20290e872d96b9567dc6d7`

## Motivation

The completed loss-first endpoint shows that promoting the first already-cached
LOSS is sufficient to recover the cache-aware endpoint on the frozen cohort.
The remaining mechanism question is narrower: when cache-blind order reaches an
already-cached LOSS only after recursively exploring unknown children, how much
of that prefix is genuinely disposable work, and how much creates memo entries
that are useful later?

Simply summing `visited` spent before the cached LOSS is an upper bound, not a
causal saving estimate. Removing that prefix also removes memo entries produced
inside it, so later search can become more expensive.

This document freezes a lightweight provenance measurement before inspecting
new results. It does not authorize a new parent cohort or a new ordering rule.

## Frozen cohort and solver modes

Use the existing 12-parent V2 endpoint cohort only. Compare the already-defined
cache-blind baseline B and loss-first-only L. Do not select parents from the new
measurements.

Outcome, `visited`, `maxdepth`, final memo use, and existing endpoint diagnostics
must remain exactly equal to their corresponding uninstrumented mode.

## Event definition

A **B prefix event** occurs at an expanded WIN node when:

1. child prefetch finds at least one cached LOSS;
2. B order places one or more uncached children before the first cached LOSS;
3. those uncached children are recursively entered before the cached LOSS is
   consumed and causes the WIN return.

For each such event, the recursive calls before that cached LOSS form its
`pre_cached_loss_prefix`.

L is a negative-control mode: because the first cached LOSS is promoted to the
front, its corresponding prefix counters must be zero.

## Frozen counters

Collect globally and by parent depth:

- `prefix_events`
- `prefix_recursive_calls`
- `prefix_recursive_visited`
- `prefix_new_memo_puts`
- `prefix_new_memo_put_loss`
- `prefix_new_memo_put_win`
- `prefix_origin_later_entry_hits`
- `prefix_origin_later_child_hits`
- WIN/LOSS split for both later-hit counters

A memo entry is `prefix-origin` iff its first insertion during the current exact
solve occurs while execution is dynamically inside a `pre_cached_loss_prefix`.
The provenance bit is metadata only and must not affect lookup, replacement,
ordering, or return values.

Count a later hit only after execution has left the dynamic prefix that first
created the entry. Hits inside the same prefix do not measure downstream value
of retaining that prefix and are excluded.

If an entry is overwritten/reinserted, provenance remains attached to the
currently stored key only if the stored result descends from a prefix-origin
first insertion. The implementation must document the memo replacement rule and
add a regression for this case before cohort use.

## Minimal implementation strategy

Avoid logging the full search DAG. Maintain:

1. a dynamic `prefix_depth` counter (zero outside a qualifying prefix);
2. one provenance bit per occupied memo slot, cleared with the slot;
3. a monotonically increasing prefix epoch or equivalent guard so hits inside
   the creating dynamic prefix are not counted as later reuse.

The bit must be written only when a previously absent key is inserted while
`prefix_depth > 0`. Ordinary memo payload remains unchanged.

Before using the 12-parent cohort, tiny regression tests must verify:

- instrumentation on/off gives identical outcome and `visited`;
- L has zero prefix events/calls/visited;
- a synthetic prefix-origin entry hit after prefix exit increments later reuse;
- a hit before prefix exit does not;
- slot clear/replacement cannot leak provenance to an unrelated key.

## Interpretation

`prefix_recursive_visited` is the gross work that loss-first skips locally.
It is **not** the predicted B-L saving.

The first mechanistic ratio is

`later_reuse_per_prefix_put = (later_entry_hits + later_child_hits) / prefix_new_memo_puts`.

The second is the fraction of prefix-origin entries ever reused after prefix
exit. This requires a per-slot `ever_reused_later` bit or an equivalent count at
clear/end; if that extra bit is judged too invasive, omit this secondary metric
rather than approximating it from hit counts.

Decision rule:

- If downstream reuse is rare (frozen threshold: fewer than 0.05 later hits per
  prefix-origin put in at least 9/12 parents), treat the skipped prefix as
  predominantly disposable and prioritize explaining where cached LOSS states
  arise.
- Otherwise, the speedup is a tradeoff between immediate prefix removal and
  lost transposition investment; proceed to targeted DAG/reuse analysis before
  making a causal `visited` attribution claim.

The 0.05 threshold is a research-priority rule, not a significance test.

## Important limitation

A hit count does not equal visited work saved. Even if reuse is common, this
measurement cannot by itself quantify the counterfactual cost of removing the
originating prefix. A causal visited decomposition would require replay or a
controlled memo-provenance ablation. This phase exists to decide whether that
heavier experiment is warranted.
