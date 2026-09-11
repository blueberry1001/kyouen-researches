# Depth-5 memo warming pathway decomposition

Status: preregistered before collecting memo-provenance or blocking results.

This is a supplemental diagnostic to `depth5-memo-warming-causal-probe.md`. It does not change that probe's primary full-block intervention or its success criterion.

## Why the full block is not mechanistically unique

There are two memo access sites in `Solver::win`:

1. the **entry lookup** for the current state;
2. the **child-prefetch lookup** used to populate `Child.cached` before sorting children.

A prior-sibling entry hit is a direct transposition shortcut: the whole recursive expansion of that state is avoided.

A prior-sibling child-prefetch hit has a different effect. The cached value changes the child's sort class before recursion:

- cached LOSS children are ordered first;
- unknown children are ordered next;
- cached WIN children are ordered last.

Therefore blocking a prior-sibling prefetch hit can change child order even if the same memo entry would later be encountered at the child's entry lookup. The preregistered full Probe B intentionally removes all cross-sibling memo knowledge, so it estimates the **total causal effect** of sibling warming, but it cannot by itself say whether the effect comes mainly from direct subtree pruning or from move-order information.

This distinction matters especially after the earlier depth-5 ordering reversal: a rule that made the locally observed cutoff LOSS child earlier increased total search by 3.610x. Memo warming may be protecting the baseline either by pruning repeated states directly, by teaching descendants which children to try first, or by both mechanisms.

## Frozen supplemental interventions

Run the same fixed roots, fresh-process protocol, `shrink/load` matching, physical-slot provenance, and blocked-hit rederivation semantics as the primary causal probe. Do not tune these modes after seeing results.

### B-all: full cross-sibling block

This is the already-preregistered primary intervention. Block prior-sibling hits at both entry lookup and child-prefetch lookup.

### B-entry: direct-reuse block only

Block prior-sibling hits only at the current-state entry lookup. Leave child-prefetch results untouched, including their effect on `Child.cached` and sorting.

Interpretation: removes direct recursive short-circuiting from prior siblings while preserving their child-order information.

### B-prefetch: ordering-information block only

Block prior-sibling hits only at child-prefetch lookup. Leave current-state entry lookups untouched.

For a blocked prefetch hit, set that child's cached status to unknown for construction/sorting; if the child is later entered, its ordinary entry lookup may still consume the prior-sibling memo entry and return immediately.

Interpretation: removes the pre-recursion ordering/classification signal while retaining direct entry reuse.

## Quantities to report

For each fixed root and each mode, report outcome, visited nodes, memo entries, runtime, and the same final `shrink/load` setting. The primary comparison remains baseline versus B-all.

For the pathway split also report:

- `visited(B-entry) / visited(baseline)`;
- `visited(B-prefetch) / visited(baseline)`;
- `visited(B-all) / visited(baseline)`;
- counts of blocked entry hits and blocked prefetch hits by memo depth and cached outcome.

Do not assume additivity. `B-all - baseline` need not equal the sum of the two single-path effects because changed ordering changes which later states are reached and which memo entries are created.

## Frozen interpretation

- If B-entry is large and B-prefetch is near baseline, sibling warming acts mainly as direct transposition reuse.
- If B-prefetch is large and B-entry is near baseline, the dominant mechanism is memo-informed child ordering rather than direct subtree pruning.
- If both single-path blocks are costly, both pathways matter.
- If neither single-path block is large but B-all is, the pathways interact strongly; the combined memo signal is more valuable than either component in isolation.

The original support criterion remains unchanged: attribution-only must exactly reproduce baseline, prior-sibling hits must be observed in multiple roots, and B-all must increase visited nodes with unchanged game outcome in at least 3 of 4 fixed roots. The split modes are mechanistic diagnostics, not extra degrees of freedom for deciding whether the primary hypothesis passed.
