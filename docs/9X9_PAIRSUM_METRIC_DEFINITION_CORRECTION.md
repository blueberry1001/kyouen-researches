# 9x9 pair-sum metric definition correction

Date: 2026-09-06

This note corrects the interpretation of the 9x9 pair-sum/mobility section in
`docs/MOVE_ORDERING_AUDIT.md` on branch `audit-blind-probe-and-move-ordering`.
It does **not** change the 10x10 blind-probe audit or its corrected independent
probe result.

## Summary

The apparent contradiction

- main: exhaustive scan reports `O > 0` in 8,595,588 / 117,253,740 safe
  4-parent/candidate pairs and `max O = 3`, with 90,988 strict raw-pair vs
  true-`T` top disagreements;
- audit branch: sampled scan reports `O = 0` throughout and zero pairTop vs
  exactTop disagreements;

comes from **different definitions of `W_ab(v)`**.

The audit implementation in `scripts/kyouen9_pairsum.py::response_sets`
requires not only

```text
{a,b,v,r} is forbidden
```

but also

```text
every other quad in P+v+r is safe.
```

The main exhaustive analyzer
`scripts/analyze-9x9-pair-gap-decomposition.cpp` uses the raw completion set
for the triple `{a,b,v}` without this extra filter.

Therefore the two scores are not the same quantity and their results must not
be compared as if they were replications of one another.

## Why the audit definition forces E = O = 0

Let `P+v` be safe. Define the audit-filtered set

```text
W'_ab(v) = { r : {a,b,v,r} is forbidden and every other quad in P+v+r is safe }.
```

### Existing-danger term E vanishes

If `r` was already dangerous in the parent `P`, then some quad contained in
`P+r` is forbidden. That quad does not contain the newly placed `v`, so it is
an "other quad" relative to `{a,b,v,r}`. The audit filter rejects `r`.

Hence no `r` in any `W'_ab(v)` can be an already-dangerous response:

```text
E' = 0.
```

### Overlap term O vanishes

Suppose the same `r` belonged to two distinct filtered sets `W'_ab(v)` and
`W'_cd(v)`. Then `P+v+r` would contain two distinct forbidden quads,
`{a,b,v,r}` and `{c,d,v,r}`. When testing membership in the first set, the
second forbidden quad is an "other quad", so the first membership is
rejected (and conversely).

Therefore filtered response sets are pairwise disjoint:

```text
O' = sum |W'_ab(v)| - |union W'_ab(v)| = 0.
```

This is true by construction; a sampled observation of `O'=0` is not evidence
that raw pair completion sets have no overlap.

## What the filtered score actually measures

For any response `r` that is safe before `v` and becomes unsafe after `v`, at
least one newly-created forbidden quad must contain `v`. If exactly one such
quad exists, `r` appears in exactly one `W'_ab(v)`. If multiple newly-created
forbidden quads exist, the current "every other quad safe" condition removes
`r` from **all** filtered sets.

So the audit score is a stricter "uniquely witnessed newly-killed response"
count. It is not the raw pair-sum used by the fixed geometric heuristic, and
it is not in general the union-based true mobility reduction `T` when a newly
killed response has multiple new witnesses.

In contrast, the main exhaustive analyzer defines raw completion sets first,
then explicitly separates

```text
raw_pair = T + E + O,
```

where `T` is the union of completions that were not already dangerous, `E`
counts already-dangerous completions, and `O` counts multiplicity.

## Consequences for existing conclusions

1. The audit-branch statement that "on 9x9 4-stone parents, pair-sum and
   exact-mobility orderings coincide" is **not established** for the original
   raw pair-sum heuristic. The compared score had already filtered away the
   mechanisms (`E` and `O`) that make raw pair-sum differ from true mobility.

2. The main exhaustive result (`O>0`, `max O=3`, 90,988 strict disagreements,
   11,378 D4 disagreement orbits) is not contradicted by the audit scan.

3. The 64-state exact pilot on main (discordant outcomes: true-`T` only LOSS
   19 vs raw-pair only LOSS 10) remains a relevant pilot for the intended
   raw-pair-vs-true-mobility question. Its sampling limitations remain.

4. `scripts/kyouen9_pairsum.py` is still useful as an independent geometry
   checker, but its `response_sets` / `pair_sum` / `exact_mobility` names must
   not be interpreted as reproducing the main raw-pair decomposition unless
   the extra "all other quads safe" filter is removed or exposed as a
   separate mode.

## Recommended validation

Add two explicit response-set modes and cross-check them on the same parents:

```text
raw_ab(v):      r iff {a,b,v,r} is forbidden
filtered_ab(v): raw condition + every other quad safe
```

Then verify mechanically:

- raw mode reproduces the C++ exhaustive analyzer on sampled `(P,v)` pairs;
- raw mode exhibits `E>0` and `O>0` examples;
- filtered mode has `E'=0` and `O'=0` by construction;
- true one-ply mobility reduction is computed directly as
  `legal(P) - {v} - legal(P+v)`, not inferred from filtered-set cardinality.

Until that cross-check is implemented, treat the audit branch's 9x9
"zero-discordance" result as a metric-definition artifact, not a negative
replication of the main 9x9 experiment.
