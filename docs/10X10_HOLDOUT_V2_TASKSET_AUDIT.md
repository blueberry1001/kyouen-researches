# 10x10 holdout-v2 task-set independent audit

Branch lineage audited: `10x10-second-clean-holdout` at `b2b7948673f7b3dfb468acfce8dabaeffdb2afa0`.

This audit independently recomputes the child-task set from the frozen 24-parent CSV and the preregistered geometric terminal rule only. No probe, memo, exact-outcome, proof, or game-value data are read.

## Independent recomputation

For each parent, enumerate empty cells in ascending cell order. Form the sorted 4-stone state and exclude it iff the determinant of rows `(x^2+y^2, x, y, 1)` is zero, i.e. the four points are concyclic or collinear and the move immediately terminates the game.

Independent recomputation result:

- frozen parents: 24
- continuing child tasks: **2292**
- CSV SHA-256: `907dc011eb64640ca3722039b0ebcfc0b604e7ad37bb3e7576c9253c607233e1`
- result: **exact match** with `scripts/freeze_10x10_holdout_v2_tasks.py`

## Per-parent counts

| index | parent | continuing | immediate-terminal moves |
|---:|---|---:|---|
| 1 | `1,62,72` | 97 | none |
| 2 | `11,16,25` | 96 | 22 |
| 3 | `3,17,43` | 96 | 37 |
| 4 | `13,26,43` | 96 | 36 |
| 5 | `3,68,78` | 97 | none |
| 6 | `4,38,81` | 97 | none |
| 7 | `2,42,82` | 90 | 12,22,32,52,62,72,92 |
| 8 | `0,17,82` | 97 | none |
| 9 | `0,33,48` | 96 | 46 |
| 10 | `22,56,57` | 97 | none |
| 11 | `0,28,83` | 97 | none |
| 12 | `1,12,36` | 97 | none |
| 13 | `1,23,66` | 97 | none |
| 14 | `11,38,64` | 97 | none |
| 15 | `0,33,79` | 97 | none |
| 16 | `0,48,79` | 94 | 2,15,99 |
| 17 | `13,14,76` | 88 | 21,26,40,47,50,57,71,83,84 |
| 18 | `1,20,94` | 92 | 50,71,82,89,97 |
| 19 | `2,65,82` | 94 | 1,25,81 |
| 20 | `3,11,55` | 96 | 36 |
| 21 | `3,24,65` | 96 | 95 |
| 22 | `4,23,78` | 97 | none |
| 23 | `11,17,26` | 96 | 22 |
| 24 | `0,18,74` | 95 | 48,50 |

The total number of excluded immediate-terminal moves is 36, and `24*97 - 36 = 2292`.

## Audit implication

The frozen task count and digest do not depend on the probe implementation. A future probe run should be rejected before analysis if it does not cover exactly these 2292 ordered tasks or if the regenerated task CSV digest differs from the value above.

This audit does not inspect or validate any LOSS/WIN outcome and therefore does not consume the holdout.