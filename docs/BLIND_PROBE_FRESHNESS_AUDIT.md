# Blind probe freshness audit

## Finding

Commit `b5172a4` cannot be treated as a valid blind validation of the 3-stone
`memo desc @ 1M` rule.

The historical runner passes an entire batch of child states to one native
solver invocation.  The native solver constructs one `Solver` before the task
loop and reuses it for every state.  Therefore memo entries persist from one
child to the next.

The resulting 3-stone probe CSVs show the expected cumulative signature: each
row spends about 1M visited nodes while absolute `memo` grows approximately
1M, 2M, 3M, ... with row index.  Sorting absolute memo descending therefore
mostly reverses the batch/input order instead of ranking independent child
search difficulty.

This explains why the reported fixed ordering sometimes appears good and
sometimes fails badly: the tested rule is confounded with input position.
The reported verdict C, medians, and counterexamples remain useful as an audit
trail, but not as evidence for or against an independently measured memo rule.

## Frozen corrective rerun

Do not tune the rule using these outcomes.  Rerun the same seven evaluated LOSS
parents first:

- `2,9,33`
- `4,9,33`
- `9,12,33`
- `9,19,33`
- `9,23,33`
- `0,31,36`
- `0,36,44`

Keep the original fixed rule unchanged:

- feature: final memo used
- budget: 1,000,000 visited per child
- direction: descending
- one fresh solver process per child
- tie break: original solver/input order
- same batch0 exact outcomes; do not extend exact search before the corrected
  ranking is frozen

Primary comparison remains first-LOSS position against the same random and
solver-default baselines.  Probe-cost accounting remains 1M per classified
child.

Only after the corrected seven-parent result is committed may additional
parents, alternative directions, delta-memo, maxdepth, or other features be
explored.

## Guardrails

`scripts/audit_blind_probe_freshness.py` detects the cumulative-memo signature
in historical probe files and exits nonzero when found.

`scripts/run_blind_probe_parent_fresh.py` runs exactly one native solver process
per child and writes separate `probe_fresh_*` CSVs, leaving historical raw data
untouched.
