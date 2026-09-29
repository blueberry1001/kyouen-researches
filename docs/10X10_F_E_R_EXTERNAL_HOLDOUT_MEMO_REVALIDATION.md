# F-E R-external holdout: corrected-memo revalidation

Date: 2026-09-29

## Why this revalidation was necessary

The preregistered 36-state R-external holdout used
`cpp/solvers/kyouen_solver_10_f_e_plain.cpp`, whose `FlatMemo81` was copied
from the historical 10x10 root solver.

That table packed

```cpp
(std::uint32_t(key.hi) << 2) | outcome
```

into 32 bits. A 10x10 position needs 36 bits in `key.hi`, so reserving two
outcome bits silently discarded the top six key bits. The corrected table
keeps the low 30 high-word bits beside the outcome and stores the remaining
six bits separately. Equality now uses the full 100-bit state key.

This is potentially more than a speed issue: a high-key state cannot hit its
own truncated entry, and overlapping linear-probe clusters can in principle
make a low-key lookup see a truncated entry from a different high key.
Therefore the frozen outcome labels had to be recomputed rather than merely
assuming that the old labels were sound.

## Frozen revalidation protocol

The sampling manifest, strata, Σd values, and expected historical labels were not
changed.

- same 36 frozen states (12 low, 12 middle, 12 high)
- fresh solver process for every state
- `memo_power=28`
- no cross-state memo sharing or outcome cache
- exact unbounded search
- corrected full-width memo key
- six CI shards, six states per shard
- workflow run: `36546020193`
- validated head: `bf58faf9d3c6c9d393c4785bebb43c749251be3c`
- per-state audit table:
  `results/10x10/f-e-r-external-holdout/corrected_memo_revalidation.csv`

The synthetic high-key memo self-test also passes before the exact solves.

## Result

**All 36/36 outcome labels are unchanged.**

| quantity | historical run | corrected-memo run |
|---|---:|---:|
| exact states | 36 | 36 |
| WIN | 26 | 26 |
| LOSS | 10 | 10 |
| label changes | — | **0** |

Therefore every endpoint that depends only on the frozen Σd values and the
WIN/LOSS labels is unchanged:

- AUC = **0.811538**
- rank-biserial = **+0.623077**
- P(LOSS | low) = **0/12**
- P(LOSS | middle) = **4/12**
- P(LOSS | high) = **6/12**
- mean Σd(LOSS) = **9118.100**
- mean Σd(WIN) = **8497.769**

Hence the preregistered decision remains

**`reversal_supported_outside_R`**.

## Search-cost effect of the bug

The corrected table visits fewer nodes in **36/36 states**.

| metric | value |
|---|---:|
| historical total visited | 488,547,405 |
| corrected total visited | 476,441,240 |
| total ratio | **0.975220** |
| total reduction | **2.478%** |
| median per-state ratio | **0.982228** |
| best ratio | **0.803605** |
| worst ratio | **0.995741** |
| WIN total reduction | **2.837%** |
| LOSS total reduction | **1.718%** |

The largest reduction is for state `0,2,58,60`:
7,108,416 -> 5,712,358 visited (**-19.64%**).

Wall-clock seconds are not compared because the historical run and this CI
revalidation used different machines. Node counts are the stable comparison.

## Scope of the conclusion

This revalidation shows that the memo-width bug **did not change any of the 36
F-E holdout labels**, while it did waste search work. It does not prove that
the historical table could never change an outcome on some other 10x10 root.

The repository's published 10x10 first-move classification is not directly
provenanced from this affected F-E executable: the representative
classification CSV was committed on 2026-07-31 (`d784e15`), while
`cpp/solvers/kyouen_solver_10_root.cpp` first appears in repository history at
`224f0da` on 2026-09-21. The present correction therefore specifically
revalidates the later FlatMemo81-based experiments rather than replacing the
independent classification evidence.

