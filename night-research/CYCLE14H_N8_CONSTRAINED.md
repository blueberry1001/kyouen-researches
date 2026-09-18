# Cycle 14H — n=8 K=15 constrained first witnesses (SAMPLE)

Tool: `cycle8_b_maxsafe.exe first 8 15 …` node-capped **incomplete** counts.
Not a complete n=8 census. K8=15 inherited proven; not re-proved.

| constraint | first-found count (cap 2e6 nodes) | witness hex |
|---|---:|---|
| require orbit `(2,2)` | ≥67 | `3120140120888207` |
| require center-block `(3,3)` (4 cells) | ≥34 | `411210804804e007` |
| forbid center-block `(3,3)` | ≥52 | `3120140120888207` |
| corners=4 | 0 incomplete | — |
| corners=0 | 0 incomplete | — |
| forbid `(0,1)` / `(1,1)` / `(1,2)` / `(1,3)` / `(2,3)` / `(0,3)` | ≥1 each (prior cycle) | various |

## Contrast to n=7 COMPLETE

On n=7 K=14, require(2,2)=0 COMPLETE, require center XOR B-orbits, and five
orbits are mandatory. On n=8 K=15 SAMPLE, **both** (2,2) and the center-block
are freely usable, and most orbits are optional (witnesses omit them).

## Harvest of 6 unique witnesses (SAMPLE)

Constrained `first` runs produced 6 distinct K=15 masks
(`results/cycle14h_n8_witnesses.json`):

- ρ (cap3): **1 on 2 sets, 2 on 4 sets** (mixed — neither all-n=7 nor all-soft)
- Occupancy: **6 distinct patterns**; (2,2) used on 5/6; center-block on 3/6
- Corners: {1,2,3} appear
- Pair-distance histogram among the 6 includes **d=4** (and 7,9–13)
  — **unlike n=7**, where every pair of max sets has d≥5

> SAMPLE contrast: n=8 max-safe pairs can sit at exchange distance 4;
> n=7’s 16-set family has empty d≤4. Crystal isolation does not transfer.

## Non-claims
- Counts are lower bounds under a node cap.
- corners 0/4 may still exist at K=15 beyond the cap.
- Do not state n=8 “has no phases” without a complete census.

## Artifacts
- this note
- `results/cycle8_h_n8_sample.json`
- `night-research/CYCLE8_11_MAIN_RESULT.md`
