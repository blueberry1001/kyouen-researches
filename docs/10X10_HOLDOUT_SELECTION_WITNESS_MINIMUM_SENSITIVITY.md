# 10x10 holdout: minimum sensitivity to pre-known selection witnesses

This note resolves the minimum-contamination sensitivity analysis identified in
`10X10_HOLDOUT_PREKNOWN_LOSS_CHILD_AUDIT.md`.

Scope: remove exactly the one pre-holdout exact LOSS witness stored in the
proof-source row used to select each of the 11 holdout parents, matching under
D4 symmetry.  This is deliberately weaker than an exhaustive historical audit:
other pre-existing exact labels, if any, are not removed here.

## Result

Two parents have only one exact LOSS child in the holdout candidate set:
`0,17,31` and `0,3,13`.  Removing their pre-known witness leaves no LOSS child,
so first-LOSS rank is undefined for those two parents.

For every one of the remaining 9 parents, the first-LOSS rank under the frozen
1M fresh-memo ascending rule is unchanged after removing the selection witness:

| parent | original first LOSS | after witness removal |
|---|---:|---:|
| `0,36,50` | 1 | 1 |
| `9,33,54` | 1 | 1 |
| `0,1,13` | 1 | 1 |
| `0,7,31` | 1 | 1 |
| `0,13,34` | 1 | 1 |
| `0,13,44` | 1 | 1 |
| `0,2,13` | 6 | 6 |
| `0,10,13` | 1 | 1 |
| `0,13,21` | 1 | 1 |

The two previously unresolved cases are direct from committed raw data:

- `9,33,54`: the selection witness `9,33,54,63` has the smallest probe memo
  (`993737`), but after removing it the next-smallest memo candidate is
  `9,33,38,54` (`994370`), which is independently exact `LOSS`.  First LOSS
  therefore remains rank 1.
- `0,7,31`: the selection witness `0,7,31,64` has probe memo `995884`, while
  `0,7,31,77` has lower memo `994974` and is independently exact `LOSS`.
  Thus the pre-known witness was not the first-ranked LOSS in the first place.

Against each parent's exact random median after removal, the 9 evaluable parents
are 8 better / 1 tie / 0 worse.  The tie remains `9,33,54`, whose LOSS density
is so high that the exact random median is rank 1.  The one-sided sign test on
the 8 non-ties is therefore p = 1/256 = 0.00390625.

## Interpretation

The explanation "the holdout looked strong only because memo-ascending put the
pre-known selection witness first" is falsified by this minimum sensitivity
check: in all 9 parents where another LOSS remains, the first-LOSS rank is
unchanged after removing that witness.

This does **not** remove the more important family-selection concern.  The 11
parents were still drawn from pre-existing proof families, so a genuinely
geometry-only / outcome-blind second parent holdout remains necessary for
population-level generalization.
