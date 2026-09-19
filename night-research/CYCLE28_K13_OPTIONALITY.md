# Cycle 28 — n=7 K=13 layer optionality (SAMPLE/COMPLETE mix)

Solver `cycle8_b_maxsafe.exe first/count 7 13 …`.

## Results

| constraint @K=13 | count | complete? |
|---|---:|---|
| require orbit center (3,3) | **280** | **yes** |
| forbid orbit center | ≥999 | no (cap 4M) |
| forbid orbit (0,3) | ≥557 | no (cap 4M) |
| require (0,2) | (prior) mandatory @13 | yes forbid=0 |
| require (1,2) | (prior) mandatory @13 | yes forbid=0 |
| require (2,2) | many witnesses | force K=13 exists COMPLETE via Package B/G1 |
| corners=4 | **0** | yes |

## Lemma (13-layer vs 14-layer)

> At size 13 the center orbit is **optional** (280 COMPLETE with center;
> census/SAMPLE also show many without). The hard requirements that survive
> to K=13 are `(0,2)` and `(1,2)` (COMPLETE forbid=0). At size 14 the
> crystal adds six mandatory orbits, empty (2,2), and the exclusive A/B
> phase split. Cross-phase cores fire named quads (Cycle 27).

## Artifacts
- this note
- `CYCLE12_K13_LAYER.md`, `CYCLE15_CAPACITY_DECOMPOSITION.md`
- `FINAL_SELECTION_THEOREM.md`
