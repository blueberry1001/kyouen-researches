# Cycle 12 — n=7 size-13 occupancy (SAMPLE)

Evidence: `cycle8_b_maxsafe.exe occ 7 13 --max-nodes 5e6`
→ `results/cycle12_occ_k13.json`. **Incomplete** (node cap).
Seen: 1116 safe 13-sets, **150 distinct occupancy patterns**.

## Contrast with K=14 (COMPLETE)

| layer | occupancy patterns | (2,2) | center | corners |
|---|---:|---|---|---|
| K=14 COMPLETE | **2** | never | 8/16 only | {2,3} only |
| K=13 SAMPLE | **150** / 1116 seen | often 0–2 stones | some patterns | 0–3 appear |

## COMPLETE facts on the 13-layer

- corners=4 @13: **0** complete
- center ∧ require(2,2) @13: **24** complete (exclusivity **relaxes** below max)
- force (2,2) @13: many witnesses (≥141 incomplete count)
- max with (2,2) occupied: **13** (Package B COMPLETE)

## Lemma

> The two-phase occupancy selection and the (2,2)/center exclusions are
> **maximum-layer (K=14) phenomena**. At K=13 the safe-set complex is already
> occupancy-rich (150 patterns in a partial dump), and center+(2,2) is legal.

## Artifacts
- `results/cycle12_occ_k13.json`
- `night-research/CYCLE11_ORBIT_NECESSITY.md` (K=13 COMPLETE probes)
- `night-research/CYCLE10_OCCUPANCY_SELECTION.md`
