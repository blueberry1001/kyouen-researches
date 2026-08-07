# 10×10 two-stone root 69,91: child classification and the four TableFull states

This experiment continues the two-stone frontier opened by
`docs/10X10_THREE_STONE_SUBSETS.md`. Coordinates use `id = y * 10 + x`; outcomes
are from the player to move.

## Classification of the 98 three-stone children

The exact split-search over all legal third stones of the two-stone root
`69,91` (canonical form `[8,30]`) classifies:

```text
WIN       = 94
LOSS      = 0
TABLE_FULL = 4
```

Machine-readable results:
[`results/10x10/two-stone-69-91-child-proof.csv`](../results/10x10/two-stone-69-91-child-proof.csv).

Until the four TABLE_FULL states are resolved, the parent `69,91` cannot be
proven LOSS (a parent is LOSS iff every child is WIN).

## The four TABLE_FULL children

| child | memo entries at failure | wall time |
|---|---|---:|
| `1,39,80` | 475,654,197 | 1486 s |
| `1,39,90` | 463,036,884 | 1411 s |
| `7,8,30` | 516,901,571 | 1584 s |
| `8,17,30` | 518,154,340 | 1524 s |

All four were re-attempted at `shrink=0`, `load=90` and failed again with the
same `TABLE_FULL`, at nearly the same memo sizes.

## Bucket diagnostics

Each child was re-run with a diagnostic build that dumps per-depth memo bucket
usage on completion (`DONE`) or on the fill that kills the search (`FILL`).
Capacities are `max_used = 2^power * load / 100` with `load=90`.

| child | outcome | d13a (2^27) | d13b (2^25) | d14a (2^27) | d14b (2^24) | d16 (2^23) |
|---|---|---|---:|---:|---:|---:|---:|
| `8,30,72` | WIN | 120,795,955 (100%) | 30,062,303 (99.5%) | 120,795,955 (100%) | 1,759,454 | 6,533,219 (86.5%) |
| `5,8,30` | WIN | 120,795,955 (100%) | 29,211,706 (96.8%) | 120,604,995 (99.8%) | 0 | 6,259,324 (82.9%) |
| `8,10,30` | WIN | 112,294,939 (93.0%) | 0 | 97,117,981 (80.4%) | 0 | 6,174,529 (81.8%) |
| `8,9,30` | WIN | 110,277,343 (91.3%) | 0 | 93,036,131 (77.0%) | 0 | 5,368,607 (71.1%) |
| `1,39,70` | WIN | 103,790,039 (85.9%) | 0 | 88,616,950 (73.4%) | 0 | 5,448,041 (72.2%) |
| `2,8,30` | WIN | 102,330,162 (84.7%) | 0 | 82,852,608 (68.6%) | 0 | 4,454,054 (59.0%) |
| `3,9,80` | WIN | 71,226,853 (59.0%) | 0 | 60,979,801 (50.5%) | 0 | 3,708,086 (49.1%) |
| `1,39,80` | TF | 120,795,955 (100%) | 17,850,690 | 120,795,955 (100%) | 666,160 | **7,549,747 (100%)** |
| `1,39,90` | TF | 120,795,955 (100%) | 14,352,064 | 119,441,955 (98.9%) | 0 | **7,549,747 (100%)** |
| `7,8,30` | TF | 120,795,955 (100%) | **30,198,988 (100%)** | 120,795,955 (100%) | 4,233,764 | 6,827,798 (90.5%) |
| `8,17,30` | TF | 120,795,955 (100%) | **30,198,988 (100%)** | 120,795,955 (100%) | 6,799,550 | 7,344,855 (97.3%) |

## Why exactly these four are hard

The decisive observations:

1. **A full depth-13 or depth-14 primary table alone never kills the search.**
   `8,30,72` (WIN) ends with both `d13a` and `d14a` at 100%; the
   `MultiDepthMemo100::put` fallback chain (`d13a` -> `d13b`, `d14a` -> `d14b`)
   absorbs the overflow.

2. **The failure trigger is a full fallback or a small leaf layer:**
   - `7,8,30` and `8,17,30` fill `d13b` too: the depth-13 layer collectively
     holds 151,0M entries (120.8M + 30.2M) and the search still needs more.
   - `1,39,80` and `1,39,90` fill the depth-16 layer (`d16`, only 2^23 * 0.9 =
     7.55M entries), which has no secondary table.

3. **The line between WIN and TABLE_FULL is razor-thin.** The largest WIN
   (`8,30,72`, 518,980,323 visited) ends at `d13b = 99.5%` of capacity — within
   136,685 entries of the failure point of `7,8,30`/`8,17,30`. These four TF
   children are the upper tail of a stable middle band, not a different
   geometric class: their D4 orbit siblings and same-Σd siblings all WIN.

4. **Legal-count and geometry do not discriminate.** All four TF children have
   the same legal-move count (98) as most children; the WIN children `8,9,30`,
   `8,10,30`, `1,39,70`, `2,8,30` sit in the same D4 orbits (third-stone
   `x = 90/91/92/82` orbits) and same-distance groups as the TF states.

## What would resolve them

The search is capacity-bound, not rule-bound. A profile that gives the depth-13
and depth-14 primary tables one more power (`d13a`, `d14a`: 2^27 -> 2^28) plus
a larger depth-16 layer (`d16`: 2^23 -> 2^24) should absorb all four
(150.9M depth-13 entries for `7,8,30` fits in 2^28 alone; 7.55M depth-16 for
`1,39,80` fits in 2^24). This costs roughly one byte per extra entry in the
affected layers; the peak RSS would rise from ~3.5 GB to ~7 GB, still far
inside the 41 GB machine. Until then the parent `69,91` remains open.
