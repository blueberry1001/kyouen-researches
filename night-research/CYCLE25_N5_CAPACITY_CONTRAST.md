# Cycle 25 — n=5 capacity contrast (COMPLETE)

n=5, K=9=2n−1, 100 max safe sets (census). Solver `cycle8_b_maxsafe.exe`.

## COMPLETE results

| constraint | result |
|---|---|
| forbid center orbit (2,2) @K=9 | **56** complete |
| require center @K=9 | **44** complete |
| max with forbid center | **9** complete (56@9) |
| max with forbid (0,2) | **8** complete (272@8) |
| max with forbid (1,2) | **8** complete (528@8) |

## Cross-board omit-cost (COMPLETE)

| omitted orbit | n=5 cost | n=6 cost | n=7 cost |
|---|---:|---:|---:|
| center / (2,2) | **0** (still K) | **0** on n=6 (still K=11 without (2,2)) | **forbidden** at K=14 |
| (0,2) | −1 | −1 | **−2** |
| (1,2) | −1 | −1 | **−2** (with (0,2) even −3) |

## Lemma

> On odd boards n=5 and n=7 the center orbit is optional-or-exclusive at
> maximum size, but only n=7 **forbids** a non-center orbit ((2,2)) at max
> and only n=7 reaches K=2n via two exclusive occupancy phases.
> n=5 center split 44/56 COMPLETE is therefore **not** a crystal.

## Artifacts
- this note
- `CYCLE24_N6_CAPACITY_CONTRAST.md`
- `FINAL_SELECTION_THEOREM.md`
