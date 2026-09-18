# Odd-board center is necessary but not sufficient for A/B phases

## COMPLETE counts on center cell

| board | K | center id | force center @K | forbid center @K |
|---|---:|---:|---|---|
| n=5 | 9 | pid 12 `(2,2)` | **44** COMPLETE | **56** COMPLETE |
| n=7 | 14 | pid 24 `(3,3)` | **8** COMPLETE | **8** COMPLETE |

Both odd boards admit max safe sets with and without the unique center cell.
n=5 splits 44/56; n=7 splits 8/8 with **additional** exclusive structure
(B-bundle vs center) and an empty orbit `(2,2)` on n=7 only.

## Implication

Having a geometric center (odd n) is **not sufficient** to produce the n=7
two-phase crystal: n=5 already has a center split without collapsing to two
occupancy vectors (n=5 has **9** occupancy vectors, no empty orbit).

n=7’s crystal needs the **joint** pattern:
mandatory six-orbit skeleton + empty (2,2) + center XOR full B-bundle +
capacity peak at 2n via exclusive extension.

## Artifacts
- `results/cycle11_verify.json`
- `night-research/CYCLE15_CAPACITY_DECOMPOSITION.md`
- `night-research/CYCLE11_ORBIT_NECESSITY.md`
