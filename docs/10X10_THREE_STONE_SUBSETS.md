# 10×10 three-stone subsets of the medium LOSS root

This experiment continues from the legal eight-stone LOSS root

```text
90,61,2,73,69,66,13,91
```

and the twelve previously classified four-stone LOSS subsets. Coordinates use
`id = y * 10 + x`; outcomes are from the player to move.

## Classification of all 56 three-stone subsets

There are `C(8,3) = 56` three-stone subsets.

```text
WIN  = 54
LOSS = 2
```

Thirty roots have an explicit legal move to one of the verified four-stone
LOSS roots. The other twenty-six roots were solved independently by the exact
C++ searcher. The outcome counts above are generated from the completed runs,
not inferred from how expensive a search appeared.

The independently verified three-stone LOSS roots are:

- `90,2,91`
- `90,73,91`

The complete machine-readable table is
[`results/10x10/three-stone-subsets-of-medium-loss.csv`](../results/10x10/three-stone-subsets-of-medium-loss.csv).

## Independent-search runs

The search began with `shrink=3` and `load=80`. A root was retried with a
larger memo table only when the preceding run ended with `TABLE_FULL`.

| Configuration | Completed roots |
|---|---:|
| `shrink=3`, standard memo profile | 14 |
| `shrink=2`, standard memo profile | 4 |
| `shrink=1`, standard memo profile | 5 |
| `shrink=0`, standard memo profile | 1 |
| `shrink=0`, targeted-v1, `load=90` | 1 |
| `shrink=0`, targeted-v2, `load=90` | 1 |
| **Total** | **26** |

| Metric over the 26 independently searched roots | Minimum | Maximum |
|---|---:|---:|
| Search visits | 10,067,830 | 644,565,278 |
| Memo entries | 10,023,329 | 643,635,814 |
| Wall time | 15.38 s | 1447.48 s |
| Peak RSS | 567,992 KiB | 4,893,968 KiB |

### The two largest roots

The first `shrink=0`, `load=80` attempts filled the depth-16 table at exactly
`6,710,886` entries. Expanding only that layer allowed the search to continue,
but then other rank tables became the limiting factor.

The `targeted-v1` temporary build used these powers instead of the standard
ones: `d13b=26`, `d14b=25`, `d15=27`, `d16=24`, and `d17=20`. It completed
`90,73,91`. For `90,2,91`, that profile then filled the combined depth-14
capacity at exactly `150,994,943` entries while depth 13 was also 94% full.
The `targeted-v2` build therefore raised only `d13b` from 26 to 27 and `d14b`
from 25 to 26.

The game rules, symmetry canonicalization, move ordering, stored outcomes, and
exact recursive search were unchanged; only memo capacity changed. The three
large `shrink=0` measurements came from GitHub Actions runs `30827930208`
(standard), `30830621637` (targeted-v1), and `30832387783` (targeted-v2).

| Root | Outcome | Visits | Memo entries | Wall time | Peak RSS | Profile |
|---|:---:|---:|---:|---:|---:|---|
| `90,2,91` | LOSS | 644,565,278 | 643,635,814 | 1447.48 s | 4,893,968 KiB | targeted-v2 |
| `90,73,91` | LOSS | 504,612,782 | 503,703,505 | 794.09 s | 4,304,208 KiB | targeted-v1 |

## Validation boundary

The thirty direct rows are checked by adding their recorded witness move and
matching the resulting four-stone set against the twelve verified LOSS roots.
The other twenty-six rows record completed exact searches. The regression
workflow checks the complete `C(8,3)` enumeration, all direct witnesses, source
counts, outcomes, configurations, and recorded search metadata, then reruns one
fixed independent root (`2,73,66`) to detect solver regressions.

This is a complete classification of the three-stone subsets of the selected
eight-stone LOSS root. It is not yet a complete classification of all legal
three-stone positions on the 10×10 board, nor a proof of the empty-board
10×10 outcome.

## Immediate consequences for two-stone subsets

There are `C(8,2) = 28` two-stone subsets.

5 of the 28 roots are immediately WIN because they can move to a recorded three-stone LOSS root:

- `2,91` is WIN by adding `90`.
- `73,91` is WIN by adding `90`.
- `90,2` is WIN by adding `91`.
- `90,73` is WIN by adding `91`.
- `90,91` is WIN by adding `2`, `73`.

The remaining 23 roots form the next exact-search frontier.
